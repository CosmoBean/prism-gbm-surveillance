#!/usr/bin/env python3
"""Apply the shipped PRISM report radiomics model (radiomics/models/calibrated) to LUMIERE, unchanged.

Images: DeepBraTumIA atlas-space skull-stripped CT1 and FLAIR (1 mm MNI); mask = union of DeepBraTumIA tumour labels.
Preprocessing and PyRadiomics settings are the legacy ones (train.preprocess_image + the training YAML).
The model's six MU-specific clinical code columns have no LUMIERE equivalent; two variants are reported:
  codes_as_unknown  IDH1/IDH2 "2" and MGMT "4" set when status is unknown, ATRX / 1p19q columns 0
  codes_zero        all six clinical columns 0

    python legacy/shipped_on_lumiere.py   # needs `prism lumiere` first and the legacy extra
    -> outputs/results/external_lumiere/{shipped_model.csv, shipped_model_adaptation.csv}
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

from prism.config import LUMIERE_COHORT, LUMIERE_ROOT as ROOT, OUTPUTS, REPO, RESULTS
from prism.models.metrics import cluster_bootstrap, point_metrics

RAD = REPO / "legacy" / "radiomics"
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
    cohort = pd.read_csv(LUMIERE_COHORT)
    if not EXTRACT.exists():
        wanted = {f"{p}/{d}" for p, d in zip(cohort.patient_id, cohort.date)}
        with zipfile.ZipFile(zp) as z:
            members = [m for m in z.namelist() if "DeepBraTumIA" in m and any(w in m for w in wanted)]
            z.extractall(EXTRACT, members)
    feats_path = OUTPUTS / "features" / "lumiere_legacy_radiomics.csv"
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
    res.to_csv(RESULTS / "external_lumiere" / "shipped_model.csv", index=False)
    print(res.round(3).to_string(index=False))



def adapt() -> None:
    """Raw vs adapted shipped model on held-out LUMIERE patients. Every arm (raw included) is scored with the same
    per-fold estimator over identical patient folds (IPCW AUC with cohort-level censoring weights, O/E, slope per
    fold, then averaged); raw is also reported pooled. Recalibration: unpenalised logistic on the logit."""
    from prism.experiments.external_lumiere import choose_shrink, lumiere_fold_ids, recalibrate, shrink_fit
    from prism.models.metrics import fold_mean_bootstrap, fold_mean_metrics

    cohort = pd.read_csv(LUMIERE_COHORT)
    feats = pd.read_csv(OUTPUTS / "features" / "lumiere_legacy_radiomics.csv").set_index("scan_id").reindex(cohort.scan_id)
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
    ids = lumiere_fold_ids(c)
    arms = ("raw", "recalibrated", "finetune_shrink")
    oof = {a: np.zeros(ids.shape) for a in arms}
    for r, f in enumerate(ids):
        for fk in np.unique(f):
            tr, te = np.where(f != fk)[0], np.where(f == fk)[0]
            k = tr[~np.isnan(y[tr])]
            oof["raw"][r, te] = raw[te]
            oof["recalibrated"][r, te], _ = recalibrate(raw[k], y[k], raw[te])
            bb, be = shrink_fit(Xs[k], y[k], beta0, b0, choose_shrink(Xs, y, k, c.patient_id, beta0, b0, r))
            oof["finetune_shrink"][r, te] = 1 / (1 + np.exp(-(bb + Xs[te] @ be)))
    fb = fold_mean_bootstrap(c, oof, ids, H, reference="raw", n_boot=1000).set_index("arm")
    rows = []
    for a in arms:
        row = {"model": "PRISM report radiomics (shipped)", "arm": a, "n_scans": len(c),
               **fold_mean_metrics(c, oof[a], ids, H), **fb.loc[a].dropna().to_dict()}
        if a == "raw":
            pm = point_metrics(c, raw, H)
            b = cluster_bootstrap(c, {"m": raw}, H, reference="m", n_boot=1000).iloc[0]
            row.update({f"{m}_pooled": v for m, v in pm.items()}, auc_ipcw_pooled_lo=b.auc_ipcw_lo,
                       auc_ipcw_pooled_hi=b.auc_ipcw_hi)
        rows.append(row)
    res = pd.DataFrame(rows)
    res.to_csv(RESULTS / "external_lumiere" / "shipped_model_adaptation.csv", index=False)
    print(res.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
    adapt()
