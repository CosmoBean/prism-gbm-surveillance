"""Prompts for the narrative summary (frozen before evaluation; see docs/results/REPORT_AGENT.md).

grounded (arm A, PRISM v2): the model sees only the facts JSON of one record and must return claims with field keys.
original (arm B): the original PRISM agent prompt (legacy/glioma_agent/src/agent_pipeline.py, generate_llm_summary)
    with its context blocks filled from the same record: the 0.48 / 0.75 confidence tiers and concordance switch, the
    "RANO 2.0" block fed by the indicative volumetric rule, the original confounder score, and the top contributions in
    place of SHAP drivers. The referral flags are added as a context block (the original had none), so both arms see
    the same facts. No citation constraint; its instruction 7 asks for a clinical recommendation, as in the original.
"""

from __future__ import annotations

import json

GROUNDED_SYSTEM = """You write the narrative summary of a PRISM surveillance report for a neuro-oncology clinician.
You receive FACTS: a JSON object whose keys are field names and whose values come from one MRI scan's audit record.

Rules:
1. Use only information in FACTS. Add no medical knowledge, image interpretation, or anything not in FACTS.
2. Every number you write must be copied exactly from a FACTS value (same digits; a field ending in "percent" may be followed by %). Never compute new numbers: no differences, sums, conversions or re-rounding.
3. For each sentence, list in "fields" the keys of all FACTS fields the sentence uses. Only list keys that exist in FACTS.
4. State the risk of documented progression within 120 days (risk.value or risk.percent), its 95% interval, and its tier (risk.tier, e.g. "upper third").
5. If any flags.<name>.active is true: state every active flag with its reason and say that the scan is flagged for clinician review. Do not describe a flag that is not active as raised.
6. Do not diagnose. Never say the findings are, represent, suggest or are consistent with progression, pseudoprogression, recurrence, radiation necrosis or treatment effect. Do not use RANO response categories (progressive disease, stable disease, partial response, complete response).
7. Do not recommend or suggest any management: no imaging intervals, follow-up, biopsy, surgery, drugs, steroids or multidisciplinary review.
8. Use hedged, probabilistic language. Avoid certainty words (definitely, clearly, confirms, rules out, will progress).
9. If you mention imaging volumes, call them indicative and not a RANO assessment.
10. Write 4 to 7 short sentences in plain clinical English.

Output only JSON of the form {"sentences": [{"text": "...", "fields": ["key", ...]}, ...]}."""

SCHEMA = {"type": "object", "additionalProperties": False, "required": ["sentences"],
          "properties": {"sentences": {"type": "array", "minItems": 1, "maxItems": 10, "items": {
              "type": "object", "additionalProperties": False, "required": ["text", "fields"],
              "properties": {"text": {"type": "string"}, "fields": {"type": "array", "items": {"type": "string"}}}}}}}


def grounded(F: dict) -> list[dict]:
    return [{"role": "system", "content": GROUNDED_SYSTEM},
            {"role": "user", "content": "FACTS:\n" + json.dumps(F, indent=1, ensure_ascii=False)}]


# ---------------------------------------------------------------- arm B: original PRISM prompt, same record
FUSION_THRESHOLD = 0.48


def confounder(F: dict) -> dict:
    """Original weighted pseudoprogression score (agent_pipeline.compute_confounder_score) on the record's inputs;
    steroid change and RC-adjacent enhancement are not in the record (original defaults 0 / False)."""
    d = F["scan.days_since_rt_end"]
    score, br = 0.0, {}
    if isinstance(d, int):
        add, txt = ((2.0, "< 3 months post-RT — highest pseudoprogression window") if d < 90 else
                    (1.0, "3–6 months post-RT — elevated pseudoprogression risk") if d < 180 else
                    (0.5, "6–12 months post-RT — moderate risk, late pseudoprogression possible") if d < 365 else
                    (0.0, "> 12 months post-RT — pseudoprogression less likely but not excluded"))
        score += add
        br["time_post_rt"] = f"+{add:.1f} ({txt})"
    else:
        br["time_post_rt"] = "N/A (days post-RT unavailable)"
    m = F["inputs.mgmt"]
    add = {"methylated": 1.5, "unknown": 0.5}.get(m, 0.0)
    score += add
    br["mgmt"] = {"methylated": "+1.5 (MGMT methylated — pseudoprogression rate ~30-40%)",
                  "unknown": "+0.5 (MGMT indeterminate — risk uncertain)"}.get(m, "+0.0 (MGMT unmethylated — pseudoprogression rate ~15%)")
    br["steroid"] = "+0.0 (Steroid dose change +0% — within normal range)"
    br["rc_adjacent"] = "+0.0 (No RC-adjacent enhancement)"
    level = "HIGH Pseudoprogression Risk" if score >= 3 else "MODERATE Pseudoprogression Risk" if score >= 1.5 \
        else "LOW Pseudoprogression Risk"
    return {"total_score": round(score, 1), "risk_level": level, "breakdown": br}


def original(F: dict, scan_id: str) -> tuple[list[dict], dict]:
    """Messages and the numeric context the prompt contains (for the 'own input' support check)."""
    p = F["risk.value"]
    alert = p >= FUSION_THRESHOLD
    vol = F.get("volume.indicative_flag")
    rano_pd = vol == "met"
    concordant = rano_pd == alert
    if p >= 0.75:
        phrase, note = "strongly suggests", "The model output is in the high-confidence range (>0.75)."
    elif alert:
        phrase = "is consistent with progression but warrants close follow-up"
        note = (f"The model output ({p:.3f}) is above threshold but in the moderate range (0.48–0.75). "
                "Clinical correlation and short-interval imaging are recommended.")
    else:
        phrase = "does not support progression at this timepoint"
        note = f"The model output ({p:.3f}) is below the alert threshold (0.48). Continued surveillance is advised."
    conc = ("RANO 2.0 criteria and the AI model are in AGREEMENT. Write a confident, definitive summary that clearly "
            "states the conclusion.") if concordant else (
        "RANO 2.0 criteria and the AI model are in DISAGREEMENT. Write a cautious, nuanced summary that explicitly "
        "flags this discordance, emphasizes clinical uncertainty, and strongly recommends multidisciplinary review and "
        "short-interval follow-up imaging (4-6 weeks).")
    cf = confounder(F)
    drivers = "; ".join(f"{F[f'contrib.top{j}_name']} (contribution={F[f'contrib.top{j}_logodds']:+.2f} log-odds, "
                        f"{F[f'contrib.top{j}_direction']})" for j in (1, 2, 3) if f"contrib.top{j}_name" in F)
    dp = F.get("volume.enhancing_change_since_prior_cc", "N/A (first timepoint)")
    dn = F.get("volume.enhancing_change_since_nadir_cc", "N/A")
    pct = F.get("volume.enhancing_change_since_nadir_percent", "N/A")
    flags = [f"- {k.split('.')[1]}: {F[k.replace('.active', '.reason')]}" for k in F
             if k.startswith("flags.") and k.endswith(".active") and F[k] is True] or ["- none"]
    pid, _, tp = scan_id.partition("_Timepoint_")
    days = F["scan.day_from_diagnosis"]
    prompt = f"""You are a neuro-oncology AI assistant generating a structured clinical report summary.
Write in formal medical English. Be precise and evidence-based.

PATIENT: {pid}, Timepoint_{tp}
Days from diagnosis to MRI: {days:.0f}
Phase of care: {F['scan.phase_of_care']}; days since end of RT: {F['scan.days_since_rt_end']}

LONGITUDINAL CHANGE (enhancing tumour volume):
- Current enhancing volume: {F.get('volume.enhancing_cc', 'N/A')} cc
- Δ from prior timepoint: {dp} cc
- Δ from nadir: {dn} cc ({pct}%)

AI MODEL:
- Progression probability within 120 days: {p:.4f} (threshold: {FUSION_THRESHOLD}); 95% interval {F['risk.interval_low']}–{F['risk.interval_high']}
- AI Verdict: {"PROGRESSION ALERT" if alert else "No Alert"}
- {note}

RANO 2.0 RULE ENGINE:
- BD Change: {pct}% ({'+' if rano_pd else 'below threshold'})
- New Lesion: Not assessed
- RANO Verdict: {"Progressive Disease (PD)" if rano_pd else "No Progression Detected"}

CONFOUNDER ASSESSMENT:
- Pseudoprogression Risk Score: {cf['total_score']}/5.5 → {cf['risk_level']}
- Breakdown: {'; '.join(f'{k}: {v}' for k, v in cf['breakdown'].items())}

SHAP TOP DRIVERS:
{drivers}

REFERRAL FLAGS:
{chr(10).join(flags)}

CONCORDANCE STATUS: {conc}

INSTRUCTIONS:
1. Write exactly ONE paragraph (5-8 sentences).
2. Open with patient context and key longitudinal change (delta, not just absolute value).
3. State RANO verdict and AI verdict clearly.
4. Integrate the confounder risk assessment naturally.
5. Reference the top SHAP driver(s) to explain WHY the AI reached its conclusion.
6. Use the phrase "{phrase}" when describing the AI's assessment.
7. Close with a concrete clinical recommendation (e.g., continue surveillance, MDT review, short-interval MRI).
8. DO NOT use bullet points. Write in flowing prose.
"""
    return [{"role": "user", "content": prompt}], {"_prompt_text": prompt}
