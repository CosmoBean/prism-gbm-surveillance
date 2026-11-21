"""Checker mutation test (plan: docs/results/CHECKER_MUTATION_PLAN.md, commit 4f854cb). Synthetic records only.

Builds correct reports for 52 synthetic records, introduces one error per mutant, and counts how often the frozen
checker (check(..., card=True), the report v3.1 rule) rejects them. No patient data is read.

    PYTHONPATH=. .venv/bin/python -m prism.analyses.checker_mutation [--v3-2]
    -> outputs/results/analyses/checker_mutation/{mutants.jsonl,summary.csv}

--v3-2 (REVISION_DATA_PLAN.md R4): every correct report and mutant is first written in the v3.2 vocabulary
(facts_v3_2.new_key on the cited keys, rename_value on the text) and checked through facts_v3_2.check_v3_2, the adapter
to the frozen checker. The counts must equal the v3.1 run. Output files get the suffix _v3_2.
"""

from __future__ import annotations

import copy
import itertools
import json
import re
import sys

import pandas as pd

from prism.config import RESULTS
from prism.report import checker
from prism.report.facts_v3_1 import facts_v3_1
from tests.test_report_v3 import good_claims, record
from tests.test_report_v3_1 import lumiere, rater_claim

OUT = RESULTS / "analyses" / "checker_mutation"
WORDS = {str(i): w for i, w in enumerate("zero one two three four five six seven eight nine ten eleven twelve".split())}
WORDS.update({"56": "fifty-six", "3": "three", "8": "eight"})
APPEND = {"D1": "These findings are consistent with tumour progression.",
          "D2": "A biopsy should be considered.",
          "D3": "Progression is likely at this scan.",
          "D4": "This scan rules out progression.",
          "D5": "This scan shows stable disease.",
          "P1": "The model's AUC in this situation is 0.91."}
CAUGHT = ["N1", "N2", "N3", "N4", "F1", "F2", "C1", "C2", "A1", "A2", "T1", "T2", "R1", *APPEND]
BLIND = ["B1", "B2"]


def records():
    out = []
    for tier, sides, conf, ood in itertools.product(("few cases", "tested"),
                                                    itertools.product(("below", "above"), repeat=2),
                                                    ("{0}", "{1}", "{0, 1}"), ((), ("MGMT status unknown",))):
        out.append((f"mu|{tier}|{sides}|{conf}|{bool(ood)}", record(tier, sides, conf, ood), False))
    for rater, ood in itertools.product((False, True), (False, True)):
        r = lumiere(rater=rater)
        if not ood:
            r["flags"].update(out_of_range=False, out_of_range_reasons=[])
        out.append((f"lumiere|rater={rater}|ood={ood}", r, True))
    return out


def correct(F, is_lumiere):
    C = good_claims(F)
    for c in C:
        c["text"] = c["text"].replace("Indicative volumes, not a RANO assessment, are",
                                      "Indicative volumes from the automatic segmentation are")
    if is_lumiere and "scan.rater_statement" in F:
        C.insert(1, {"text": F["scan.rater_statement"], "fields": ["scan.rater_statement"]})
    return C


def idx(C, key):
    return [i for i, c in enumerate(C) if key in c["fields"]]


def bump(tok):
    d = len(tok.split(".")[1]) if "." in tok else 0
    return f"{float(tok) + 10 ** (1 - d):.{d}f}"


def mutants(C, F):
    """Yield (operator, claims) with exactly one error each."""
    for i, c in enumerate(C):                                       # N1: every sentence holding a number
        m = checker.NUM.search(c["text"])
        if m:
            D = copy.deepcopy(C)
            D[i]["text"] = c["text"][:m.start()] + bump(m.group()) + c["text"][m.end():]
            yield "N1", D
    for i, c in enumerate(C):                                       # N2: first small integer as a word
        m = re.search(r"(?<![\d.])(\d{1,2})(?![\d.])", c["text"])
        if m and m.group(1) in WORDS:
            D = copy.deepcopy(C)
            D[i]["text"] = c["text"][:m.start()] + WORDS[m.group(1)] + c["text"][m.end():]
            yield "N2", D
            break
    yield "N3", C + [{"text": "The previous scan was taken 7 weeks before this one.", "fields": ["scan.phase"]}]
    D = copy.deepcopy(C); D[0]["fields"] = D[0]["fields"] + ["meas.nonexistent_field"]; yield "N4", D
    oor = idx(C, "flags.out_of_range.reason")
    if F["flags.out_of_range.active"] and oor:
        yield "F1", [c for i, c in enumerate(C) if i not in oor]
    if not F["flags.out_of_range.active"]:
        yield "F2", C + [{"text": "Out of training range flag: MGMT status unknown.", "fields": ["scan.phase"]}]
    k = idx(C, "conformal.combined.80.statement")
    if k:
        t = C[k[0]]["text"]
        for a, b in (("both outcomes", "no progression only"), ("no progression only", "both outcomes"),
                     ("progression only", "both outcomes")):
            if a in t:
                D = copy.deepcopy(C); D[k[0]]["text"] = t.replace(a, b, 1); yield "C1", D
                break
        yield "C2", [c for i, c in enumerate(C) if i not in k]
    k = idx(C, "pathways.agreement_statement")
    if k:
        t = C[k[0]]["text"]
        t2 = re.sub(r"\bdisagree\b", "agree", t, count=1) if re.search(r"\bdisagree\b", t) else \
            re.sub(r"\bagree\b", "disagree", t, count=1)
        D = copy.deepcopy(C); D[k[0]]["text"] = t2; yield "A1", D
    k = idx(C, "pathway.timeline.statement")
    if k:
        t = C[k[0]]["text"]
        t2 = re.sub(r"\bbelow\b", "above", t, count=1) if " below " in t else re.sub(r"\babove\b", "below", t, count=1)
        D = copy.deepcopy(C); D[k[0]]["text"] = t2; yield "A2", D
    k = idx(C, "card.tier_statement")
    if k and F["card.tier"] != "tested":
        yield "T1", [c for i, c in enumerate(C) if i not in k]
    if k:
        t = C[k[0]]["text"]
        t2 = t.replace("few cases", "tested", 1) if "few cases" in t else t.replace("tested", "few cases", 1)
        D = copy.deepcopy(C); D[k[0]]["text"] = t2; yield "T2", D
    k = idx(C, "pathway.combined.statement")
    if k:
        yield "R1", [c for i, c in enumerate(C) if i not in k]
    for op, txt in APPEND.items():
        yield op, C + [{"text": txt, "fields": ["pathway.combined.statement"]}]
    k = idx(C, "meas.enhancing_change_since_previous_statement")
    if k and re.search(r"\b(larger|smaller)\b", C[k[0]]["text"]):
        t = C[k[0]]["text"]
        D = copy.deepcopy(C)
        D[k[0]]["text"] = re.sub(r"\b(larger|smaller)\b", lambda m: "smaller" if m.group() == "larger" else "larger", t,
                                 count=1)
        yield "B1", D
    k = idx(C, "meas.enhancing_cc")
    if k:
        t = C[k[0]]["text"]
        m = re.search(r"([\d.]+) cc of enhancing tumour and ([\d.]+) cc of FLAIR", t)
        if m:
            D = copy.deepcopy(C)
            D[k[0]]["text"] = t[:m.start()] + f"{m.group(2)} cc of enhancing tumour and {m.group(1)} cc of FLAIR" + \
                t[m.end():]
            yield "B2", D


def to_v3_2(C):
    from prism.report.facts_v3_2 import new_key, rename_value
    return [{**c, "text": rename_value(c["text"]), "fields": [new_key(k) for k in c["fields"]]} for c in C]


def main(v32: bool = False):
    from prism.report.facts_v3_2 import check_v3_2
    OUT.mkdir(parents=True, exist_ok=True)
    sfx = "_v3_2" if v32 else ""
    chk = (lambda C, F, rec: check_v3_2(to_v3_2(C), rec)) if v32 else (lambda C, F, rec: checker.check(C, F, card=True))
    rows, false_rej = [], []
    with open(OUT / f"mutants{sfx}.jsonl", "w") as fh:
        for rid, rec, is_lum in records():
            F = facts_v3_1(rec)
            C = correct(F, is_lum)
            if not chk(C, F, rec)["pass"]:
                false_rej.append(rid)
                continue
            for op, D in mutants(C, F):
                rej = not chk(D, F, rec)["pass"]
                rows.append({"record": rid, "op": op, "rejected": rej})
                fh.write(json.dumps({"record": rid, "op": op, "rejected": rej,
                                     "claims": to_v3_2(D) if v32 else D}) + "\n")
    df = pd.DataFrame(rows)
    s = df.groupby("op").rejected.agg(["size", "sum"]).rename(columns={"size": "mutants", "sum": "rejected"})
    s["rate"] = s.rejected / s.mutants
    s["expected"] = ["blind spot" if o in BLIND else "caught" for o in s.index]
    s = s.loc[[o for o in CAUGHT + BLIND if o in s.index]]
    s.to_csv(OUT / f"summary{sfx}.csv")
    print(f"records {len(records())}, correct reports rejected {len(false_rej)} {false_rej}")
    print(s.to_string())
    caught = df[df.op.isin(CAUGHT)]
    print(f"expected-caught operators: {caught.rejected.sum()} of {len(caught)} mutants rejected")
    for _, r in df[df.op.isin(CAUGHT) & ~df.rejected].head(10).iterrows():
        print("MISSED", r.op, r.record)


if __name__ == "__main__":
    main("--v3-2" in sys.argv)
