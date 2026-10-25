"""UCSF-ALPTDG image measurements computed exactly as for MU, so MU-trained image models can be applied unchanged.

UCSF ships BraTS-space (240x240x155, 1 mm, skull-stripped) NIfTIs with one consecutive post-treatment pair per patient
(time1, time2). Its seg labels follow the same BraTS post-treatment convention as MU (1 = NCR / MU NETC, 2 = SNFH,
3 = ET, 4 = RC), so prism.features.measurements.concepts_from_paths is used as is. Only image files, SubjectID /
timepoint and the xlsx volume columns (for the agreement check) are read: no clinical data, no labels.

Change features: time2 vs time1. time1 has no earlier scan in this dataset (has_prev = 0, change = 0, nadir = itself),
whereas MU scans usually have earlier history. Scan order is an ordinal day (time1 = 0, time2 = 1): features that need
real days (days_since_prior, rate_*) are not computed.

    PYTHONPATH=. .venv/bin/python -m prism.features.ucsf_imaging   # -> outputs/data/ucsf/imaging_features.csv
"""

from __future__ import annotations

import os
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import nibabel as nib
import numpy as np
import pandas as pd

from prism.config import LABEL_ET, LABEL_NETC, LABEL_RC, LABEL_SNFH, MEASUREMENTS, OUTPUTS, WORKERS
from prism.features.measurements import add_deltas, concepts_from_paths

UCSF_ROOT = Path(os.environ.get("PRISM_UCSF_ROOT", "/project/community/sbandred/ucsf"))
UCSF_XLSX = UCSF_ROOT / "UCSF_PostopGlioma_Table S1 R1 V5.0_UNBLINDED_FINAL.xlsx"
OUT = OUTPUTS / "data" / "ucsf"
FEATURES = OUT / "imaging_features.csv"
# xlsx volume column -> label set (the column names say WT = 1+2+3, TC = 1+2; the values are WT = 1+2+3+4, TC = 1+3).
XLSX_VOLUMES = {"NCR_Volume_Label1": (LABEL_NETC,), "SNFH_Volume_Label2": (LABEL_SNFH,), "ET_Volume_Label3": (LABEL_ET,),
                "RC_Volume_Label4": (LABEL_RC,), "WT_Volume_Label1+2+3": (1, 2, 3, 4), "TC_Volume_Label_1+2": (1, 3)}
SUB_SEGS = ("t1ce_subtraction_seg", "flair_subtraction_seg")
DAY_DEPENDENT = ("days_since_prior",)  # plus every rate_* column


def ucsf_paths(sid: str, tp: int) -> dict[str, Path]:
    d, stem = UCSF_ROOT / sid, f"{sid}_time{tp}"
    return {"t1": d / f"{stem}_t1.nii.gz", "t1c": d / f"{stem}_t1ce.nii.gz", "t2": d / f"{stem}_t2.nii.gz",
            "flair": d / f"{stem}_flair.nii.gz", "mask": d / f"{stem}_seg.nii.gz"}


def subjects() -> list[str]:
    return sorted(p.name for p in UCSF_ROOT.iterdir() if p.is_dir() and p.name.isdigit())


def _scan(args: tuple[str, int]) -> dict:
    sid, tp = args
    row = concepts_from_paths(ucsf_paths(sid, tp), {"scan_id": f"{sid}_time{tp}", "patient_id": sid,
                                                    "timepoint": f"time{tp}"})
    mask = np.rint(np.asarray(nib.load(str(ucsf_paths(sid, tp)["mask"])).dataobj)).astype(np.int16)
    row.update({f"vox_label{k}": int((mask == k).sum()) for k in range(5)})
    row["vox_label_other"] = int((~np.isin(mask, range(5))).sum())
    if tp == 2:  # subtraction segs (time1 -> time2): voxel count per label value
        for s in SUB_SEGS:
            a = np.rint(np.asarray(nib.load(str(UCSF_ROOT / sid / f"{sid}_{s}.nii.gz")).dataobj)).astype(np.int16)
            v, c = np.unique(a[a != 0], return_counts=True)
            row.update({f"{s}_vox{int(k)}": int(n) for k, n in zip(v, c)})
    return row


def change_features(meas: pd.DataFrame) -> pd.DataFrame:
    """The I_pure / LUMIERE change inputs, as prism.analyses.detection.change_nadir and the exploratory scripts build
    them: log((cur + 0.1) / (prev + 0.1)) per volume (0 without a previous scan) and the log ratio of ET / lesion to
    the smallest volume over the whole history including the scan (triage_feasibility._features_one, window -inf)."""
    from prism.analyses.detection import EPS, VOLS
    from prism.analyses.triage_feasibility import _features_one
    rows = []
    for pid, g in meas.sort_values(["patient_id", "mri_day"]).groupby("patient_id", sort=False):
        for i in range(len(g)):
            cur, day = g.iloc[i], g.mri_day.iat[i]
            prev = g[g.mri_day < day]  # strictly earlier, as change_nadir
            r = {"scan_id": cur.scan_id, "has_prev": float(len(prev) > 0)}
            p = prev.iloc[-1] if len(prev) else None
            lr = lambda a, b: float(np.log((a + EPS) / (b + EPS))) if p is not None else 0.0
            for v in VOLS:
                r[f"logratio_prev_{v}"] = lr(cur[f"{v}_cc"], p[f"{v}_cc"] if p is not None else np.nan)
            r["logratio_prev_necrosis_cavity"] = lr(cur.netc_cc + cur.rc_cc,
                                                    p.netc_cc + p.rc_cc if p is not None else np.nan)
            f = _features_one(pd.concat([prev, g.iloc[[i]]]), day, -np.inf)
            r["nadir_all_et"], r["nadir_all_lesion"] = f["traj_logratio_nadir_et"], f["traj_logratio_nadir_lesion"]
            rows.append(r)
    return pd.DataFrame(rows)


def model_inputs(meas: pd.DataFrame) -> pd.DataFrame:
    """Model-ready columns of the image-only arms: measurement_groups volumes + morphology (I_scan), the change inputs
    (I_pure adds logratio_prev_{et,netc,snfh,rc,tumor,lesion} + nadir_all_{et,lesion}) and the LUMIERE image inputs
    (log_et_cc, log_necrosis_cavity_cc, log_snfh_cc, logratio_prev_{et,necrosis_cavity,snfh})."""
    from prism.features.tabular import measurement_groups
    cohort = meas[["scan_id"]].reset_index(drop=True)
    # Only volumes + morphology are used; the "delta" group needs days, so give it a placeholder when they are absent.
    mg = measurement_groups(cohort, meas if "days_since_prior" in meas else meas.assign(days_since_prior=np.nan))
    ch = change_features(meas).set_index("scan_id").reindex(cohort.scan_id).reset_index(drop=True)
    lum = pd.DataFrame({"log_necrosis_cavity_cc": np.log1p((meas.netc_cc + meas.rc_cc).to_numpy())})
    return pd.concat([cohort, mg["volumes"], mg["morphology"], lum, ch], axis=1)


def agreement(meas: pd.DataFrame) -> pd.DataFrame:
    """Our label voxel counts vs the xlsx volume columns (mm^3 = voxels at 1 mm)."""
    x = pd.read_excel(UCSF_XLSX, sheet_name="UCSF-LPTDG", usecols=["Full ID", *XLSX_VOLUMES])
    m = meas.set_index("scan_id").reindex(x["Full ID"].astype(str))
    rows = []
    for col, labels in XLSX_VOLUMES.items():
        ours = sum(m[f"vox_label{k}"] for k in labels).to_numpy(float)
        ref = x[col].to_numpy(float)
        ok = ~np.isnan(ref)
        rows.append({"xlsx_column": col, "labels": "+".join(map(str, labels)), "n_filled": int(ok.sum()),
                     "pearson": float(np.corrcoef(ours[ok], ref[ok])[0, 1]),
                     "spearman": float(pd.Series(ours[ok]).corr(pd.Series(ref[ok]), method="spearman")),
                     "n_exact": int((ours[ok] == ref[ok]).sum()),
                     "median_abs_diff_mm3": float(np.median(np.abs(ours[ok] - ref[ok]))),
                     "max_abs_diff_mm3": float(np.max(np.abs(ours[ok] - ref[ok]))),
                     "n_blank": int((~ok).sum()), "n_blank_and_label_empty": int((~ok & (ours == 0)).sum()),
                     "n_filled_but_label_empty": int((ok & (ours == 0)).sum()),
                     "n_filled_zero": int((ok & (ref == 0)).sum())})
    return pd.DataFrame(rows)


def subtraction_check(out: pd.DataFrame) -> pd.DataFrame:
    """Descriptive: subtraction-seg increase (1) / decrease (2) voxels vs the xlsx Inc / Dec columns and vs our
    time2 - time1 compartment change (ET <-> t1ce, SNFH <-> flair)."""
    x = pd.read_excel(UCSF_XLSX, sheet_name="UCSF-LPTDG").set_index("Full ID")
    x.columns = [*x.columns[:-1], "ET_OverallChange_Volume"]  # the last header is a duplicate "SNFH_..." in the xlsx
    t = out[out.timepoint.eq("time2")].set_index("scan_id").join(x[[c for c in x if c.endswith("crease_Volume") or
                                                                     "_Inc_" in c or "_Dec_" in c or "Overall" in c]])
    rows = []
    for comp, seg in (("ET", "t1ce"), ("SNFH", "flair")):
        inc, dec = (t.get(f"{seg}_subtraction_seg_vox{k}", pd.Series(0, index=t.index)).fillna(0) for k in (1, 2))
        net, ours = inc - dec, t[f"d_{comp.lower()}_cc"] * 1000
        nz = (inc + dec) > 0
        rows.append({"compartment": comp, "n_pairs": len(t), "n_subtraction_nonempty": int(nz.sum()),
                     "inc_equals_xlsx": float((inc == t[f"{comp}_Inc_Volume"]).mean()),
                     "dec_equals_xlsx": float((dec == t[f"{comp}_Dec_Volume"]).mean()),
                     "spearman_net_vs_our_delta": net.corr(ours, method="spearman"),
                     "pearson_net_vs_our_delta": net.corr(ours),
                     "sign_agreement_nonempty": float((np.sign(net) == np.sign(ours))[nz].mean()),
                     "median_abs_net_nonempty_mm3": float(net[nz].abs().median()),
                     "median_abs_our_delta_nonempty_mm3": float(ours[nz].abs().median()),
                     "median_abs_our_delta_empty_mm3": float(ours[~nz].abs().median()),
                     "q75_abs_our_delta_empty_mm3": float(ours[~nz].abs().quantile(0.75))})
    return pd.DataFrame(rows)


def distribution_shift(ucsf: pd.DataFrame) -> pd.DataFrame:
    """Median and IQR of every model input, all MU timepoints vs all UCSF scans (no labels)."""
    mu = model_inputs(pd.read_csv(MEASUREMENTS))
    rows = []
    for c in ucsf.columns.drop("scan_id"):
        a, b = mu[c], ucsf[c]
        if c.startswith(("logratio_prev_", "nadir_all_")):  # change: scans with a previous scan only
            a, b = a[mu.has_prev.eq(1)], b[ucsf.has_prev.eq(1)]
        a, b = a.dropna(), b.dropna()
        q = lambda s: s.quantile([0.25, 0.5, 0.75]).to_numpy() if len(s) else np.full(3, np.nan)
        (a1, a2, a3), (b1, b2, b3) = q(a), q(b)
        iqr = a3 - a1
        rows.append({"feature": c, "mu_n": len(a), "mu_median": a2, "mu_q25": a1, "mu_q75": a3, "ucsf_n": len(b),
                     "ucsf_median": b2, "ucsf_q25": b1, "ucsf_q75": b3,
                     "shift_in_mu_iqr": (b2 - a2) / iqr if iqr > 0 else np.nan,
                     "mu_missing_frac": float(mu[c].isna().mean()), "ucsf_missing_frac": float(ucsf[c].isna().mean())})
    return pd.DataFrame(rows)


# (pattern, group, description); first match wins. Arms: I_scan = volumes + morphology; I_pure = I_scan + change.
DICTIONARY = [
    (r"^scan_id$", "id", "<SubjectID>_time<1|2>"), (r"^SubjectID$", "id", "UCSF SubjectID"),
    (r"^timepoint$", "id", "time1 or time2 (time2 is the later scan of the pair)"),
    (r"^(et|netc|snfh|rc)_cc$", "raw", "compartment volume in cc (label 3 ET, 1 NCR = MU NETC, 2 SNFH, 4 RC)"),
    (r"^tumor_cc$", "raw", "ET + NETC, cc (cavity excluded)"), (r"^lesion_cc$", "raw", "ET + NETC + SNFH, cc"),
    (r"^snfh_to_tumor_ratio$", "raw", "SNFH / tumour volume (NaN if tumour = 0)"),
    (r"^et_max_axial_mm2$", "raw", "largest single axial-slice ET area, mm^2"),
    (r"^et_cavity_distance_mm_p50$", "raw", "median distance of ET voxels to the cavity, mm"),
    (r"^vox_label(\d)$", "check", "voxel count of seg label (mm^3)"),
    (r"^vox_label_other$", "check", "voxels with a label outside 0-4 (expected 0)"),
    (r"^(t1ce|flair)_subtraction_seg_vox(\d)$", "check", "time2 only: voxels of the subtraction seg with this value "
     "(1 = increase, 2 = decrease: equal to the xlsx Inc / Dec volumes; t1ce value 3 is a 1-2 voxel artefact in 4)"),
    (r"^logratio_prev_necrosis_cavity$", "LUMIERE", "log((cur + 0.1) / (prev + 0.1)) of NETC + RC; 0 at time1"),
    (r"^logratio_prev_", "I_pure (et/snfh also LUMIERE)", "log((cur + 0.1) / (prev + 0.1)) cc; 0 at time1"),
    (r"^(has_prior|n_prior_scans)$", "measurements.add_deltas", "earlier scan within UCSF (time2 = 1)"),
    (r"^(d|logratio)_nadir_", "measurements.add_deltas", "change vs the smallest earlier volume (time2: = time1)"),
    (r"^(d|logratio)_", "measurements.add_deltas", "change vs the previous scan (time2 - time1; NaN at time1)"),
    (r"^(vol_pd_flag|et_new_from_zero_nadir|new_et_component)$", "measurements.add_deltas",
     "RANO-style volumetric flags vs time1 (NaN at time1)"),
    (r"^log_(et|netc|snfh|rc|tumor|lesion)_cc$", "I_scan: volumes", "log1p(cc); log_et/snfh_cc are also LUMIERE inputs"),
    (r"^log_necrosis_cavity_cc$", "LUMIERE", "log1p(NETC + RC cc), harmonised with DeepBraTumIA necrotic"),
    (r"^nadir_all_(et|lesion)$", "I_pure", "log(cur + 0.1) - min over the history incl. the scan; 0 at time1"),
    (r"^has_prev$", "LUMIERE T (not image-only)", "1 if a previous scan exists (time2)"),
    (r".", "I_scan: morphology", "as measurement_groups()['morphology'] (prism/features/measurements.py)"),
]


def column_dictionary(cols) -> pd.DataFrame:
    import re
    rows = []
    for c in cols:
        g, d = next((g, d) for p, g, d in DICTIONARY if re.search(p, c))
        rows.append({"column": c, "group": g, "description": d})
    return pd.DataFrame(rows)


def main(argv=None) -> None:
    jobs = [(s, t) for s in subjects() for t in (1, 2)]
    with ProcessPoolExecutor(min(WORKERS, 48)) as ex:
        raw = pd.DataFrame(list(ex.map(_scan, jobs, chunksize=2)))
    assert raw.et_cc.notna().all(), "a UCSF scan failed to load"
    raw["mri_day"] = raw.timepoint.map({"time1": 0.0, "time2": 1.0})  # ordinal: order only, not days
    deltas = add_deltas(raw[[c for c in raw if not c.startswith(("vox_", "t1ce_sub", "flair_sub"))]])
    deltas = deltas.drop(columns=[c for c in deltas if c in DAY_DEPENDENT or c.startswith("rate_")])
    meas = raw.merge(deltas, on="scan_id", how="left")
    X = model_inputs(meas)
    keep = [c for c in meas if c not in X or c == "scan_id"]
    out = meas[keep].merge(X, on="scan_id")
    out.insert(1, "SubjectID", out.pop("patient_id"))
    OUT.mkdir(parents=True, exist_ok=True)
    out.drop(columns="mri_day").to_csv(FEATURES, index=False)
    column_dictionary(out.columns.drop("mri_day")).to_csv(OUT / "imaging_features_dictionary.csv", index=False)
    ag = agreement(meas)
    ag.to_csv(OUT / "imaging_volume_agreement.csv", index=False)
    sc = subtraction_check(out)
    sc.to_csv(OUT / "imaging_subtraction_check.csv", index=False)
    print(sc.round(3).T.to_string())
    sh = distribution_shift(X)
    sh.to_csv(OUT / "imaging_shift_mu_vs_ucsf.csv", index=False)
    print(f"{len(out)} scans, {out.shape[1]} columns -> {FEATURES}")
    print(ag.round(4).to_string())
    print(sh.round(3).to_string())


if __name__ == "__main__":
    main()
