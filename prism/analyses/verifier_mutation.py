"""M3 evaluation of the bound verifier (plan: docs/results/METHODS_PLAN.md, commit 1363773).

1. Synthetic records (checker_mutation.records): the existing operators plus the held-out B3-B5 fixed in the plan,
   each mutant checked by the frozen checker and by the verifier.
2. Real reports (report_v3_2 evaluation set: v3.2 language model and template): false rejections of the unmutated
   reports by rule, and every operator applied where its pattern occurs. Only counts are printed or written.

    PRISM_SKIP_UCSF=1 PYTHONPATH=. .venv/bin/python -m prism.analyses.verifier_mutation
    -> outputs/results/analyses/verifier_mutation/{synthetic.csv,real.csv,real_false_rejections.csv}
"""

from __future__ import annotations

import copy
import json
import re

import pandas as pd

from prism.analyses import checker_mutation as CM
from prism.config import RESULTS
from prism.report import checker
from prism.report import verifier as V
from prism.report.facts_v3_1 import facts_v3_1

OUT = RESULTS / "analyses" / "verifier_mutation"
HELD_OUT = ["B3", "B4", "B5"]


def held_out(C, F):
    k = CM.idx(C, "meas.enhancing_change_since_previous_statement")
    if k:
        s = str(F["meas.enhancing_change_since_previous_statement"])
        w = "increased" if re.search(r"\bsmaller\b", s) else "decreased" if re.search(r"\blarger\b", s) else None
        if w:
            D = copy.deepcopy(C)
            D[k[0]] = {"text": f"Enhancing tumour {w} since the previous scan.",
                       "fields": ["meas.enhancing_change_since_previous_statement"]}
            yield "B3", D
    k = CM.idx(C, "pathway.timeline.statement")
    a, b = F.get("pathway.timeline.score"), F.get("pathway.images.score")
    if k and a is not None and b is not None and a != b:
        t = C[k[0]]["text"]
        m = re.search(r"(timeline pathway score )([\d.]+)", t)
        if m:
            dec = len(m.group(2).split(".")[1]) if "." in m.group(2) else 0
            D = copy.deepcopy(C)
            D[k[0]]["text"] = t[:m.start(2)] + f"{b:.{dec}f}" + t[m.end(2):]
            D[k[0]]["fields"] = D[k[0]]["fields"] + ["pathway.images.statement"]
            yield "B4", D
    k = CM.idx(C, "meas.enhancing_cc")
    e, f = F.get("meas.enhancing_cc"), F.get("meas.flair_hyperintensity_cc")
    if k and e is not None and f is not None and e != f:
        D = copy.deepcopy(C)
        D[k[0]] = {"text": f"Enhancing tumour measured {f} cc.", "fields": ["meas.enhancing_cc",
                                                                             "meas.flair_hyperintensity_cc"]}
        yield "B5", D


def all_mutants(C, F):
    yield from CM.mutants(C, F)
    yield from held_out(C, F)


def run_set(items, label):
    """items: iterable of (id, claims (v3.1 vocabulary), F). Returns (mutant rows, unmutated rows)."""
    rows, base = [], []
    for rid, C, F in items:
        fz = checker.check(C, F, card=True)["pass"]
        vr = V.verify(C, F)
        rules = sorted({b.split()[0] for v in vr["bound"].values() for b in v})
        base.append({"set": label, "id": rid, "frozen_pass": fz, "verifier_pass": vr["pass"], "rules": "+".join(rules)})
        if not (fz and vr["pass"]):
            continue
        for op, D in all_mutants(C, F):
            rows.append({"set": label, "op": op, "frozen_rejected": not checker.check(D, F, card=True)["pass"],
                         "verifier_rejected": not V.verify(D, F)["pass"]})
    return pd.DataFrame(rows), pd.DataFrame(base)


def summarise(df):
    g = df.groupby(["set", "op"]).agg(mutants=("op", "size"), frozen=("frozen_rejected", "mean"),
                                      verifier=("verifier_rejected", "mean")).reset_index()
    return g


def synthetic():
    for rid, rec, is_lum in CM.records():
        F = facts_v3_1(rec)
        yield rid, CM.correct(F, is_lum), F


def real(version):
    from prism.analyses import report_v3_2 as RV
    from prism.report.facts_v3_2 import back_claims
    recs = RV.load_set("eval")
    outs = {} if version == "template" else \
        {o["id"]: o for o in map(json.loads, open(RV.OUT / "llm" / f"outputs_eval_{version}.jsonl"))}
    for sid, rec in recs.items():
        F1 = facts_v3_1(rec)
        if version == "template":
            claims = RV.template_claims(rec)
        else:
            o = outs.get(f"eval|{sid}")
            claims = checker.parse_structured(o["text"]) if o else None
        if claims is None:
            continue
        yield f"{rec['cohort']}|{sid}", back_claims(claims, F1), F1


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    m_syn, b_syn = run_set(synthetic(), "synthetic")
    parts = [run_set(real(v), f"real_{v}") for v in ("v3_2", "template")]
    m_all = pd.concat([m_syn] + [p[0] for p in parts])
    b_all = pd.concat([b_syn] + [p[1] for p in parts])
    s = summarise(m_all)
    s.to_csv(OUT / "mutants.csv", index=False)
    b_all["cohort"] = b_all.id.str.split("|").str[0]
    fr = b_all.groupby(["set", "cohort"]).agg(reports=("id", "size"), frozen_pass=("frozen_pass", "sum"),
                                              verifier_pass=("verifier_pass", "sum")).reset_index()
    rules = b_all[~b_all.verifier_pass & b_all.frozen_pass].groupby(["set", "rules"]).size().rename("n").reset_index()
    fr.to_csv(OUT / "false_rejections.csv", index=False)
    rules.to_csv(OUT / "false_rejection_rules.csv", index=False)
    pd.set_option("display.width", 200)
    pd.set_option("display.max_rows", 200)
    print(s.round(3).to_string(index=False))
    print(fr.to_string(index=False))
    print(rules.to_string(index=False))


if __name__ == "__main__":
    main()
