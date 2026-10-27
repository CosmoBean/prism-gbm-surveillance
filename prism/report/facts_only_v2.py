"""Facts-only v2 (docs/results/REPORT_FIELD_ABLATION_V2_PLAN.md section 1): one specification renders the prompt
and the checker.

Each facts-only key has a finite list of accepted sentence forms rendered from its value; the first is canonical and
is the one the prompt shows. A sentence passes only if, case-folded and whitespace-normalised, it equals a form of
the keys it cites. Defence-in-depth checks (frozen checker numbers and citations, forbidden wording, clinical
inference, banned model-derived terms) run as well; the last three skip verbatim copies of supplied statements.
Development may change only the forms, the prompt wording and the banned list (bump SPEC_VERSION).
"""

from __future__ import annotations

import json
import re

from prism.report import checker
from prism.report.field_ablation import (  # noqa: F401  (some names re-exported for the v2 runner)
    FACTS_ONLY, FACTS_SCHEMA, FACTS_SECTIONS, FULL_ONLY_PREFIXES, _BANNED, _CHANGE_KEYS, _CLINICAL_INFERENCE,
    _MEASURED_KEYS, _VOLUME_DISPLAY, _required_keys, facts_for_arm, parse_facts_only,
)

SPEC_VERSION = "v2-iter0"
CRITERIA = ("fail_unparsed", "fail_section_order", "fail_multi_sentence", "fail_form", "fail_required_missing",
            "fail_unsupported_number", "fail_invalid_citation", "fail_forbidden", "fail_banned_term",
            "fail_clinical_inference")
# v1 list minus above / below / higher / lower, which occur inside supplied statements.
_REMOVED = "above|below|higher|lower|"
assert _REMOVED in _BANNED.pattern
BANNED_V2 = re.compile(_BANNED.pattern.replace(_REMOVED, ""), _BANNED.flags)
SECTION_OF = {"scan.phase": "scan", "scan.previous_available": "scan", "scan.rater_statement": "scan",
              "meas.available": "measurements", "meas.label": "measurements",
              **{k: "measurements" for k in _MEASURED_KEYS}, **{k: "longitudinal" for k in _CHANGE_KEYS},
              "system.cohort": "provenance"}
_COHORT = re.compile(r"MU-Glioma-Post|LUMIERE|UCSF-ALPTDG", re.I)
_COHORT_NAME = {"mu-glioma-post": "MU-Glioma-Post", "lumiere": "LUMIERE", "ucsf-alptdg": "UCSF-ALPTDG"}
_MULTI = re.compile(r"(?<!\d)[.!?](?!\d)\s+\S")
_WORD = re.compile(r"[a-z]+")


def _stop(s: str) -> str:
    s = s.strip()
    return s if s.endswith(".") else s + "."


def sentence_forms(key: str, facts: dict) -> list[str]:
    """Accepted sentence forms for one key; the first is canonical. [] for a key without forms."""
    if key not in facts:
        return []
    v = facts[key]
    if key == "scan.phase":
        return [f"Scan timing: {v}."]
    if key == "scan.previous_available":
        return ["A previous scan is available." if v == "yes" else "No previous scan is available."]
    if key == "scan.rater_statement":
        return [_stop(v)]
    if key == "system.cohort":
        m = _COHORT.search(str(v))
        return [f"Source cohort: {_COHORT_NAME[m.group(0).lower()]}."] if m else []
    if key == "meas.available":
        return ["Segmentation volumes are available." if v == "yes" else
                "No usable segmentation volumes are available."]
    if key == "meas.label":
        return ["Volumes are from the automatic segmentation and are indicative."]
    if key in _MEASURED_KEYS:
        name = _VOLUME_DISPLAY[key]
        lead = name if name.startswith("FLAIR") else name[0].lower() + name[1:]
        return [f"{name} volume is {v:.1f} cc.", f"The {lead} volume is {v:.1f} cc."]
    if key in _CHANGE_KEYS:
        s = str(v).strip()
        return [_stop(s[:1].upper() + s[1:])]
    return []


def required_keys(facts: dict) -> list[str]:
    return _required_keys(facts)


def _report_keys(facts: dict) -> list[str]:
    """Required keys plus the optional cohort, in section order."""
    keys = required_keys(facts) + (["system.cohort"] if "system.cohort" in facts else [])
    return [k for s in FACTS_SECTIONS for k in keys if SECTION_OF.get(k) == s]


def reference_report(facts: dict) -> list[dict]:
    """Deterministic report: the canonical form of every required key (plus the cohort), in section order."""
    return [{"section": SECTION_OF[k], "text": forms[0], "fields": [k]}
            for k in _report_keys(facts) if (forms := sentence_forms(k, facts))]


def messages(facts: dict) -> list[dict]:
    """Prompt rendered from the specification: every present key's canonical form, verbatim."""
    if any(key.startswith(FULL_ONLY_PREFIXES) for key in facts):
        raise ValueError("facts-only prompt received excluded fields")
    lines = []
    for k in _report_keys(facts):
        forms = sentence_forms(k, facts)
        if forms:
            lines.append(f'- section "{SECTION_OF[k]}", fields ["{k}"]: {forms[0]}')
    supplied = {key: value for key, value in facts.items() if key.startswith(("scan.", "meas."))}
    if (m := _COHORT.search(str(facts.get("system.cohort", "")))):
        supplied["system.cohort"] = _COHORT_NAME[m.group(0).lower()]
    system = (
        "Write a factual scan summary from FACTS only. Output exactly these sentences, one per item, in this order. "
        "Copy each sentence text exactly as written, give its section, and cite exactly the key shown in fields. "
        "Do not add, change, merge, split or reword any sentence, and add no other sentence.\n"
        "Sentences:\n" + "\n".join(lines) + "\n"
        'Output only JSON of the form {"sentences":[{"section":"scan","text":"...","fields":["scan.phase"]}]}.'
    )
    return [{"role": "system", "content": system},
            {"role": "user", "content": "FACTS:\n" + json.dumps(supplied, indent=1, ensure_ascii=False)}]


def _norm(text: str) -> str:
    return " ".join(text.split()).casefold()


def _without_statements(text: str, facts: dict) -> str:
    """Remove verbatim copies of supplied statements (case-insensitive, trailing full stop ignored)."""
    stmts = sorted({str(v).strip().rstrip(".") for k, v in facts.items() if k.endswith("_statement")}, key=len,
                   reverse=True)
    for s in stmts:
        if s:
            text = re.sub(re.escape(s) + r"\.?", " ", text, flags=re.I)
    return text


def _shape_ok(claims) -> bool:
    return isinstance(claims, list) and bool(claims) and all(
        isinstance(c, dict) and isinstance(c.get("text"), str) and isinstance(c.get("fields"), list) and
        all(isinstance(k, str) for k in c["fields"]) and c.get("section") in FACTS_SECTIONS for c in claims)


def check(claims: list[dict] | None, facts: dict) -> dict:
    """Check a parsed facts-only v2 response: one boolean per criterion, the missing keys and the non-form words."""
    out = {c: False for c in CRITERIA}
    out.update(parsed=False, n_claims=len(claims) if isinstance(claims, list) else 0, missing=[], non_form_words=[])
    if not _shape_ok(claims):
        out.update({"fail_unparsed": True, "pass": False})
        return out
    forms = [{_norm(f) for k in c["fields"] for f in sentence_forms(k, facts)} for c in claims]
    order = [FACTS_SECTIONS.index(c["section"]) for c in claims]
    checked = [checker.check_claim(c, facts) for c in claims]
    text = " ".join(_without_statements(c["text"], facts) for c in claims)
    out["missing"] = [k for k in required_keys(facts)
                      if not any(k in c["fields"] and _norm(c["text"]) in {_norm(f) for f in sentence_forms(k, facts)}
                                 for c in claims)]
    words = set()
    for c in claims:
        vocab = {w for k in c["fields"] for f in sentence_forms(k, facts) for w in _WORD.findall(f.casefold())}
        words |= {w for w in _WORD.findall(c["text"].casefold()) if w not in vocab}
    out.update(
        parsed=True, non_form_words=sorted(words),
        fail_section_order=order != sorted(order),
        fail_multi_sentence=any(_MULTI.search(c["text"]) or not c["text"].strip() for c in claims),
        fail_form=any(not c["fields"] or _norm(c["text"]) not in f for c, f in zip(claims, forms)),
        fail_required_missing=bool(out["missing"]),
        fail_unsupported_number=any(r["unsupported_numbers"] or (not r["supported"] and not r["invalid_fields"])
                                    for r in checked),
        fail_invalid_citation=any(r["invalid_fields"] for r in checked),
        fail_forbidden=any(checker.forbidden_v3(text).values()),
        fail_banned_term=bool(BANNED_V2.search(text)),
        fail_clinical_inference=bool(_CLINICAL_INFERENCE.search(text)))
    out["pass"] = not any(out[c] for c in CRITERIA)
    return out


def consistency_errors(facts: dict) -> list[str]:
    """[] when every form the prompt shows passes the checker and the reference report passes; else short errors
    naming the key and criterion (no fact values)."""
    errors = []
    prompt = messages(facts)[0]["content"]
    for k in facts:
        forms = sentence_forms(k, facts)
        if forms and k not in SECTION_OF:
            errors.append(f"{k}: no section")
            continue
        if forms and forms[0] not in prompt:
            errors.append(f"{k}: canonical form not in prompt")
        for i, form in enumerate(forms):
            r = check([{"section": SECTION_OF[k], "text": form, "fields": [k]}], facts)
            errors += [f"{k} form {i}: {c}" for c in CRITERIA if r[c] and c != "fail_required_missing"]
    errors += [f"{k}: required key has no form" for k in required_keys(facts) if not sentence_forms(k, facts)]
    r = check(reference_report(facts), facts)
    errors += [f"reference: {c}" for c in CRITERIA if r[c]]
    errors += [f"reference: missing {k}" for k in r["missing"]]
    return errors
