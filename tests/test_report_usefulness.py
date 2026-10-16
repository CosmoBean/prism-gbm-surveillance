"""Unit tests for the v2 report facts, prompt output parsing, usefulness scoring and judge parsing (synthetic record)."""

import json

from prism.report import checker, judge, prompts, prompts_v2, style, usefulness
from prism.report.facts import facts
from prism.report.facts_v2 import facts_v2


def record(phase="early_post_rt", p=0.52, prior=True, flags=(("early_post_rt_window", "days_since_rt_end = 30 <= 84"),),
           known=True):
    ins = [{"feature": f, "value": v, "unit": u} for f, v, u in [
        ("age", 61, "years"), ("male", 1, "0/1"), ("idh_mutant", 0, "0/1"), ("idh_unknown", 0, "0/1"),
        ("mgmt_methylated", 1, "0/1"), ("mgmt_unknown", 0, "0/1"), ("rt_started", 1, "0/1"), ("rt_completed", 1, "0/1"),
        ("chemo_started", 1, "0/1"), ("rt_start_day", 30, "days")]]
    return {
        "scan_id": "P_1_T_2", "patient_id": "P_1", "scan_day_from_diagnosis": 120.0, "phase_of_care": phase,
        "days_since_rt_end": 30.0, "inputs": ins, "all_inputs_known_by_scan": known,
        "prediction": {"risk_progression_within_120d": p, "interval_95": [0.31, 0.70], "conformal_sets": {"0.2": "{0, 1}"}},
        "explanation": {"groups_logodds": {"clinical": -0.2, "timing": 0.3, "treatment": 0.1},
                        "terms": [{"column": "rt_start_day", "group": "treatment", "contribution_logodds": 0.4},
                                  {"column": "mgmt_methylated", "group": "clinical", "contribution_logodds": -0.3}]},
        "referral": {"flags": [{"flag": f, "reason": r} for f, r in flags], "refer": bool(flags)},
        "risk_tier": {"cuts": [0.30, 0.50]}, "imaging": {"available": False}, "model": {"cv_auc": 0.698},
        "context_v2": {"reference_mean": 0.41, "prior": {"scan_id": "P_1_T_1", "risk": 0.40, "days_before": 60.0}
                       if prior else None}}


def test_facts_v2_superset_and_fields():
    r = record()
    F1, F2 = facts(r), facts_v2(r)
    assert all(F2[k] == v for k, v in F1.items())
    assert F2["risk.statement"] == "52% (95% interval 31-70%) risk of documented progression within 120 days"
    assert F2["risk.relative_to_reference"] == "above" and F2["risk.reference_percent"] == 41
    assert F2["risk.change_since_prior_points"] == 12 and F2["risk.change_since_prior_direction"] == "higher"
    assert facts_v2(record(p=0.302))["risk.tier_position"] == "middle third (just above a tier boundary)"
    assert "inputs.lookahead_note" in facts_v2(record(known=False))
    assert not facts_v2(record(prior=False))["risk.prior_available"]


def test_risk_statement_citation_supports_horizon():
    F = facts_v2(record())
    ok = [{"text": "The model estimates a 52% (95% interval 31-70%) risk of documented progression within 120 days.",
           "fields": ["risk.statement"]}]
    v1_fail = [{"text": "The model estimates a 52% risk within 120 days (95% interval 31% to 70%).",
                "fields": ["risk.percent", "risk.interval_low_percent", "risk.interval_high_percent"]}]
    assert checker.check(ok, F)["n_unsupported"] == 0
    assert checker.check(v1_fail, F)["n_unsupported"] == 1  # the v1 failure mode: 120 not cited


def good_v2(F):
    return [
        {"section": "findings", "text": "Scan on day 120 from diagnosis, early post-RT, 30 days after the end of RT; in this "
         "window treatment-related change can look like progression on MRI.",
         "fields": ["scan.day_from_diagnosis", "scan.phase_of_care", "scan.days_since_rt_end", "phase.why_it_matters"]},
        {"section": "findings", "text": "The model estimates a 52% (95% interval 31-70%) risk of documented progression "
         "within 120 days.", "fields": ["risk.statement"]},
        {"section": "findings", "text": "This is in the upper third (cut points 30% and 50%), above the training-scan "
         "average of 41%.", "fields": ["risk.tier_position", "risk.tier_cut_lower_percent", "risk.tier_cut_upper_percent",
                                        "risk.relative_to_reference", "risk.reference_percent"]},
        {"section": "findings", "text": "Compared with the prior scan 60 days earlier, the risk is 12 points higher (was 40%).",
         "fields": ["risk.prior_days_before", "risk.change_since_prior_points", "risk.prior_percent"]},
        {"section": "findings", "text": "The largest contribution was RT start day, towards higher risk.",
         "fields": ["contrib.top1_name", "contrib.top1_direction"]},
        {"section": "findings", "text": "The model does not use the MRI images or tumour volumes.", "fields": ["model.not_used"]},
        {"section": "findings", "text": "The scan is flagged for clinician review: it is inside the 84-day early post-RT "
         "window where treatment effects can mimic progression; the 80% conformal set is uncertain, containing both outcomes.",
         "fields": ["flags.early_post_rt_window.reason", "flags.uncertain.reason", "flags.action"]},
        {"section": "impression", "text": "Estimated 52% (95% interval 31-70%) risk within 120 days, upper third, read in "
         "the early post-RT window.", "fields": ["risk.statement", "risk.tier_position", "flags.early_post_rt_window.reason"]},
    ]


def test_usefulness_complete_and_v2_parse():
    r = record(flags=(("early_post_rt_window", "x"), ("uncertain", "y")))
    F = facts_v2(r)
    cl = good_v2(F)
    raw = json.dumps({"sentences": cl})
    parsed = checker.parse_structured(raw)
    c = checker.check(parsed, F)
    assert c["pass"] and not c["any_forbidden"], c
    u = usefulness.score(parsed, F)
    assert u["complete"] and u["usefulness"] == 1.0, u
    assert not u["S1_false_reassurance"] and not u["S2_wording_mismatch"]
    assert u["U8_lookahead"] is None  # not applicable
    s = prompts_v2.sectioned(raw)
    assert len(s["impression"]) == 1 and prompts_v2.render_text(raw, "v2").startswith("FINDINGS:")


def test_usefulness_misses_and_safety():
    F = facts_v2(record(p=0.60))
    cl = [{"text": "The model estimates a 60% risk, which is reassuring and unlikely to matter.", "fields": ["risk.percent"]}]
    u = usefulness.score(cl, F)
    assert not u["U1_risk_complete"] and not u["U5_not_seen"] and not u["complete"]
    assert u["S1_false_reassurance"] and u["S2_wording_mismatch"]
    assert usefulness.score(None, F)["usefulness"] == 0.0


def test_style_and_judge_parse():
    assert 5 < style.fkgl("The model estimates the risk of documented progression within one hundred and twenty days. "
                          "It does not use the images.") < 15
    assert style.profile(["Findings: a lesion. Impression: possible tumour."])["hedge_sentence_share"]["possible/possibly"] == 0.5
    j = judge.parse('{"reason": "x", "preferred": "first"}')
    assert j["preferred"] == "first" and judge.parse("not json") is None
    assert set(judge.PAIR_SCHEMA["required"]) == {"reason", "preferred"}


def test_v1_prompt_unchanged():
    assert prompts.GROUNDED_SYSTEM.startswith("You write the narrative summary of a PRISM surveillance report")
    assert "risk.statement" not in prompts.GROUNDED_SYSTEM and prompts_v2.VERSION.startswith("v2")


def test_judge_regex_lines():
    import re
    t = "".join(f"{k}: 3 | A short reason.\n" for k in judge.RUBRIC)
    assert re.fullmatch(judge.ABS_REGEX, t) and judge.parse_absolute(t)["accuracy"]["score"] == 3
    assert judge.parse_absolute("accuracy: 3 | x\n") is None
