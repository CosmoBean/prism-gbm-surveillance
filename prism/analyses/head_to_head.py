"""Head-to-head on the PRISM report split (all gliomas): train once on the 127 training patients, test on the 30 test
patients of the PRISM report radiomics model, with the C3 pipelines (prism.experiments.c3_radiomics.fit_predict).

The PRISM report radiomics model enters with its shipped test-set probabilities
(legacy/radiomics/models/calibrated/test_predictions.csv), which also define the split. AUC against the naive label
(as in the PRISM report) and IPCW AUC(120 d) with a patient-cluster bootstrap CI over the 30 test patients.

    python -m prism head2head [--drop-mgmt-flag] [--n-boot 1000]
    -> outputs/results/c3/prism_report_split/head_to_head.csv   (head_to_head_masking_only.csv with --drop-mgmt-flag)

--drop-mgmt-flag removes the early-post-RT x MGMT-methylated flag from the timing block (the "masking only" ablation).

The two legacy rows can be (near-)identical; that is expected, not a bug. Univariate top-10 selection on all 2446 legacy
columns picks almost only 2-level texture: original-image texture (which "legacy texture" also offers) or its
wavelet-LLL twin (excluded from "legacy texture", r 0.93-0.99 with the original feature). On the 2026-10-11 data the
two top-10 sets share 7 features and the rows differ (IPCW AUC 0.840 vs 0.847); with other labels they can coincide.
"""

from __future__ import annotations

import argparse

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from prism.config import REPO, RESULTS
from prism.models.metrics import cluster_bootstrap, counted_warnings, point_metrics

H = 120
TEST_PREDICTIONS = REPO / "legacy" / "radiomics" / "models" / "calibrated" / "test_predictions.csv"
SHIPPED = "PRISM report radiomics model (as shipped)"
MODELS = {
    SHIPPED: None,
    "Baseline ridge": (None, "none", "none", "none", "ridge"),
    "Baseline boosting": (None, "none", "none", "none", "gbm"),
    "Baseline + legacy 2-level texture (top10)": ("legacy_texture", "none", "top10", "concat", "ridge"),
    "Baseline + legacy radiomics (top10)": ("legacy", "none", "top10", "concat", "ridge"),
    "Baseline + corrected compartments (ICC, top10, stacked)": ("v2_compartments", "icc", "top10", "stack", "ridge"),
}
MGMT_FLAG = "early_post_rt_x_mgmt_methylated"


@counted_warnings
def run(drop_mgmt_flag: bool, n_boot: int) -> pd.DataFrame:
    import prism.features.tabular as t
    if drop_mgmt_flag:
        _timing = t.timing
        t.timing = lambda c: _timing(c).drop(columns=MGMT_FLAG, errors="ignore")
    from prism.experiments import c3_radiomics as c3

    cohort, _, base, rad, er = c3.load("all_glioma")
    rad["legacy_texture"] = rad["legacy"].filter(regex=r"^[a-z0-9]+_(glcm|glrlm|glszm|gldm|ngtdm)_")
    tp = pd.read_csv(TEST_PREDICTIONS)
    tp["scan_id"] = tp.patient_id + "_" + tp.timepoint
    test = cohort.patient_id.isin(tp.patient_id).to_numpy()
    tr, te = np.where(~test)[0], np.where(test)[0]
    shipped = tp.set_index("scan_id").reindex(cohort.scan_id.iloc[te])
    if shipped.calibrated_probability.isna().any():
        raise ValueError("PRISM report test scans missing from the all-glioma cohort")
    d = cohort.iloc[te].reset_index(drop=True)
    preds = {name: (shipped.calibrated_probability.to_numpy() if cfg is None else
                    c3.fit_predict(cfg, cohort, base, rad, er, tr, te))
             for name, cfg in MODELS.items()}
    boot = cluster_bootstrap(d, preds, H, reference="Baseline ridge", n_boot=n_boot).set_index("formulation")
    rows = []
    for name, p in preds.items():
        pm = point_metrics(d, p, H)
        rows.append({"model": name, "n_train_patients": cohort.patient_id.iloc[tr].nunique(),
                     "n_test_patients": d.patient_id.nunique(), "n_test_scans": len(d),
                     "auc_naive_original": roc_auc_score(shipped.label, p), "auc_ipcw": pm["auc_ipcw"],
                     **boot.loc[name].dropna().to_dict(), "brier_ipcw": pm["brier_ipcw"]})
    return pd.DataFrame(rows)


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="prism head2head", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--drop-mgmt-flag", action="store_true")
    ap.add_argument("--n-boot", type=int, default=1000)
    a = ap.parse_args(argv)
    res = run(a.drop_mgmt_flag, a.n_boot)
    out = RESULTS / "c3" / "prism_report_split"
    out.mkdir(parents=True, exist_ok=True)
    name = "head_to_head_masking_only.csv" if a.drop_mgmt_flag else "head_to_head.csv"
    res.to_csv(out / name, index=False)
    cols = ["model", "auc_naive_original", "auc_ipcw", "auc_ipcw_lo", "auc_ipcw_hi", "d_auc_ipcw_vs_Baseline ridge",
            "d_auc_ipcw_lo", "d_auc_ipcw_hi"]
    print(f"train {res.n_train_patients.iat[0]} patients, test {res.n_test_patients.iat[0]} patients "
          f"({res.n_test_scans.iat[0]} scans) -> {out / name}")
    print(res[[c for c in cols if c in res]].round(3).to_string(index=False))
