"""Grounded prompt v2 (report_usefulness.py). v1 (prompts.GROUNDED_SYSTEM) is unchanged and stays reproducible.

What changed from v1, and why:
  - Structure from the public reference reports (RadGenome-Brain MRI: FINDINGS then a 1-2 sentence IMPRESSION; the
    impression restates the key finding with its hedge). Each sentence carries a section tag.
  - Content a reader needs next to the probability (pre-specified usefulness items U1-U8, REPORT_USEFULNESS.md):
    risk with interval and horizon, what it is relative to (tier and the training-scan average), phase of care and why
    it matters, main drivers, what the model did not see, flags with reasons, change since the prior scan, look-ahead.
  - Horizon-citation failure of v1 (13/249): the risk is written from one field, risk.statement, which contains the
    percent, the interval and "120 days", so citing that one key supports every number in the sentence.
  - No verbal probability words (likely, unlikely, low, high): position is given by the tier and the reference
    comparison only (avoids wording that disagrees with the number, and false reassurance).
  - Hedging restricted to wording about the estimate ("estimated", "about", "may"); the reference corpora's diagnostic
    hedges ("suggestive of", "consistent with", "considered") are diagnosis wording and stay forbidden.
The output shape adds "section"; prism.report.checker.parse_structured ignores it, so the v1 checker runs unchanged.
"""

from __future__ import annotations

import json

VERSION = "v2.3"

GROUNDED_SYSTEM_V2 = """You write the narrative part of a PRISM surveillance report for a neuro-oncology clinician who already sees the risk number. Your job is to make that number usable: what it is relative to, why it is what it is, what it cannot know, and what needs a closer look.
You receive FACTS: a JSON object whose keys are field names and whose values come from one MRI scan's audit record.

Content rules:
1. Use only information in FACTS. Add no medical knowledge, image interpretation, or anything not in FACTS.
2. Every number you write must be copied exactly from a FACTS value (same digits; a field ending in "percent" may be followed by %). Never compute new numbers.
3. For each sentence, list in "fields" the keys of ALL FACTS fields whose information or numbers the sentence uses. Only list keys that exist in FACTS.
4. Do not diagnose. Never say the findings are, represent, suggest, favour or are consistent with progression, pseudoprogression, recurrence, radiation necrosis or treatment effect. Do not use RANO response categories.
5. Do not recommend or suggest any management: no imaging intervals, follow-up, biopsy, surgery, drugs, steroids or multidisciplinary review.
6. Do not describe the risk with probability words such as likely, unlikely, low, high, reassuring or worrying. Place it only with the tier words of risk.tier_position and with risk.relative_to_reference.
7. Hedge only the estimate itself ("the model estimates", "about", "may"). Avoid certainty words (definitely, clearly, confirms, rules out, will).
8. Call imaging volumes indicative and not a RANO assessment.
9. Name model inputs and contributions exactly as written in FACTS (for example contrib.top1_name).

Style: write as a radiologist writes a report: complete sentences with a subject and a verb, 12 to 25 words each, no fragments, lists or parentheses other than those copied from FACTS. Write flag names in plain words (early post-RT window, out of distribution, uncertain), never with underscores. Keep the whole summary under 180 words: do not repeat a fact within FINDINGS.

Write these sentences, in this order:
FINDINGS (section "findings")
 a. Context: the scan day from diagnosis, the phase of care and, when applicable, the days since the end of RT; then, in the same or the next sentence, phase.why_it_matters.
 b. Risk: "The model estimates a " + risk.statement + "." Cite "risk.statement".
 c. Position: "This is in the " + risk.position_statement + "." Cite "risk.position_statement".
 d. Only if risk.prior_available is true: the risk was risk.prior_statement (cite "risk.prior_statement"). Only if volume.prior_available is true: the indicative enhancing and FLAIR volume changes since the prior scan (and the enhancing change since the nadir), called indicative.
 e. Drivers: the one or two largest contributions (contrib.top1_name, contrib.top2_name) and their directions.
 f. Limits: the model did not use model.not_used.
 g. Flags: if flags.any_active is true, one sentence per active flag giving its name and its reason from flags.<name>.reason (cite that reason key), then that the scan is flagged for clinician review; otherwise one sentence that no referral flag is raised. Never describe an inactive flag as raised.
 h. Only if inputs.lookahead_note exists: state it.
IMPRESSION (section "impression"), one or two sentences:
 i. At most two sentences and 45 words: "The model estimates a " + risk.statement + ", in the " + the tier and the comparison with the average; then the single most important caveat in a few words (the active flags by name and that the scan is flagged for clinician review, or else the phase of care). Add nothing new.

Output only JSON of the form {"sentences": [{"section": "findings" | "impression", "text": "...", "fields": ["key", ...]}, ...]}."""

SCHEMA_V2 = {"type": "object", "additionalProperties": False, "required": ["sentences"],
             "properties": {"sentences": {"type": "array", "minItems": 1, "maxItems": 14, "items": {
                 "type": "object", "additionalProperties": False, "required": ["section", "text", "fields"],
                 "properties": {"section": {"type": "string", "enum": ["findings", "impression"]},
                                "text": {"type": "string"},
                                "fields": {"type": "array", "items": {"type": "string"}}}}}}}


def grounded_v2(F: dict) -> list[dict]:
    return [{"role": "system", "content": GROUNDED_SYSTEM_V2},
            {"role": "user", "content": "FACTS:\n" + json.dumps(F, indent=1, ensure_ascii=False)}]


def sectioned(raw: str) -> dict | None:
    """v2 output -> {"findings": [...], "impression": [...]} (None if not parseable)."""
    try:
        s = raw.strip()
        obj = json.loads(s[s.find("{"): s.rfind("}") + 1])
        out = {"findings": [], "impression": []}
        for c in obj["sentences"]:
            out[c.get("section", "findings")].append(c["text"].strip())
        return out
    except Exception:
        return None


def render_text(raw: str, arm: str) -> str:
    """Plain text a reader (or the judge) sees: v2 with FINDINGS / IMPRESSION headings, v1 as one paragraph."""
    from prism.report.checker import parse_structured
    if arm == "v2":
        s = sectioned(raw)
        if s is not None:
            return f"FINDINGS: {' '.join(s['findings'])}\nIMPRESSION: {' '.join(s['impression'])}"
    cl = parse_structured(raw)
    return " ".join(c["text"] for c in cl) if cl else raw
