"""Report facts v2: the v1 facts (prism.report.facts.facts, unchanged) plus the fields a reader needs to use the risk
next to the probability. v1 is untouched; v2 only adds keys, so the v1 checker runs on v2 facts unchanged.

Added (all from the record and its `context_v2` block; no outcome of the scan, no other cohort statistic):
  risk.reference_percent      average model-estimated risk over the fold model's own training scans (no labels)
  risk.relative_to_reference  "above" / "below" / "close to" (within 5 percentage points), precomputed in words
  risk.tier_cut_lower_percent / risk.tier_cut_upper_percent and risk.tier_position (fixes the v1 display issue where
                              risk and cut point round to the same 2-dp value)
  risk.statement              the risk sentence's anchor: "<p>% (95% interval <lo>-<hi>%) within 120 days"
  risk.position_statement     tier with cut points and the comparison with the training-scan average, in words
  risk.prior_percent, risk.prior_days_before, risk.change_since_prior_points, risk.change_since_prior_direction
                              out-of-fold risk of the same patient's previous scan (same CV repeat and fold; past-only),
  risk.prior_statement        and the same in words
  phase.why_it_matters        fixed text per phase of care (why the phase changes how the risk is read)
  model.inputs_used / model.not_used
                              what the model saw and what it did not (images, volumes, steroids, symptoms, ...)
  inputs.lookahead_note       when an input was not known by the scan day
"""

from __future__ import annotations

from prism.report.facts import facts, r0

PHASE_WHY = {
    "pre_rt": "before radiotherapy the scan is a post-surgical baseline, before any response to radiotherapy can be "
              "seen",
    "during_rt": "during radiotherapy, treatment has started but its effect cannot yet be judged; the estimate rests "
                 "on clinical, timing and treatment inputs",
    "early_post_rt": "in the first 84 days after radiotherapy, treatment-related change can look like progression on "
                     "MRI; the model does not read the images, so its estimate cannot separate the two",
    "later_post_rt": "more than 84 days after radiotherapy, early treatment-related change is less common; the "
                     "estimate still uses clinical, timing and treatment inputs only, not the images",
}
INPUTS_USED = ("age, sex, IDH and MGMT status, days from diagnosis, radiotherapy and chemotherapy dates and dose, "
               "surgery day and scan number")
NOT_USED = ("the MRI images or tumour volumes, steroid dose, symptoms, performance status, extent of resection, or "
            "perfusion and diffusion imaging")
CLOSE_POINTS, SIMILAR_POINTS = 5, 2


def facts_v2(rec: dict) -> dict:
    F = facts(rec)
    ctx = rec.get("context_v2", {})
    p = rec["prediction"]["risk_progression_within_120d"]
    lo, hi = rec["prediction"]["interval_95"]
    cuts = rec["risk_tier"]["cuts"]
    F["risk.statement"] = (f"{r0(100 * p)}% (95% interval {r0(100 * lo)}-{r0(100 * hi)}%) risk of documented "
                           f"progression within 120 days")
    F["risk.tier_cut_lower_percent"], F["risk.tier_cut_upper_percent"] = r0(100 * cuts[0]), r0(100 * cuts[1])
    near = [c for c in cuts if abs(p - c) < 0.005]
    F["risk.tier_position"] = (f"{F['risk.tier']} (just {'below' if p < near[0] else 'above'} a tier boundary)"
                               if near else F["risk.tier"])
    if ctx.get("reference_mean") is not None:
        ref = ctx["reference_mean"]
        F["risk.reference_percent"] = r0(100 * ref)
        F["risk.reference_meaning"] = "average model-estimated risk across the scans the model was trained on"
        d = 100 * (p - ref)
        F["risk.relative_to_reference"] = "close to" if abs(d) < CLOSE_POINTS else "above" if d > 0 else "below"
    pos = (f"{F['risk.tier_position']} of the model's estimates on its training scans (cut points "
           f"{F['risk.tier_cut_lower_percent']}% and {F['risk.tier_cut_upper_percent']}%)")
    if "risk.reference_percent" in F:
        pos += f", {F['risk.relative_to_reference']} the training-scan average of {F['risk.reference_percent']}%"
    F["risk.position_statement"] = pos
    pr = ctx.get("prior")
    F["risk.prior_available"] = pr is not None
    if pr is not None:
        F["risk.prior_percent"] = r0(100 * pr["risk"])
        F["risk.prior_days_before"] = r0(pr["days_before"])
        ch = r0(100 * p) - r0(100 * pr["risk"])
        F["risk.change_since_prior_points"] = ch
        F["risk.change_since_prior_direction"] = ("similar (within 2 percentage points)" if abs(ch) <= SIMILAR_POINTS
                                                  else "higher" if ch > 0 else "lower")
        F["risk.prior_statement"] = (f"{F['risk.prior_percent']}% on the prior scan {F['risk.prior_days_before']} days "
                                     "earlier, so the current estimate is " +
                                     ("similar" if abs(ch) <= SIMILAR_POINTS else
                                      f"{abs(ch)} percentage points {'higher' if ch > 0 else 'lower'}"))
    F["phase.why_it_matters"] = PHASE_WHY[rec["phase_of_care"]]
    F["model.inputs_used"] = INPUTS_USED
    F["model.not_used"] = NOT_USED
    if F["inputs.all_known_by_scan_day"] == "no":
        F["inputs.lookahead_note"] = ("at least one input (e.g. a molecular result) was recorded after the scan day, so "
                                      "this estimate uses information that was not available on the scan day")
    return F
