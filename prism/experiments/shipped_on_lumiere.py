#!/usr/bin/env python3
"""Apply the shipped PRISM report radiomics model (radiomics/models/calibrated) to LUMIERE, unchanged.

Images: DeepBraTumIA atlas-space skull-stripped CT1 and FLAIR (1 mm MNI); mask = union of DeepBraTumIA tumour labels.
Preprocessing and PyRadiomics settings are the legacy ones (train.preprocess_image + the training YAML).
The model's six MU-specific clinical code columns have no LUMIERE equivalent; two variants are reported:
  codes_as_unknown  IDH1/IDH2 "2" and MGMT "4" set when status is unknown, ATRX / 1p19q columns 0
  codes_zero        all six clinical columns 0

    uv run python -m prism.experiments.shipped_on_lumiere
"""

from __future__ import annotations

import json
import pickle
import sys
import tempfile
import zipfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import nibabel as nib
import numpy as np
import pandas as pd

from prism.config import OUTPUTS, REPO
from prism.lumiere import ROOT
from prism.metrics import cluster_bootstrap, point_metrics

RAD = REPO / "radiomics"
sys.path.insert(0, str(RAD))
from radiomics_pipeline.workflows import train as surv  # noqa: E402

sys.modules["scripts.run_postoperative_progression_surveillance"] = surv
YAML = RAD / "configs" / "postoperative_progression_surveillance_radiomics.yaml"
EXTRACT = ROOT / "imaging"
H = 120


def _find(scan_dir: Path, name: str) -> Path | None:
    hits = sorted(scan_dir.rglob(name))
    return hits[0] if hits else None


def extract(scan_id: str) -> dict:
    pid, date = scan_id.split("_", 1)
    d = next(EXTRACT.rglob(f"{pid}/{date}"), None)
    rec = {"scan_id": scan_id}
    if d is None:
        return rec
    atlas = _find(d, "DeepBraTumIA-segmentation") or d
    ct1, flair = _find(atlas, "ct1_skull_strip.nii.gz"), _find(atlas, "flair_skull_strip.nii.gz")
    seg = next((p for p in atlas.rglob("seg_mask.nii.gz") if "native" not in str(p)), None)
    if not (ct1 and flair and seg):
        return rec
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        s = nib.load(str(seg))
        union = (np.asarray(s.dataobj) > 0).astype(np.uint8)
        if union.sum() == 0:
            return rec
        mask_path = tmp / "union.nii.gz"
        nib.save(nib.Nifti1Image(union, s.affine, s.header), str(mask_path))
        ex = surv.build_radiomics_extractor(YAML)
        for mod, img in (("t1c", ct1), ("flair", flair)):
            out, _ = surv.preprocess_image(img, mask_path, tmp / f"{mod}.nii.gz")
            for k, v in ex.execute(str(out), str(mask_path)).items():
                if not k.startswith("diagnostics_"):
                    val = surv.scalarize_radiomics_value(v)
                    if val is not None:
                        rec[f"{mod}_{k.replace('original_', '')}"] = val
    return rec


def main() -> None:
    zp = ROOT / "Imaging-v202211.zip"
    cohort = pd.read_csv(OUTPUTS / "lumiere" / "cohort.csv")
    if not EXTRACT.exists():
        wanted = {f"{p}/{d}" for p, d in zip(cohort.patient_id, cohort.date)}
        with zipfile.ZipFile(zp) as z:
            members = [m for m in z.namelist() if "DeepBraTumIA" in m and any(w in m for w in wanted)]
            z.extractall(EXTRACT, members)
    feats_path = OUTPUTS / "lumiere" / "legacy_radiomics.csv"
    if not feats_path.exists():
        with ProcessPoolExecutor(64) as ex:
            feats = pd.DataFrame(list(ex.map(extract, cohort.scan_id)))
        feats.to_csv(feats_path, index=False)
    feats = pd.read_csv(feats_path).set_index("scan_id").reindex(cohort.scan_id)

    bundle = pickle.load(open(RAD / "models" / "calibrated" / "model_bundle.pkl", "rb"))
    cols = bundle["selected_columns"]
    ok = feats[[c for c in cols if not c.startswith("clin_")]].notna().all(axis=1).to_numpy()
    print(f"legacy features extracted for {ok.sum()} / {len(cohort)} scans")
    rows = []
    for variant in ("codes_as_unknown", "codes_zero"):
        X = pd.DataFrame(index=cohort.index)
        for c in cols:
            if not c.startswith("clin_"):
                X[c] = feats[c].to_numpy()
            elif variant == "codes_zero":
                X[c] = 0.0
            else:
                unk = {"clin_idh1_mutation__2": cohort.idh.eq("unknown"), "clin_idh2_mutation__2": cohort.idh.eq("unknown"),
                       "clin_mgmt_methylation__4": cohort.mgmt.eq("unknown")}
                X[c] = unk[c].astype(float).to_numpy() if c in unk else 0.0
        Xt = surv.transform_preprocessor(X[ok], bundle["preprocessor_state"])
        raw = surv.predict_positive_probability(bundle["classifier"], Xt)
        p = bundle["calibrator"].predict_proba(raw.reshape(-1, 1))[:, 1]
        c = cohort[ok].reset_index(drop=True)
        pm = point_metrics(c, p, H)
        b = cluster_bootstrap(c, {"m": p}, H, reference="m", n_boot=1000).iloc[0]
        rows.append({"variant": variant, "n_scans": int(ok.sum()), **pm, "auc_ipcw_lo": b.auc_ipcw_lo,
                     "auc_ipcw_hi": b.auc_ipcw_hi})
    res = pd.DataFrame(rows)
    res.to_csv(OUTPUTS / "external_lumiere" / "shipped_model.csv", index=False)
    print(res.round(3).to_string(index=False))


if __name__ == "__main__":
    main()


def adapt() -> None:
    """Raw vs adapted shipped model on held-out LUMIERE patients (grouped CV, per-fold AUC + pooled O/E)."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import roc_auc_score
    from sklearn.model_selection import StratifiedGroupKFold
    from prism.experiments.external_lumiere import SHRINK_LAMBDAS, shrink_fit

    cohort = pd.read_csv(OUTPUTS / "lumiere" / "cohort.csv")
    feats = pd.read_csv(OUTPUTS / "lumiere" / "legacy_radiomics.csv").set_index("scan_id").reindex(cohort.scan_id)
    bundle = pickle.load(open(RAD / "models" / "calibrated" / "model_bundle.pkl", "rb"))
    cols = bundle["selected_columns"]
    ok = feats[[c for c in cols if not c.startswith("clin_")]].notna().all(axis=1).to_numpy()
    c = cohort[ok].reset_index(drop=True)
    X = pd.DataFrame({k: (feats[k].to_numpy()[ok] if not k.startswith("clin_") else
                          ({"clin_idh1_mutation__2": c.idh.eq("unknown"), "clin_idh2_mutation__2": c.idh.eq("unknown"),
                            "clin_mgmt_methylation__4": c.mgmt.eq("unknown")}.get(k, pd.Series(False, index=c.index))
                           .astype(float).to_numpy())) for k in cols})
    Xs = np.asarray(surv.transform_preprocessor(X, bundle["preprocessor_state"]), dtype=float)
    clf = bundle["classifier"]
    beta0, b0 = clf.coef_[0], clf.intercept_[0]
    raw = bundle["calibrator"].predict_proba(surv.predict_positive_probability(clf, Xs).reshape(-1, 1))[:, 1]
    y = c[f"label_{H}"].to_numpy()
    strata = pd.Series(y).map({1.0: "p", 0.0: "n"}).fillna("c")
    lg = lambda p: np.log(np.clip(p, 1e-6, 1 - 1e-6) / (1 - np.clip(p, 1e-6, 1 - 1e-6)))
    arms = ("raw", "recalibrated", "finetune_shrink")
    oof = {a: np.zeros((5, len(c))) for a in arms}
    fold_auc = {a: [] for a in arms}
    for r in range(5):
        for tr, te in StratifiedGroupKFold(5, shuffle=True, random_state=r).split(Xs, strata, c.patient_id):
            k = tr[~np.isnan(y[tr])]
            oof["raw"][r, te] = raw[te]
            cal = LogisticRegression(C=1.0).fit(lg(raw[k])[:, None], y[k].astype(int))
            oof["recalibrated"][r, te] = 1 / (1 + np.exp(-(max(cal.coef_[0][0], 0.05) * lg(raw[te]) + cal.intercept_[0])))
            best, best_loss = SHRINK_LAMBDAS[-1], np.inf
            for lam in SHRINK_LAMBDAS:
                losses = []
                for itr, ite in StratifiedGroupKFold(3, shuffle=True, random_state=r).split(k, y[k], c.patient_id.iloc[k]):
                    bb, be = shrink_fit(Xs[k[itr]], y[k[itr]], beta0, b0, lam)
                    pz = 1 / (1 + np.exp(-(bb + Xs[k[ite]] @ be)))
                    losses.append(-np.mean(y[k[ite]] * np.log(pz + 1e-9) + (1 - y[k[ite]]) * np.log(1 - pz + 1e-9)))
                if np.mean(losses) < best_loss:
                    best, best_loss = lam, np.mean(losses)
            bb, be = shrink_fit(Xs[k], y[k], beta0, b0, best)
            oof["finetune_shrink"][r, te] = 1 / (1 + np.exp(-(bb + Xs[te] @ be)))
            kt = te[~np.isnan(y[te])]
            if len(np.unique(y[kt])) == 2:
                for a in arms:
                    fold_auc[a].append(roc_auc_score(y[kt], oof[a][r, kt]))
    rows = []
    for a in arms:
        pm = point_metrics(c, oof[a].mean(0), H)
        rows.append({"model": "PRISM report radiomics (shipped)", "arm": a, "auc_per_fold_mean": np.mean(fold_auc[a]),
                     "auc_per_fold_sd": np.std(fold_auc[a]), "auc_ipcw_pooled": pm["auc_ipcw"], "oe_ratio": pm["oe_ratio"],
                     "brier_ipcw": pm["brier_ipcw"]})
    res = pd.DataFrame(rows)
    res.to_csv(OUTPUTS / "external_lumiere" / "shipped_model_adaptation.csv", index=False)
    print(res.round(3).to_string(index=False))
