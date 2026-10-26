"""Report facts v3.1 (docs/results/REPORT_V3_1_PLAN.md section 1): facts_v3 with two changes.

1. The LUMIERE rater flag carries its own words, number included: `scan.rater_statement` = "The rater recorded this
   scan as within 3 months after radiotherapy: yes." (or "no."), replacing the bare yes / no field
   `scan.rater_within_3_months_after_rt`, so the "3" a report writes is in the cited field.
2. No number words in any fact value: every word the frozen checker counts as a number word (checker.NUMBER_WORDS:
   three ... ninety, hundred, half, twice, ...) is written as digits ("3 segmentation volumes", not "three").

`system.version` stays "v3" so the frozen checker (checker.py, blob 26d6637a...) applies its v3 rules unchanged;
`system.facts_version` = "v3.1" marks the view. No label, no outcome, no other scan's data enters the facts.
"""

from __future__ import annotations

import re

from prism.report.facts_v3 import active_flags, facts_v3  # noqa: F401  (active_flags re-exported)

FACTS_VERSION = "v3.1"
RATER_STATEMENT = "The rater recorded this scan as within 3 months after radiotherapy: {}."
DIGITS = {"three": "3", "four": "4", "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9", "ten": "10",
          "eleven": "11", "twelve": "12", "thirteen": "13", "fourteen": "14", "fifteen": "15", "sixteen": "16",
          "seventeen": "17", "eighteen": "18", "nineteen": "19", "twenty": "20", "thirty": "30", "forty": "40",
          "fifty": "50", "sixty": "60", "seventy": "70", "eighty": "80", "ninety": "90", "hundred": "100",
          "thousand": "1000"}


def digits(s: str) -> str:
    """Number words -> digits. Words with no digit form (half, quarter, twice, double, triple, tenfold) are not
    expected in facts values; facts_v3_1 asserts none remains."""
    return re.sub(r"\b(" + "|".join(DIGITS) + r")\b", lambda m: DIGITS[m.group(1).lower()], s, flags=re.I)


def facts_v3_1(rec: dict) -> dict:
    from prism.report.checker import NUMBER_WORDS
    F3 = facts_v3(rec)
    F = {}
    for k, v in F3.items():
        if k == "scan.rater_within_3_months_after_rt":
            F["scan.rater_statement"] = RATER_STATEMENT.format(v)
            continue
        F[k] = digits(v) if isinstance(v, str) else v
        if k == "system.version":
            F["system.facts_version"] = FACTS_VERSION
    bad = [k for k, v in F.items() if isinstance(v, str) and NUMBER_WORDS.search(v)]
    assert not bad, f"number words left in facts: {bad}"
    return F
