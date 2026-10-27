# EXPLORATORY (post hoc, 2026-10-26): diagnosis of why the facts-only ablation reports fail their frozen checker.
# Not pre-registered. Re-runs check_facts_only on the saved facts-only outputs and writes aggregate counts only
# (no record IDs, no report text) to outputs/results/analyses/report_field_ablation/diagnosis_posthoc.csv.
# Run: PYTHONPATH=. .venv/bin/python scripts/exploratory_field_ablation_diagnosis.py  (seconds; prints results)
import collections, re
import pandas as pd
from prism.analyses import report_field_ablation as P
from prism.report import field_ablation as A

records = P._records(P.REPO)
outputs = {r["id"]: r for r in P._jsonl(P.OUT / "llm/outputs_facts_only.jsonl")}
rows = []
def add(group, name, value, denominator=None):
    rows.append({"group": group, "name": name, "value": value, "denominator": denominator})

criteria = collections.Counter(); per_report = collections.Counter(); missing = collections.Counter()
required = collections.Counter(); banned = collections.Counter(); words = collections.Counter()
forms = collections.Counter(); n_parsed = 0; below_facts = 0; below_both = 0; below_banned = 0
for rid, rec in records.items():
    facts = A.facts_for_arm(rec, A.FACTS_ONLY)
    out = outputs.get(f"eval|{rid}")
    claims = A.parse_facts_only(out["text"]) if out else None
    check = A.check_facts_only(claims, facts)
    for key in A._required_keys(facts):
        required[key] += 1
    facts_below = any(isinstance(v, str) and re.search(r"\bbelow\b", v, re.I) for v in facts.values())
    below_facts += facts_below
    if not check["parsed"]:
        continue
    n_parsed += 1
    failed = {"wrong_measurement_form": bool(check["wrong_measurement_form"]),
              "unlicensed_words": bool(check["unlicensed_words"]),
              "required_missing": bool(check["required"]["missing"]),
              "semantic_mismatch": bool(check["semantic_mismatch"]),
              "banned_terms": bool(check["banned_terms"]),
              "unsupported_number": bool(check["unsupported"]),
              "invalid_citation": bool(check["n_invalid_citations"]),
              "forbidden_wording": any(check["forbidden"].values()),
              "clinical_inference": bool(check["clinical_inference"]),
              "multi_sentence": bool(check["multi_sentence"]),
              "not_ordered": not check["ordered"]}
    for name, value in failed.items():
        criteria[name] += value
    per_report[sum(failed.values())] += 1
    for key in check["required"]["missing"]:
        missing[key] += 1
    for term in check["banned_terms"]:
        banned[term] += 1
    has_below = "below" in check["banned_terms"]
    below_banned += has_below
    below_both += has_below and facts_below
    for claim in claims:
        keys = set(claim["fields"]); volume = keys & set(A._MEASURED_KEYS)
        kind = ("single_volume" if len(volume) == 1 else "multi_volume" if volume else
                "availability_label" if keys & {"meas.available", "meas.label"} else None)
        if kind:
            forms[(kind, "total")] += 1
            forms[(kind, "accepted")] += A._measurement_form_supported(claim, facts)
        for word in A._unlicensed_words(claim, facts):
            words[word] += 1

add("reports", "n", len(records)); add("reports", "parsed", n_parsed, len(records))
for name, value in criteria.items():
    add("criterion_reports_failing", name, value, n_parsed)
for k in sorted(per_report):
    add("criteria_failed_per_report", str(k), per_report[k], n_parsed)
for key in required:
    add("required_key_missing", key, missing[key], required[key])
for term, value in banned.most_common():
    add("banned_term_reports", term, value, n_parsed)
add("below", "records_with_below_in_facts", below_facts, len(records))
add("below", "reports_with_banned_below", below_banned, n_parsed)
add("below", "reports_with_banned_below_and_below_in_facts", below_both, below_banned)
for kind in ("single_volume", "multi_volume", "availability_label"):
    add("sentence_form_accepted", kind, forms[(kind, "accepted")], forms[(kind, "total")])
for word, value in words.most_common(10):
    add("unlicensed_word_sentences", word, value)
frame = pd.DataFrame(rows)
frame.to_csv(P.OUT / "diagnosis_posthoc.csv", index=False)
print(frame.to_string(index=False))
