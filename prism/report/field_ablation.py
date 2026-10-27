"""Field partition for the paired v3.1 report ablation."""

from __future__ import annotations

from collections import Counter
import hashlib
import json
import re

from prism.config import REPO
from prism.report import checker
from prism.report.facts_v3_1 import facts_v3_1

FACTS_ONLY = "facts_only"
FULL_EVIDENCE = "full_evidence"
FULL_ONLY_PREFIXES = ("pathway.", "pathways.", "conformal.", "card.", "flags.")
EVAL_RELATIVE = "outputs/results/analyses/report_v3_1/records/eval.jsonl"
FROZEN_RELATIVE = "outputs/results/analyses/report_v3_1/FROZEN_hashes.txt"
FACTS_SECTIONS = ("scan", "measurements", "longitudinal", "provenance")
FACTS_SCHEMA = {"type": "object", "additionalProperties": False, "required": ["sentences"],
                "properties": {"sentences": {"type": "array", "minItems": 1, "maxItems": 24, "items": {
                    "type": "object", "additionalProperties": False, "required": ["section", "text", "fields"],
                    "properties": {"section": {"type": "string", "enum": list(FACTS_SECTIONS)},
                                   "text": {"type": "string"},
                                   "fields": {"type": "array", "items": {"type": "string"}}}}}}}
_MEASURED_KEYS = ("meas.enhancing_cc", "meas.flair_hyperintensity_cc", "meas.necrosis_cc",
                  "meas.cavity_cc", "meas.necrosis_and_cavity_cc")
_VOLUME_LABEL = re.compile(
    r"\b(necrosis (?:and|with) (?:resection )?cavity|resection cavity|FLAIR hyperintensity|"
    r"enhancing tumour|necrosis|cavity|FLAIR|enhancing)\b", re.I)
_VOLUME_KIND = {"enhancing": "meas.enhancing_cc", "enhancing tumour": "meas.enhancing_cc",
                "flair": "meas.flair_hyperintensity_cc", "flair hyperintensity": "meas.flair_hyperintensity_cc",
                "necrosis": "meas.necrosis_cc", "cavity": "meas.cavity_cc",
                "resection cavity": "meas.cavity_cc", "necrosis and cavity": "meas.necrosis_and_cavity_cc",
                "necrosis with cavity": "meas.necrosis_and_cavity_cc"}
_VOLUME_DISPLAY = {"meas.enhancing_cc": "Enhancing tumour", "meas.flair_hyperintensity_cc": "FLAIR hyperintensity",
                   "meas.necrosis_cc": "Necrosis", "meas.cavity_cc": "Resection cavity",
                   "meas.necrosis_and_cavity_cc": "Necrosis and cavity"}
_CHANGE_KEYS = ("meas.enhancing_change_since_previous_statement",
                "meas.flair_hyperintensity_change_since_previous_statement",
                "meas.enhancing_change_since_earlier_minimum_statement")
_BANNED = re.compile(
    r"\b(?:scores?|models?|predict(?:ion|ions|ive|ed)?|pathways?|conformal|tiers?|flags?|"
    r"risks?|probabilit(?:y|ies)|likel(?:y|ihood)|uncertain(?:ty)?|confiden(?:ce|t)|"
    r"outcomes?|progress(?:ion|ive|ed)?|recurren(?:ce|t)|pseudo-?progression|"
    r"radiation necrosis|treatment effect|both outcomes|agree(?:ment)?|disagree(?:ment)?|"
    r"above|below|higher|lower|tested|performance|accuracy|reliab(?:le|ility))\b", re.I)
_CLINICAL_INFERENCE = re.compile(
    r"\b(?:tumou?r|lesion|disease)\b.{0,40}\b(?:grown?|growing|growth|increas\w*|"
    r"worsen\w*|spread|expand\w*|shrink\w*|improv\w*|respond\w*)\b|"
    r"\b(?:scan|imaging)\b.{0,30}\b(?:shows?|indicates?|suggests?)\b.{0,30}\b"
    r"(?:growth|worsening|response|change)\b", re.I)
_UNAVAILABLE_VOLUME = re.compile(
    r"\b(?:no|not|without|unavailable|absent|missing)\b.{0,35}\b(?:segmentation|volumes?)\b|"
    r"\b(?:segmentation|volumes?)\b.{0,35}\b(?:unavailable|absent|missing|not available)\b", re.I)
_NEUTRAL_WORDS = frozenset((
    "a an the this scan timing phase previous is are was were available unavailable no usable automatic "
    "segmentation indicative volume volumes cc from at measured measurement measures of and with by source "
    "cohort rater recorded within after before radiotherapy days earlier compared comparison to its end there it"
).split())
_LIMITATIONS = ("Measurements come from automatic segmentation and are indicative. "
                "Only the supplied scan facts are described; no diagnosis or management advice is given.")


def facts_for_arm(rec: dict, arm: str) -> dict:
    """Build the v3.1 facts once, then apply the strict arm field contract."""
    if arm not in (FACTS_ONLY, FULL_EVIDENCE):
        raise ValueError(f"unknown report field arm: {arm}")
    facts = facts_v3_1(rec)
    if arm == FULL_EVIDENCE:
        return facts
    return {key: value for key, value in facts.items() if not key.startswith(FULL_ONLY_PREFIXES)}


def _required_keys(facts: dict) -> list[str]:
    keys = ["scan.phase", "scan.previous_available", "meas.available"]
    if "scan.rater_statement" in facts:
        keys.append("scan.rater_statement")
    if facts.get("meas.available") == "yes":
        keys += ["meas.label"]
        keys += [key for key in _MEASURED_KEYS + _CHANGE_KEYS if key in facts]
    return [key for key in keys if key in facts]


def facts_only_messages(facts: dict) -> list[dict]:
    """Separate structured prompt with no dependency on model-derived fields."""
    if any(key.startswith(FULL_ONLY_PREFIXES) for key in facts):
        raise ValueError("facts-only prompt received excluded fields")
    required = ", ".join(_required_keys(facts))
    supplied = {key: value for key, value in facts.items() if key.startswith(("scan.", "meas."))}
    if "system.cohort" in facts:
        cohort = re.search(r"MU-Glioma-Post|LUMIERE|UCSF-ALPTDG", facts["system.cohort"], re.I)
        if cohort:
            supplied["system.cohort"] = cohort.group(0)
    system = (
        "Write a factual scan summary from FACTS only. Use four ordered sections: "
        "scan, measurements, longitudinal, provenance. Include the available content for these keys: "
        f"{required}. Describe the cohort in plain terms if useful. Copy numeric values exactly and cite "
        "every FACTS key used by each sentence. Do not infer a clinical finding, diagnose, interpret, "
        "recommend an action, or add unsupported information. State segmentation volumes as indicative. "
        "Use a separate sentence for each volume: '<name> volume is <value> cc.' The first volume sentence "
        "may add 'from automatic segmentation; indicative.' Copy fixed change statements as whole sentences. "
        "Use complete sentences and British spelling. Output only JSON of the form "
        '{"sentences":[{"section":"scan","text":"...","fields":["scan.phase"]}]}.'
    )
    return [{"role": "system", "content": system},
            {"role": "user", "content": "FACTS:\n" + json.dumps(supplied, indent=1, ensure_ascii=False)}]


def _contains_field_value(claim: dict, key: str, facts: dict) -> bool:
    text = claim["text"].lower()
    value = facts[key]
    if key in _MEASURED_KEYS:
        labels = list(_VOLUME_LABEL.finditer(text))
        for i, label in enumerate(labels):
            if _VOLUME_KIND[label.group(0).lower()] != key:
                continue
            end = labels[i + 1].start() if i + 1 < len(labels) else len(text)
            segment = text[label.end():end]
            written = checker.numbers(segment)
            if written and checker.matches(written[0], [float(value)], False):
                return True
        return False
    if isinstance(value, (int, float)):
        return any(checker.matches(n, [float(value)], pc) for n, pc in checker.numbers(text, with_percent=True))
    if key == "scan.previous_available":
        return "previous" in text and (("no " in text or "without" in text) if value == "no" else
                                        not ("no previous" in text or "without" in text))
    if key == "meas.available":
        mentions_volume = "segmentation" in text or "volume" in text
        unavailable = bool(_UNAVAILABLE_VOLUME.search(text))
        return mentions_volume and (unavailable if value == "no" else not unavailable)
    if key == "meas.label":
        return "segmentation" in text and "indicative" in text
    if key == "scan.phase":
        return value.lower() in text
    if key == "system.cohort":
        cohort = re.search(r"MU-Glioma-Post|LUMIERE|UCSF-ALPTDG", str(value), re.I)
        return bool(cohort and cohort.group(0).lower() in text)
    if key.endswith("statement"):
        return text.strip().rstrip(".") == str(value).lower().strip().rstrip(".")
    return str(value).lower() in text


def _unlicensed_words(claim: dict, facts: dict) -> list[str]:
    """Fail closed on narrative words not supplied by cited facts or neutral measurement grammar."""
    allowed = set(_NEUTRAL_WORDS)
    for key in claim["fields"]:
        if key not in facts:
            continue
        value = facts[key]
        if key == "system.cohort":
            cohort = re.search(r"MU-Glioma-Post|LUMIERE|UCSF-ALPTDG", str(value), re.I)
            value = cohort.group(0) if cohort else ""
        if isinstance(value, str):
            allowed.update(word.lower() for word in re.findall(r"[A-Za-z]+", value))
        if key == "meas.enhancing_cc":
            allowed.update(("enhancing", "tumour"))
        elif key == "meas.flair_hyperintensity_cc":
            allowed.update(("flair", "hyperintensity"))
        elif key == "meas.necrosis_cc":
            allowed.add("necrosis")
        elif key == "meas.cavity_cc":
            allowed.update(("resection", "cavity"))
        elif key == "meas.necrosis_and_cavity_cc":
            allowed.update(("necrosis", "cavity", "resection"))
    return sorted({word.lower() for word in re.findall(r"[A-Za-z]+", claim["text"])
                   if word.lower() not in allowed})


def _measurement_form_supported(claim: dict, facts: dict) -> bool:
    """Accept only descriptive volume/availability forms; word order cannot change their meaning."""
    keys = set(claim["fields"])
    volume_keys = keys.intersection(_MEASURED_KEYS)
    if not volume_keys and not keys.intersection(("meas.available", "meas.label")):
        return True
    actual = claim["text"].strip().casefold()
    if len(volume_keys) == 1:
        key = next(iter(volume_keys))
        label = _VOLUME_DISPLAY[key]
        base = f"{label} volume is {facts[key]:.1f} cc"
        forms = {f"{prefix}{base}{suffix}.".casefold() for prefix in ("", "The ")
                 for suffix in ("", " from automatic segmentation; indicative")}
        return actual in forms
    if volume_keys:
        return False
    if keys.intersection(("meas.available", "meas.label")):
        forms = ("No usable segmentation volumes are available.", "No segmentation volumes are available.",
                 "Segmentation volumes are available.", "Volumes from automatic segmentation are indicative.")
        return actual in {form.casefold() for form in forms}
    return True


def parse_facts_only(raw: str) -> list[dict] | None:
    """Parse the shared structured format while retaining each sentence's section."""
    parsed = checker.parse_structured(raw)
    if parsed is None:
        return None
    try:
        s = raw.strip()
        obj = json.loads(s[s.find("{"):s.rfind("}") + 1])
        source = obj["sentences"]
        if len(source) != len(parsed) or any(c.get("section") not in FACTS_SECTIONS or
                                             not isinstance(c.get("fields"), list) for c in source):
            return None
        return [{**claim, "section": item["section"]} for claim, item in zip(parsed, source)]
    except (ValueError, TypeError, KeyError, AttributeError):
        return None


def check_facts_only(claims: list[dict] | None, facts: dict) -> dict:
    """Check a parsed facts-only response without invoking the full-evidence checker."""
    if claims is None or not isinstance(claims, list) or not claims:
        return {"parsed": False, "n_claims": 0, "pass": False}
    shape_ok = all(isinstance(c, dict) and isinstance(c.get("text"), str) and
                   isinstance(c.get("fields"), list) and
                   all(isinstance(key, str) for key in c["fields"]) and
                   c.get("section") in FACTS_SECTIONS for c in claims)
    if not shape_ok:
        return {"parsed": False, "n_claims": len(claims), "pass": False}
    order = [FACTS_SECTIONS.index(c["section"]) for c in claims]
    ordered = order == sorted(order)
    checked = [checker.check_claim(c, facts) for c in claims]
    missing = [key for key in _required_keys(facts)
               if not any(key in c["fields"] and _contains_field_value(c, key, facts) for c in claims)]
    text = " ".join(c["text"] for c in claims)
    forbidden = checker.forbidden_v3(text)
    banned = sorted({m.group(0).lower() for m in _BANNED.finditer(text)})
    clinical_inference = sorted({m.group(0) for m in _CLINICAL_INFERENCE.finditer(text)})
    unlicensed_words = [{"text": c["text"], "words": words} for c in claims
                        if (words := _unlicensed_words(c, facts))]
    wrong_measurement_form = [c["text"] for c in claims if not _measurement_form_supported(c, facts)]
    multi_sentence = [c["text"] for c in claims
                      if re.search(r"(?<!\d)[.!?](?!\d)\s+\S", c["text"]) or not c["text"].strip()]
    semantic_mismatch = [c for c in claims if not c["fields"] or
                         any(key in facts and not _contains_field_value(c, key, facts) for key in c["fields"])]
    unsupported = [r for r in checked if not r["supported"]]
    out = {"parsed": True, "n_claims": len(claims), "n_unsupported": len(unsupported),
           "n_invalid_citations": sum(len(r["invalid_fields"]) for r in checked),
           "unsupported": unsupported, "semantic_mismatch": semantic_mismatch,
           "required": {"missing": missing, "required_pass": not missing},
           "ordered": ordered, "forbidden": forbidden, "banned_terms": banned,
           "clinical_inference": clinical_inference, "unlicensed_words": unlicensed_words,
           "multi_sentence": multi_sentence, "wrong_measurement_form": wrong_measurement_form}
    out["pass"] = not (unsupported or semantic_mismatch or missing or any(forbidden.values()) or banned or
                       clinical_inference or unlicensed_words or multi_sentence or wrong_measurement_form) and ordered
    return out


def render_facts_only(scan_label: str, facts: dict, claims: list[dict] | None) -> str:
    """Render shared measurements and facts-only prose without full-evidence tables."""
    if any(key.startswith(FULL_ONLY_PREFIXES) for key in facts):
        raise ValueError("facts-only renderer received excluded fields")
    if claims is not None and not check_facts_only(claims, facts)["pass"]:
        raise ValueError("facts-only renderer received unchecked or unsupported claims")
    titles = {"scan": "Scan", "measurements": "Measurements", "longitudinal": "Longitudinal",
              "provenance": "Provenance"}
    rows = {"scan": [("Timing", facts.get("scan.phase", "–")),
                     ("Previous scan", facts.get("scan.previous_available", "–"))],
            "measurements": [], "longitudinal": [], "provenance": []}
    for key in _MEASURED_KEYS:
        if key in facts:
            rows["measurements"].append((key.removeprefix("meas.").replace("_", " ").title(),
                                          f"{facts[key]:.1f} cc"))
    if facts.get("meas.available") == "no":
        rows["measurements"].append(("Volumes", "No usable segmentation"))
    for key in _CHANGE_KEYS:
        if key in facts:
            rows["longitudinal"].append((key.removeprefix("meas.").replace("_statement", "").replace("_", " ").title(),
                                         facts[key]))
    if "scan.rater_statement" in facts:
        rows["scan"].append(("Rater timing", facts["scan.rater_statement"]))
    lines = [f"# Scan facts: {scan_label}", ""]
    for section in FACTS_SECTIONS:
        lines += [f"## {titles[section]}", ""]
        lines += [c["text"] for c in (claims or []) if c.get("section") == section]
        if rows[section]:
            lines += ["", "| Item | Value |", "|---|---|"]
            lines += [f"| {name} | {value} |" for name, value in rows[section]]
        lines.append("")
    lines += ["## Limitations", "", _LIMITATIONS, ""]
    return "\n".join(lines)


def freeze_manifest() -> dict:
    """Describe the locked v3.1 evaluation input without copying record contents.

    A record hash covers its exact UTF-8 JSONL line, including the line ending.
    This function reads source artifacts only and does not write the manifest.
    """
    from prism.analyses import report_v3_1

    source = REPO / EVAL_RELATIVE
    records = []
    counts = Counter()
    seen = set()
    for line in source.read_bytes().splitlines(keepends=True):
        rec = json.loads(line)
        record_id = rec["record_id"]
        if record_id in seen:
            raise ValueError(f"duplicate evaluation record ID: {record_id}")
        seen.add(record_id)
        counts[rec["cohort"]] += 1
        records.append({"record_id": record_id, "sha256": hashlib.sha256(line).hexdigest()})
    writer_id, revision = report_v3_1.MODELS[report_v3_1.PRIMARY][:2]
    return {
        "source": EVAL_RELATIVE,
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "record_hash_method": "SHA-256 of exact JSONL line bytes, including line ending",
        "record_count": len(records),
        "counts_by_cohort": dict(sorted(counts.items())),
        "records": records,
        "frozen_hashes_source": FROZEN_RELATIVE,
        "frozen_hashes_txt": (REPO / FROZEN_RELATIVE).read_text(),
        "primary_writer": {"key": report_v3_1.PRIMARY, "id": writer_id, "revision": revision},
        "field_contract": {
            FACTS_ONLY: {"excluded_prefixes": list(FULL_ONLY_PREFIXES)},
            FULL_EVIDENCE: {"excluded_prefixes": []},
        },
    }
