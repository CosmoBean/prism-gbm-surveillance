"""Field partition for the paired v3.1 report ablation."""

from __future__ import annotations

from collections import Counter
import hashlib
import json

from prism.config import REPO
from prism.report.facts_v3_1 import facts_v3_1

FACTS_ONLY = "facts_only"
FULL_EVIDENCE = "full_evidence"
FULL_ONLY_PREFIXES = ("pathway.", "pathways.", "conformal.", "card.", "flags.")
EVAL_RELATIVE = "outputs/results/analyses/report_v3_1/records/eval.jsonl"
FROZEN_RELATIVE = "outputs/results/analyses/report_v3_1/FROZEN_hashes.txt"


def facts_for_arm(rec: dict, arm: str) -> dict:
    """Build the v3.1 facts once, then apply the strict arm field contract."""
    if arm not in (FACTS_ONLY, FULL_EVIDENCE):
        raise ValueError(f"unknown report field arm: {arm}")
    facts = facts_v3_1(rec)
    if arm == FULL_EVIDENCE:
        return facts
    return {key: value for key, value in facts.items() if not key.startswith(FULL_ONLY_PREFIXES)}


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
