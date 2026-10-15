"""Deterministic report sections (no LLM), rendered from one report record and its facts.

1 Scan context  2 Inputs (value, source, as-of day)  3 Risk (interval, tier, conformal set)  4 Contributions by group
5 Referral flags with reasons  6 Volumetric change (indicative, not RANO)  7 Summary (LLM, grounded)  8 Limitations

Ported from the original PRISM report (legacy/glioma_agent): the longitudinal delta table (now real compartment
volumes vs prior and nadir, not the model's own probability), the explanation section (now exact additive log-odds
contributions of the deployed model), the confidence-tiered summary (now tertile tiers + interval) and the
decision-support disclaimer. Dropped: the probability-proxy "RANO 2.0" verdict, the RANO-AI concordance switch, the
fixed 0.48 alert threshold, the weighted confounder score, the hard-coded molecular placeholder table and the
ground-truth label column (see docs/results/REPORT_AGENT.md).
"""

from __future__ import annotations

from prism.report.facts import term_name


def _pc(v):
    return f"{v:+d}%" if isinstance(v, int) else "% " + v.replace("not computed ", "not computed: ").replace("(", "").replace(")", "")


def _fmt(v):
    return "missing" if v is None else f"{v:g}"


def limitations(F: dict) -> str:
    return (f"Limitations: model discrimination in development cross-validation AUC {F['model.cv_auc']:.2f} "
            "(single institution, MU-Glioma-Post); the risk is the probability of documented progression within 120 "
            "days, not a diagnosis of progression or pseudoprogression; volumes are indicative, not a RANO assessment.")


def render(rec: dict, F: dict, summary: list[str] | None = None, top: int = 6) -> str:
    pr, ex = rec["prediction"], rec["explanation"]
    L = [f"# PRISM surveillance report - {rec['scan_id']}", "",
         "## 1. Scan context",
         f"- Scan day {F['scan.day_from_diagnosis']} from diagnosis (calendar dates are not distributed with the "
         "de-identified data)",
         f"- Phase of care: {F['scan.phase_of_care']}",
         f"- Days since end of RT: {F['scan.days_since_rt_end']}",
         f"- Model: {rec['model']['source']}; all inputs known by the scan day: {F['inputs.all_known_by_scan_day']}", "",
         "## 2. Inputs (as of the scan day)", "", "| Input | Value | Unit | Source | As-of day | Note |",
         "|---|---|---|---|---|---|"]
    for i in rec["inputs"]:
        L.append(f"| {i['feature']} | {_fmt(i['value'])} | {i['unit']} | "
                 f"{i['source'].replace('MU clinical workbook column ', 'workbook: ')} | {i['as_of_day']:g} | {i['note']} |")
    L += ["", "## 3. Risk of documented progression within 120 days",
          f"- **{F['risk.value']:.2f}** (95% bootstrap interval {F['risk.interval_low']:.2f}-{F['risk.interval_high']:.2f})",
          f"- Tier: **{F['risk.tier']}** of development-cohort predictions (cut points {F['risk.tier_cut_lower']:.2f} "
          f"and {F['risk.tier_cut_upper']:.2f})",
          f"- 80% conformal prediction set: {F['risk.conformal_set']}", "",
          "## 4. What drove the estimate (exact additive log-odds)",
          f"- Intercept {ex['intercept']:+.2f}; clinical {F['contrib.clinical_logodds']:+.2f}; timing "
          f"{F['contrib.timing_logodds']:+.2f}; treatment {F['contrib.treatment_logodds']:+.2f}; imaging: "
          f"{F['contrib.imaging']}", f"- Sum = logit {ex['sum_check']['logit']:+.2f} (check error "
                                      f"{ex['sum_check']['abs_error']:.1e})", "",
          "| Term (value at this scan) | Group | Log-odds |", "|---|---|---|"]
    ins = {i["feature"]: i for i in rec["inputs"]}
    for t in ex["terms"][:top]:
        L.append(f"| {term_name(t['column'], ins)} | {t['group']} | {t['contribution_logodds']:+.2f} |")
    L += ["", "## 5. Referral flags"]
    act = [k.split(".")[1] for k in F if k.endswith(".active") and F[k] is True]
    L += [f"- **{n.replace('_', ' ')}**: {F[f'flags.{n}.reason']}" for n in act] or ["- none raised"]
    L += [f"- Action: {F['flags.action']}", "", "## 6. Volumetric change (indicative, not RANO)"]
    if not F["volume.available"]:
        L.append("- no measurements for this scan")
    else:
        L.append(f"- Enhancing {F['volume.enhancing_cc']:.1f} cc; FLAIR hyperintensity {F['volume.flair_hyperintensity_cc']:.1f} cc")
        if F["volume.prior_available"]:
            L += [f"- vs prior scan ({F['volume.days_since_prior']} d earlier): enhancing "
                  f"{F['volume.enhancing_change_since_prior_cc']:+.1f} cc ({_pc(F['volume.enhancing_change_since_prior_percent'])})",
                  f"- vs nadir ({F['volume.enhancing_nadir_cc']:.1f} cc): enhancing "
                  f"{F['volume.enhancing_change_since_nadir_cc']:+.1f} cc ({_pc(F['volume.enhancing_change_since_nadir_percent'])})",
                  f"- Indicative volumetric flag ({F['volume.indicative_rule']}): {F['volume.indicative_flag']}"]
        else:
            L.append("- first scan: no prior or nadir")
    L += ["", "## 7. Summary (generated from the fields above)"]
    L += [" ".join(summary)] if summary else ["- (not generated)"]
    L += ["", "## 8. " + limitations(F), ""]
    return "\n".join(L)
