"""Report facts v3.2 (docs/results/REVISION_DATA_PLAN.md, R4): facts_v3_1 with the model names of the paper.

The only change from v3.1 is vocabulary. "Timeline pathway" becomes "clinical-history model", "image pathway"
becomes "imaging model" and "pathway" becomes "model", in the facts values and in the keys
(`pathway.timeline.*` -> `model.clinical_history.*`, `pathways.*` -> `models.*`, and so on).

The frozen checker (checker.py, blob 26d6637a...) is not edited. `check_v3_2` maps a v3.2 report back to the v3.1
vocabulary (cited keys by the exact inverse of the key map; the two model names in the text) and calls the frozen
checker with the v3.1 facts of the same record, so every v3.1 rule runs unchanged.
"""

from __future__ import annotations

import re

from prism.report.facts_v3_1 import facts_v3_1

FACTS_VERSION = "v3.2"
KEY_TOKENS = {"pathway": "model", "pathways": "models", "timeline": "clinical_history", "images": "imaging",
              "pathways_disagree": "models_disagree"}
# ordered: longer phrases first
VALUE_SUBS = [(r"\btimeline pathway\b", "clinical-history model"), (r"\bimage pathway\b", "imaging model"),
              (r"\btimeline and image scores\b", "clinical-history and imaging scores"),
              (r"\bboth pathways together\b", "the clinical-history and imaging models together"),
              (r"\btimeline score\b", "clinical-history score"), (r"\bimage score\b", "imaging score"),
              (r"\bimage (?=\d)", "imaging "), (r"\bpathways\b", "models"), (r"\bpathway\b", "model"),
              (r"\btimeline\b", "clinical-history")]
# report text back to the v3.1 names, so the checker's side rule (SIDE_PAT: timeline | image | combined) applies
TEXT_BACK = [(r"\bclinical[- ]history\b", "timeline"), (r"\bimaging (model|score|scores|pathway)\b", r"image \1"),
             (r"\bimaging (?=\d)", "image ")]


def new_key(k: str) -> str:
    return ".".join(KEY_TOKENS.get(t, t) for t in k.split("."))


def rename_value(v):
    if not isinstance(v, str):
        return v
    for a, b in VALUE_SUBS:
        v = re.sub(a, b, v)
    return v


def facts_v3_2(rec: dict) -> dict:
    F1 = facts_v3_1(rec)
    F = {new_key(k): rename_value(v) for k, v in F1.items()}
    assert len(F) == len(F1), "key map is not one to one"
    F["system.facts_version"] = FACTS_VERSION
    bad = [k for k, v in F.items() if re.search(r"timeline|pathway", k + " " + str(v), re.I)]
    assert not bad, f"old model names left in facts: {bad}"
    return F


def back_claims(claims: list[dict] | None, F1: dict) -> list[dict] | None:
    """v3.2 claims -> v3.1 vocabulary: cited keys by the inverse key map, model names in the text."""
    if claims is None:
        return None
    inv = {new_key(k): k for k in F1}
    out = []
    for c in claims:
        t = c["text"]
        for a, b in TEXT_BACK:
            t = re.sub(a, b, t, flags=re.I)
        out.append({**c, "text": t, "fields": [inv.get(k, k) for k in c.get("fields", [])]})
    return out


def check_v3_2(claims: list[dict] | None, rec: dict) -> dict:
    """The frozen v3.1 check (check(..., card=True)) of a v3.2 report of `rec`."""
    from prism.report import checker
    F1 = facts_v3_1(rec)
    return checker.check(back_claims(claims, F1), F1, card=True)
