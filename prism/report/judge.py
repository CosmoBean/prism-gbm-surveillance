"""EXPLORATORY LLM-as-judge rubric (not a substitute for clinicians).

A model from a different family than the report writer (writer: Qwen; judge: Google Gemma 4 31B-it) rates each
summary against the record's facts, blinded to prompt version: the judge sees the facts and the summary text only
(v2 shows FINDINGS / IMPRESSION headings, so form is not hidden; the version label, citations and section keys are).
Two tasks, greedy decoding, JSON output:
  absolute   six 1-5 ratings with a one-sentence reason each (RUBRIC), one line per criterion, constrained by
             ABS_REGEX (nested-JSON output looped on whitespace in the development run)
  pairwise   two summaries of the same scan, presented in both orders; "first" / "second" / "tie" on overall
             usefulness next to the probability; a preference counts only if it is the same in both orders
"""

from __future__ import annotations

import json

RUBRIC = {
    "accuracy": "Every statement agrees with FACTS; no number, flag, tier or input is misstated or invented.",
    "completeness": "The reader learns what is needed to use the risk number: risk with interval and horizon, what it is "
                    "relative to, phase of care and why it matters, main drivers, what the model could not see, review "
                    "flags with reasons, and change since the prior scan when there is one.",
    "clarity": "Clear, concise clinical English that a busy neuro-oncology clinician can read in under a minute.",
    "calibrated_language": "Words match the number and its uncertainty: no false reassurance, no alarm beyond the "
                           "estimate, uncertainty stated where FACTS show it.",
    "scope": "Stays within decision support: no diagnosis, no RANO category, no management advice.",
    "overall_usefulness": "How useful the summary is to a clinician alongside the bare probability.",
}
JUDGE_SYSTEM = (
    "You are an experienced neuro-oncology clinician and radiologist reviewing short machine-written summaries that "
    "accompany a risk estimate from a prediction model. FACTS is the complete record the summary was written from. "
    "Rate the SUMMARY on each criterion from 1 (very poor) to 5 (excellent):\n" +
    "\n".join(f"- {k}: {v}" for k, v in RUBRIC.items()) +
    "\nJudge only what is written. Be strict and consistent. Answer in exactly this format, one line per "
    "criterion:\n" + "\n".join(f"{k}: <score 1-5> | <one-sentence reason>" for k in RUBRIC))
PAIR_SYSTEM = (
    "You are an experienced neuro-oncology clinician comparing two machine-written summaries of the same scan record. "
    "FACTS is the complete record both were written from. Decide which summary would be more useful to a clinician "
    "alongside the bare probability, considering accuracy, completeness, clarity, calibrated language and staying "
    "within decision support (no diagnosis, no RANO category, no management advice). Output JSON only.")

ABS_REGEX = "".join(f"{k}: [1-5] \\| [^\\n|]{{5,200}}\\n" for k in RUBRIC)  # one line per criterion
PAIR_SCHEMA = {"type": "object", "additionalProperties": False, "required": ["reason", "preferred"],
               "properties": {"reason": {"type": "string"},
                              "preferred": {"type": "string", "enum": ["first", "second", "tie"]}}}


def absolute(F: dict, summary: str) -> list[dict]:
    return [{"role": "system", "content": JUDGE_SYSTEM},
            {"role": "user", "content": f"FACTS:\n{json.dumps(F, indent=1, ensure_ascii=False)}\n\nSUMMARY:\n{summary}"}]


def pairwise(F: dict, first: str, second: str) -> list[dict]:
    return [{"role": "system", "content": PAIR_SYSTEM},
            {"role": "user", "content": f"FACTS:\n{json.dumps(F, indent=1, ensure_ascii=False)}\n\nFIRST SUMMARY:\n"
                                        f"{first}\n\nSECOND SUMMARY:\n{second}"}]


def parse_absolute(raw: str) -> dict | None:
    """'criterion: 4 | reason' lines -> {criterion: {"score", "reason"}}; None unless every criterion is present."""
    import re
    out = {m.group(1): {"score": int(m.group(2)), "reason": m.group(3).strip()}
           for m in re.finditer(r"^(\w+): ([1-5]) \| (.*)$", raw, re.M) if m.group(1) in RUBRIC}
    return out if set(out) == set(RUBRIC) else None


def parse(raw: str) -> dict | None:
    try:
        s = raw.strip()
        return json.loads(s[s.find("{"): s.rfind("}") + 1])
    except Exception:
        return None
