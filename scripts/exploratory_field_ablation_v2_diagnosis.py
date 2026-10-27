"""EXPLORATORY (not pre-registered): aggregate diagnosis of two facts-only v2 results, written after seeing them.

1. Full-arm shared-fact stress misses: whether a sentence citing the change statement cites the key, contains the new
   statement verbatim, and states the new magnitude and direction.
2. Full-arm clinical-inference matches on the evaluation set: which pattern branch and trigger words matched, whether
   the sentence cites a model-derived key, and which model-derived fact value also matches the pattern.
3. Shared-key coverage: which shared keys the facts-only report cites (in supported claims with valid citations) and the
   full report does not.

Reads the frozen v2 outputs locally and prints counts only: no record IDs, no report text.

    PYTHONPATH=. .venv/bin/python scripts/exploratory_field_ablation_v2_diagnosis.py
"""

from __future__ import annotations

import collections
import json
import re
from pathlib import Path

from prism.analyses import report_field_ablation as V1
from prism.analyses import report_field_ablation_v2 as V2
from prism.config import REPO
from prism.report import checker, facts_only_v2 as S, field_ablation as A


def _outputs(name: str) -> dict[str, dict]:
    return {row["id"]: row for row in V1._jsonl(V2.OUT2 / "llm" / name)}


def stress_full() -> dict:
    outs = _outputs("outputs_stress_full_evidence.jsonl")
    key = V1.STATEMENT_KEY
    counts = collections.Counter()
    for entry in V1._stress_entries(REPO, V1.OUT):
        facts = A.facts_for_arm(entry["record"], A.FULL_EVIDENCE)
        row = next(v for k, v in outs.items() if entry["perturbed_id"] in k)
        claims = checker.parse_structured(row["text"]) or []
        statement = facts[key].casefold().strip().rstrip(".")
        cc = float(facts["meas.enhancing_change_since_previous_cc"])
        words = ("larger", "increase") if cc > 0 else ("smaller", "decrease")
        cited = [c["text"] for c in claims if key in c.get("fields", [])]
        magnitude = any(checker.matches(n, [abs(cc)], False) for t in cited for n in checker.numbers(t))
        direction = any(w in t.casefold() for t in cited for w in words)
        counts["n"] += 1
        counts["cites change key"] += bool(cited)
        counts["new statement verbatim in a citing sentence"] += any(statement in t.casefold() for t in cited)
        counts["new magnitude and direction in a citing sentence"] += magnitude and direction
    return dict(counts)


def clinical_inference_full() -> dict:
    manifest = V1._guard(REPO, V1.OUT)
    records = V1._records(REPO)
    outs = _outputs("outputs_full_evidence.jsonl")
    counts, triggers, sources = collections.Counter(), collections.Counter(), collections.Counter()
    for item in manifest["records"]:
        facts = A.facts_for_arm(records[item["record_id"]], A.FULL_EVIDENCE)
        shared = {k: v for k, v in facts.items() if not k.startswith(A.FULL_ONLY_PREFIXES)}
        model_values = {k: v for k, v in facts.items() if k.startswith(A.FULL_ONLY_PREFIXES) and isinstance(v, str)}
        hit = False
        for claim in checker.parse_structured(outs[f"eval|{item['record_id']}"]["text"]) or []:
            for match in A._CLINICAL_INFERENCE.finditer(S._without_statements(claim["text"], shared)):
                hit = True
                words = re.findall(r"\w+", match.group(0).casefold())
                triggers[f"{words[0]} … {words[-1]}"] += 1
                counts["matches"] += 1
                counts["in a sentence citing a model-derived key"] += any(
                    k.startswith(A.FULL_ONLY_PREFIXES) for k in claim.get("fields", []))
                for key, value in model_values.items():
                    if A._CLINICAL_INFERENCE.search(value):
                        sources[key] += 1
        counts["reports with a match"] += hit
    return {**counts, "trigger words": dict(triggers), "model-derived fact values that also match": dict(sources)}


def shared_keys_missing_from_full() -> dict:
    manifest = V1._guard(REPO, V1.OUT)
    records = V1._records(REPO)
    full, facts_only = _outputs("outputs_full_evidence.jsonl"), _outputs("outputs_facts_only_v2.jsonl")
    missing = collections.Counter()

    def cited(row: dict, facts: dict, shared: dict) -> set[str]:
        keys = set()
        for claim in checker.parse_structured(row["text"]) or []:
            result = checker.check_claim(claim, facts)
            if result["supported"] and not result["invalid_fields"]:
                keys |= {k for k in claim["fields"] if k in shared}
        return keys

    for item in manifest["records"]:
        rec = records[item["record_id"]]
        facts, shared = A.facts_for_arm(rec, A.FULL_EVIDENCE), A.facts_for_arm(rec, A.FACTS_ONLY)
        rid = f"eval|{item['record_id']}"
        missing.update(cited(facts_only[rid], shared, shared) - cited(full[rid], facts, shared))
    return dict(missing.most_common())


if __name__ == "__main__":
    print("full-arm stress (n=6):", json.dumps(stress_full()))
    print("full-arm clinical-inference pattern (406 reports):", json.dumps(clinical_inference_full(), ensure_ascii=False))
    print("shared keys cited by facts-only, not by full (reports):", json.dumps(shared_keys_missing_from_full()))
