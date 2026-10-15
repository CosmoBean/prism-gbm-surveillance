"""Report facts: a flat {field key: value} view of ONE report record, rounded to display precision.

This is the only thing the report text (deterministic sections and the LLM summary) is written from, and the only
thing the faithfulness checker compares against. No outcome, no other scan, no cohort statistic outside the record.
Numbers are pre-rounded here (risk 2 dp, log-odds 2 dp, volumes 1 dp, percentages and days 0 dp) so that "copied
from a field" is a well-defined check.
"""

from __future__ import annotations

PHASES = {"pre_rt": "pre-RT (radiotherapy not yet started)", "during_rt": "during RT (started, not completed)",
          "early_post_rt": "early post-RT (0-84 days after the end of radiotherapy)",
          "later_post_rt": "later post-RT (more than 84 days after the end of radiotherapy)"}
TIERS = ("lower third", "middle third", "upper third")

LABELS = {  # preprocessed column -> plain name
    "age": "age at diagnosis", "male": "male sex", "idh_mutant": "IDH mutant", "idh_unknown": "IDH status unknown",
    "mgmt_methylated": "MGMT methylated", "mgmt_unknown": "MGMT status unknown",
    "days_from_diagnosis": "days from diagnosis to scan", "days_since_rt_end": "days since end of RT",
    "rt_date_unknown": "no completed RT with known end date", "early_post_rt": "within 84 days after RT end",
    "early_post_rt_x_mgmt_methylated": "early post-RT x MGMT methylated", "visit_index": "scan number",
    "rt_started": "RT started", "rt_completed": "RT completed", "rt_dose_gy": "RT dose", "rt_fractions": "RT fractions",
    "rt_hypofractionated": "hypofractionated RT", "rt_start_day": "RT start day", "rt_duration_days": "RT duration",
    "chemo_started": "chemotherapy started", "surgery_day": "day of first surgery",
    "biopsy_before_resection": "biopsy before resection", "previous_brain_tumor": "previous brain tumour"}
OOD_NAMES = {"rt_start_day": "RT start day", "days_since_rt_end": "days since RT end", "surgery_day": "surgery day",
             "age": "age", "days_from_diagnosis": "days from diagnosis", "visit_index": "scan number",
             "rt_dose_gy": "RT dose (Gy)", "rt_fractions": "RT fractions", "rt_duration_days": "RT duration (days)"}


def label(col: str) -> str:
    if col.startswith("missingindicator_"):
        return LABELS.get(col.removeprefix("missingindicator_"), col) + " not recorded"
    return LABELS.get(col, col)


def term_name(col: str, ins: dict) -> str:
    """Plain name with the scan's value: 'RT start day = 48', 'RT completed: yes', 'MGMT status unknown: no'."""
    if col.startswith("missingindicator_"):
        return label(col)
    v = ins.get(col, {}).get("value")
    if v is None:
        return label(col) + ": not recorded (imputed)"
    if ins[col]["unit"].startswith("0/1"):
        return label(col) + (": yes" if v == 1 else ": no")
    return f"{label(col)} = {v:g}"


def r2(x):
    return None if x is None else round(float(x), 2)


def r1(x):
    return None if x is None else round(float(x), 1)


def r0(x):
    return None if x is None else int(round(float(x)))


def tier_of(p: float, cuts) -> str:
    return TIERS[int(p >= cuts[0]) + int(p >= cuts[1])]


def _ood_text(reason: str) -> str:
    """'rt_start_day = 48 outside training 1-99% [-12, 45]' -> plain words (numbers kept)."""
    import re
    m = re.match(r"(\w+) = (\S+) outside training 1-99% \[(\S+), (\S+)\]", reason)
    if not m:
        return reason
    f, v, lo, hi = m.groups()
    rd = lambda s: f"{round(float(s)):g}"
    return f"{OOD_NAMES.get(f, f)} {rd(v)} is outside the training range ({rd(lo)} to {rd(hi)}, 1st-99th percentile)"


def facts(rec: dict, n_terms: int = 3) -> dict:
    pr, ex = rec["prediction"], rec["explanation"]
    p = pr["risk_progression_within_120d"]
    lo, hi = pr["interval_95"]
    cuts = rec["risk_tier"]["cuts"]
    flags = {f["flag"]: f["reason"] for f in rec["referral"]["flags"]}
    ins = {i["feature"]: i for i in rec["inputs"]}
    v = lambda f: ins[f]["value"]
    F = {
        "scan.day_from_diagnosis": r0(rec["scan_day_from_diagnosis"]),
        "scan.phase_of_care": PHASES[rec["phase_of_care"]],
        "scan.days_since_rt_end": r0(rec["days_since_rt_end"]) if rec.get("days_since_rt_end") is not None
        and rec["phase_of_care"] in ("early_post_rt", "later_post_rt") else "not applicable (RT not completed)",
        "risk.horizon_days": 120,
        "risk.outcome": "documented progression within 120 days after this scan",
        "risk.value": r2(p), "risk.percent": r0(100 * p),
        "risk.interval_low": r2(lo), "risk.interval_high": r2(hi),
        "risk.interval_low_percent": r0(100 * lo), "risk.interval_high_percent": r0(100 * hi), "risk.interval_level_percent": 95,
        "risk.tier": tier_of(p, cuts),
        "risk.tier_cut_lower": r2(cuts[0]), "risk.tier_cut_upper": r2(cuts[1]),
        "risk.conformal_set": {"{0, 1}": "both outcomes (progression and no progression)", "{0}": "no progression only",
                               "{1}": "progression only", "{}": "empty"}[pr["conformal_sets"]["0.2"]],
        "risk.conformal_level_percent": 80,
        "contrib.clinical_logodds": r2(ex["groups_logodds"]["clinical"]),
        "contrib.timing_logodds": r2(ex["groups_logodds"]["timing"]),
        "contrib.treatment_logodds": r2(ex["groups_logodds"]["treatment"]),
        "contrib.imaging": "not part of this model (imaging branches added no measurable value in development)",
    }
    for j, t in enumerate(ex["terms"][:n_terms], 1):
        F[f"contrib.top{j}_name"] = term_name(t["column"], ins)
        F[f"contrib.top{j}_group"] = t["group"]
        F[f"contrib.top{j}_logodds"] = r2(t["contribution_logodds"])
        F[f"contrib.top{j}_direction"] = "towards higher risk" if t["contribution_logodds"] > 0 else "towards lower risk"
    F.update({
        "inputs.age_years": r0(v("age")), "inputs.sex": "male" if v("male") == 1 else "female",
        "inputs.idh": "unknown" if v("idh_unknown") == 1 else ("mutant" if v("idh_mutant") == 1 else "wildtype"),
        "inputs.mgmt": "unknown" if v("mgmt_unknown") == 1 else ("methylated" if v("mgmt_methylated") == 1 else "unmethylated"),
        "inputs.rt_started": "yes" if v("rt_started") == 1 else "no",
        "inputs.rt_completed": "yes" if v("rt_completed") == 1 else "no",
        "inputs.chemo_started": "yes" if v("chemo_started") == 1 else "no",
        "inputs.all_known_by_scan_day": "yes" if rec["all_inputs_known_by_scan"] else "no",
    })
    names = {"early_post_rt_window": "early_post_rt_window", "out_of_distribution": "out_of_distribution",
             "uncertain": "uncertain"}
    reasons = {"early_post_rt_window": lambda r: f"scan {F['scan.days_since_rt_end']} days after the end of RT, inside "
                                                 "the 84-day early post-RT window where treatment effects can mimic "
                                                 "progression",
               "out_of_distribution": lambda r: "; ".join(_ood_text(x) for x in r.split("; ")),
               "uncertain": lambda r: "the 80% conformal prediction set contains both outcomes"}
    for k, n in names.items():
        F[f"flags.{n}.active"] = k in flags
        F[f"flags.{n}.reason"] = reasons[k](flags[k]) if k in flags else "not raised"
    F["flags.any_active"] = bool(flags)
    F["flags.action"] = "flagged for clinician review" if flags else "no referral flag"
    im = rec["imaging"]
    F["volume.available"] = bool(im.get("available"))
    if im.get("available"):
        F["volume.label"] = "indicative, not RANO"
        F["volume.enhancing_cc"] = r1(im["et_cc"])
        F["volume.flair_hyperintensity_cc"] = r1(im["snfh_cc"])
        F["volume.prior_available"] = im["prior_available"]
        if im["prior_available"]:
            F["volume.days_since_prior"] = r0(im["days_since_prior"])
            F["volume.enhancing_change_since_prior_cc"] = r1(im["et_change_since_prior_cc"])
            F["volume.enhancing_change_since_prior_percent"] = r0(im["et_change_since_prior_pct"]) \
                if im["et_change_since_prior_pct"] is not None else "not computed (prior below 1 cc)"
            F["volume.enhancing_nadir_cc"] = r1(im["et_nadir_cc"])
            F["volume.enhancing_change_since_nadir_cc"] = r1(im["et_change_since_nadir_cc"])
            F["volume.enhancing_change_since_nadir_percent"] = r0(im["et_change_since_nadir_pct"]) \
                if im["et_change_since_nadir_pct"] is not None else "not computed (nadir below 1 cc)"
            F["volume.flair_change_since_prior_cc"] = r1(im["snfh_change_since_prior_cc"])
            F["volume.indicative_flag"] = "met" if im["volumetric_flag"] or im["new_enhancement_from_zero_nadir"] \
                else "not met"
            F["volume.indicative_rule"] = ("enhancing volume at least 40% and at least 1 cc above the nadir of earlier "
                                           "scans, or at least 1 cc of new enhancement from a nadir near 0 cc")
    F["model.cv_auc"] = r2(rec["model"]["cv_auc"])
    F["model.intended_use"] = ("decision support alongside, not instead of, the clinical and radiological assessment; "
                               "not a diagnosis")
    return F


def active_flags(F: dict) -> list[str]:
    return [k.split(".")[1] for k, v in F.items() if k.startswith("flags.") and k.endswith(".active") and v is True]
