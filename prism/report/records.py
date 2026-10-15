"""Per-scan report records: the audit record (prism.audit.record.build) for every out-of-fold scan of one CV repeat,
plus the two blocks the report needs and the audit layer does not store per scan:

  risk_tier   tertile cut points of the fold model's predicted risk on its own training scans (no test information)
  imaging     past-only compartment volumes and change since the prior scan and the nadir (measurements.csv), with the
              volumetric flag of BASELINES.md (B1), labelled indicative, not a RANO assessment

Inputs: the audit stage's cv_predictions_<pop>.csv.gz (bootstrap interval, conformal sets); the fold models are refitted
(deterministic) and their predictions must reproduce the stored risk to 1e-9. The outcome is NOT written into the
record; it goes to a separate evaluation-only table.
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

from prism.analyses.phase_ladder import phase_label
from prism.audit.model import design, fit_pipeline, ood_flags, ood_ranges
from prism.audit.record import build
from prism.config import MEASUREMENTS, RESULTS
from prism.data.mu import load_cohort, load_index
from prism.experiments import c3_radiomics as c3
from prism.features.measurements import PD_MIN_NADIR_CC
from prism.models.folds import load_folds

AUDIT = RESULTS / "analyses" / "audit_system"
VOL_COLS = ["et_cc", "snfh_cc", "netc_cc", "rc_cc", "has_prior", "days_since_prior", "d_et_cc", "d_snfh_cc",
            "d_nadir_et_cc", "d_nadir_snfh_cc", "vol_pd_flag", "et_new_from_zero_nadir", "n_prior_scans"]


def _pct(cur, old):
    return None if old is None or pd.isna(old) or old < 1.0 else float(100 * (cur - old) / old)


def imaging_block(m: pd.Series, scan_day: float) -> dict:
    """Volumes (cc) of the scan and past-only change; percentages only from a baseline >= 1 cc."""
    if m is None or pd.isna(m.get("et_cc")):
        return {"available": False}
    prior = bool(m["has_prior"] == 1)
    out = {"available": True, "source": "outputs/features/measurements.csv (MU-Glioma-Post masks; past-only deltas)",
           "as_of_day": scan_day, "et_cc": float(m.et_cc), "snfh_cc": float(m.snfh_cc), "netc_cc": float(m.netc_cc),
           "resection_cavity_cc": float(m.rc_cc), "prior_available": prior}
    if prior:
        et_prior, et_nadir = m.et_cc - m.d_et_cc, m.et_cc - m.d_nadir_et_cc
        sn_prior = m.snfh_cc - m.d_snfh_cc
        out.update({"n_prior_scans": int(m.n_prior_scans), "days_since_prior": float(m.days_since_prior),
                    "et_prior_cc": float(et_prior), "et_change_since_prior_cc": float(m.d_et_cc),
                    "et_change_since_prior_pct": _pct(m.et_cc, et_prior),
                    "et_nadir_cc": float(et_nadir), "et_change_since_nadir_cc": float(m.d_nadir_et_cc),
                    "et_change_since_nadir_pct": _pct(m.et_cc, et_nadir),
                    "snfh_change_since_prior_cc": float(m.d_snfh_cc), "snfh_change_since_prior_pct": _pct(m.snfh_cc, sn_prior),
                    "volumetric_flag": bool(m.vol_pd_flag == 1), "new_enhancement_from_zero_nadir": bool(m.et_new_from_zero_nadir == 1),
                    "volumetric_rule": f"enhancing volume >= 40% and >= 1 cc above the past-only nadir (nadir >= "
                                       f"{PD_MIN_NADIR_CC:g} cc), or >= 1 cc from a ~0 cc nadir (BASELINES.md B1)"})
    out["label"] = "indicative, not RANO"
    return out


def tier_cuts(p_train: np.ndarray) -> list[float]:
    return [float(np.quantile(p_train, 1 / 3)), float(np.quantile(p_train, 2 / 3))]


def build_records(pop: str = "grade4", repeat: int = 0, scans: set | None = None) -> tuple[list[dict], pd.DataFrame]:
    """Records for every out-of-fold scan of `repeat` (optionally only `scans`), and the evaluation-only outcomes."""
    cohort = load_cohort(pop)
    X, groups = design(cohort)
    phase = phase_label(cohort)
    folds = load_folds()
    index = load_index().set_index("scan_id")
    meas = pd.read_csv(MEASUREMENTS).set_index("scan_id")
    cv = pd.read_csv(AUDIT / f"cv_predictions_{pop}.csv.gz")
    cv = cv[cv.repeat == repeat].set_index("scan_id").loc[cohort.scan_id]
    f = c3._fold_ids(cohort, folds, repeat)
    y = cohort["label_120"].to_numpy(float)
    card = json.loads((AUDIT / f"model_card_{pop}.json").read_text())["cv_performance"]
    recs, outcomes, dev = [], [], 0.0
    for k in sorted(np.unique(f)):
        tr, te = np.where(f != k)[0], np.where(f == k)[0]
        m = fit_pipeline(X, cohort, tr, groups, seed=repeat)
        p_te = m.predict(X.iloc[te])
        dev = max(dev, float(np.abs(p_te - cv.risk.to_numpy()[te]).max()))
        cuts = tier_cuts(m.predict(X.iloc[tr]))
        ood = ood_flags(X.iloc[te], cohort.iloc[te], ood_ranges(X, tr))
        for j, i in enumerate(te):
            sid = cohort.scan_id.iat[i]
            if scans is not None and sid not in scans:
                continue
            c = cv.loc[sid]
            rec = build(cohort.iloc[i], X.iloc[i], index.loc[sid], m, phase[i], (c.risk_lo, c.risk_hi), ood[j],
                        {0.1: c["set_alpha_0.1"], 0.2: c["set_alpha_0.2"]},
                        {"source": f"out-of-fold fit, repeat {repeat}, fold {k} (patient not in training)", "C": m.C,
                         "population": pop, "cv_auc": card["auc_ipcw"], "cv_auc_95ci": card["auc_ipcw_95ci"],
                         "cv_auc_source": card["source"], "cv_auc_estimator": card["estimator"]})
            rec["days_since_rt_end"] = None if pd.isna(cohort.days_since_rt_end.iat[i]) else float(cohort.days_since_rt_end.iat[i])
            rec["risk_tier"] = {"cuts": cuts, "method": "tertiles of the fold model's predicted risk on its training scans"}
            rec["imaging"] = imaging_block(meas.loc[sid] if sid in meas.index else None,
                                           float(cohort.days_from_diagnosis_to_mri.iat[i]))
            recs.append(rec)
            outcomes.append({"scan_id": sid, "patient_id": cohort.patient_id.iat[i], "phase": phase[i],
                             "label_120": y[i], "event": bool(cohort.event.iat[i]),
                             "time_to_event": float(cohort.time_to_event.iat[i])})
    if dev > 1e-9:
        raise RuntimeError(f"refitted fold models differ from cv_predictions_{pop} by {dev:.2e}")
    return recs, pd.DataFrame(outcomes).assign(max_abs_dev_vs_audit_cv=dev)
