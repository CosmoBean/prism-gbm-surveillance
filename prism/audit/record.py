"""Per-scan audit record (JSON-serialisable dict) and a compact markdown render."""

from __future__ import annotations

import numpy as np
import pandas as pd

from prism.audit.model import GROUPS, Fitted, source_feature
from prism.audit.provenance import as_of
from prism.config import EARLY_POST_RT_DAYS

PHASE_TEXT = {"pre_rt": "pre-RT (no RT started by the scan day)", "during_rt": "during RT (started, not completed)",
              "early_post_rt": f"early post-RT (<= {EARLY_POST_RT_DAYS} d after RT end)",
              "later_post_rt": f"later post-RT (> {EARLY_POST_RT_DAYS} d after RT end)"}


def build(scan: pd.Series, x: pd.Series, index_row: pd.Series, fitted: Fitted, phase: str, interval: tuple,
          ood_reasons: list[str], conformal: dict, fit_info: dict, outcome: dict | None = None) -> dict:
    """scan = cohort row, x = raw feature row, conformal = {alpha: set string}."""
    X1 = x.to_frame().T.astype(float)
    contrib = fitted.contributions(X1).iloc[0]
    z = pd.Series(fitted.z(X1)[0], index=fitted.columns)
    logit = float(fitted.logit(X1)[0])
    total = fitted.intercept + float(contrib.sum())
    assert abs(total - logit) < 1e-8, (total, logit)
    p = 1 / (1 + np.exp(-logit))
    scan_day = float(scan["days_from_diagnosis_to_mri"])
    inputs = [as_of(f, x[f], scan_day, index_row) for f in fitted.raw_columns]
    flags = []
    if phase == "early_post_rt":
        flags.append({"flag": "early_post_rt_window", "reason": f"scan {scan['days_since_rt_end']:g} d after RT end "
                      f"(<= {EARLY_POST_RT_DAYS} d, RANO 2.0 pseudoprogression window)"})
    if ood_reasons:
        flags.append({"flag": "out_of_distribution", "reason": "; ".join(ood_reasons)})
    if conformal.get(0.2) == "{0, 1}":
        flags.append({"flag": "uncertain", "reason": "the alpha = 0.2 conformal prediction set contains both classes"})
    terms = [{"column": c, "group": fitted.group_of[c], "raw_feature": source_feature(c),
              "standardised_value": float(z[c]), "coef": float(fitted.coef[j]), "contribution_logodds": float(contrib[c])}
             for j, c in enumerate(fitted.columns)]
    rec = {
        "scan_id": scan["scan_id"], "patient_id": scan["patient_id"], "scan_day_from_diagnosis": scan_day,
        "phase_of_care": phase, "phase_text": PHASE_TEXT[phase],
        "inputs": inputs, "all_inputs_known_by_scan": all(i["known_by_scan"] for i in inputs),
        "prediction": {"risk_progression_within_120d": float(p), "logit": logit,
                       "interval_95": [float(interval[0]), float(interval[1])],
                       "interval_method": "2.5-97.5 percentiles over patient-cluster bootstrap refits of the training "
                                          "pipeline", "conformal_sets": {str(a): s for a, s in conformal.items()}},
        "explanation": {"intercept": fitted.intercept, "sum_check": {"intercept_plus_contributions": total,
                                                                      "logit": logit, "abs_error": abs(total - logit)},
                        "groups_logodds": {g: float(sum(t["contribution_logodds"] for t in terms if t["group"] == g))
                                           for g in GROUPS},
                        "terms": sorted(terms, key=lambda t: -abs(t["contribution_logodds"]))},
        "referral": {"refer": bool(flags), "flags": flags},
        "model": fit_info,
    }
    if outcome is not None:
        rec["evaluation_only_not_available_at_scan"] = outcome
    return rec


def render_md(rec: dict, top: int = 6) -> str:
    pr = rec["prediction"]
    ex = rec["explanation"]
    lines = [f"### {rec['scan_id']}  (day {rec['scan_day_from_diagnosis']:g} from diagnosis)",
             f"- **Phase of care:** {rec['phase_text']}",
             f"- **Risk of documented progression within 120 d:** {pr['risk_progression_within_120d']:.2f} "
             f"(95% bootstrap interval {pr['interval_95'][0]:.2f}–{pr['interval_95'][1]:.2f}); "
             f"conformal set α=0.2 {pr['conformal_sets'].get('0.2')}, α=0.1 {pr['conformal_sets'].get('0.1')}",
             "- **Referral:** " + ("REFER — " + "; ".join(f"{f['flag']}: {f['reason']}" for f in rec["referral"]["flags"])
                                   if rec["referral"]["refer"] else "no flag"),
             f"- **Log-odds:** intercept {ex['intercept']:+.2f} + clinical {ex['groups_logodds']['clinical']:+.2f} "
             f"+ timing {ex['groups_logodds']['timing']:+.2f} + treatment {ex['groups_logodds']['treatment']:+.2f} "
             f"= {ex['sum_check']['logit']:+.2f} (check error {ex['sum_check']['abs_error']:.1e})",
             f"- **Inputs known by scan day:** {'yes, all' if rec['all_inputs_known_by_scan'] else 'NO'}",
             "", "| Top terms | group | input | z | coef | log-odds |", "|---|---|---|---|---|---|"]
    vals = {i["feature"]: i for i in rec["inputs"]}
    for t in ex["terms"][:top]:
        v = vals.get(t["raw_feature"], {}).get("value")
        shown = "missing" if t["column"].startswith("missingindicator_") else ("missing (imputed)" if v is None else f"{v:g}")
        lines.append(f"| {t['column']} | {t['group']} | {shown} | {t['standardised_value']:+.2f} | {t['coef']:+.2f} | "
                     f"{t['contribution_logodds']:+.2f} |")
    lines += ["", "| Input | value | source | as-of day | note |", "|---|---|---|---|---|"]
    for i in rec["inputs"]:
        v = "missing" if i["value"] is None else f"{i['value']:g}"
        lines.append(f"| {i['feature']} | {v} | {i['source'].replace('MU clinical workbook column ', '')} | "
                     f"{i['as_of_day']:g} | {i['note']} |")
    if "evaluation_only_not_available_at_scan" in rec:
        o = rec["evaluation_only_not_available_at_scan"]
        lines += ["", f"*Evaluation only (not available at the scan):* 120-d label = {o['label_120']}, "
                      f"event = {o['event']}, time to event/censoring = {o['time_to_event']:g} d."]
    return "\n".join(lines) + "\n"
