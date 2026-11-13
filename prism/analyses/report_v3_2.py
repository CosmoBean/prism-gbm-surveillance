"""Report v3.2 (REVISION_DATA_PLAN.md R4) and the template baseline (R3), on MU and LUMIERE.

    PYTHONPATH=. .venv/bin/python -m prism.analyses.report_v3_2 --steps <step> [...]

Steps
  select     development patients by the v3 and v3.1 rules (MU 20, seed 20261026; LUMIERE 10, seed 20261027). The
             v3.1 selection files were lost in the 2026-11-02 reset; the rules are deterministic, so this redoes them
  sets       dev and eval record sets as v3.1 (MU and LUMIERE only; UCSF not on disk)
  requests   v3.1 requests (prompt v3.4, reproduction of the frozen v3.1 run) and v3.2 requests (prompt v3.5)
  generate   local vLLM, offline, one GPU (report_v3_1.run_vllm), for the requested --versions and --sets
  freeze     git blob hashes of facts_v3_2.py and prompts_v3_2.py, written before any v3.2 evaluation request
  evaluate   frozen checker: v3.1 directly, v3.2 through facts_v3_2.check_v3_2; template reports (R3) for eval
Outputs: outputs/results/analyses/report_v3_2/ (patient-level, git-ignored); aggregate tables summary_*.csv.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess

import numpy as np
import pandas as pd

from prism.analyses import report_v3 as R3
from prism.analyses import report_v3_1 as R31
from prism.config import REPO, RESULTS

OUT = RESULTS / "analyses" / "report_v3_2"
COHORTS = ("mu", "lumiere")


def select_step(_a=None):
    pop = R3.dev_population()
    pats = sorted(pop.patient_id.unique())
    mu = sorted(np.random.default_rng(R3.DEV_SEED).choice(pats, R3.N_DEV, replace=False).tolist())
    recs = R31._external_population("lumiere")
    lp = sorted({r["patient_id"] for r in recs})
    lu = sorted(np.random.default_rng(R31.DEV_SEED).choice(lp, R31.N_DEV_EXT, replace=False).tolist())
    obj = {"rules": "v3 (MU) and v3.1 (LUMIERE) rules, redone after the reset", "mu": mu, "lumiere": lu,
           "n_population": {"mu": len(pats), "lumiere": len(lp)}}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "dev_patients.json").write_text(json.dumps(obj, indent=1))
    print({k: len(v) for k, v in obj.items() if isinstance(v, list)}, obj["n_population"], flush=True)


def load_set(s):
    return {r["record_id"]: r for r in map(json.loads, open(OUT / "records" / f"{s}.jsonl"))}


def sets_step(_a=None):
    dev = json.loads((OUT / "dev_patients.json").read_text())
    out = {"dev": [], "eval": []}
    mem = R3._members("mu")
    mu = [r for r in map(json.loads, open(R31.SYSTEM / "records_mu.jsonl"))
          if r["population"] == "grade4" and r["record_id"] in mem]
    for coh, recs in (("mu", mu), ("lumiere", R31._external_population("lumiere"))):
        for r in recs:
            out["dev" if r["patient_id"] in set(dev[coh]) else "eval"].append(r)
    (OUT / "records").mkdir(parents=True, exist_ok=True)
    for s, rs in out.items():
        with open(OUT / "records" / f"{s}.jsonl", "w") as f:
            f.writelines(json.dumps(r) + "\n" for r in rs)
    print({s: pd.Series([r["cohort"] for r in rs]).value_counts().to_dict() for s, rs in out.items()}, flush=True)


def requests_step(a):
    from prism.report import prompts_v3_1 as P31
    from prism.report import prompts_v3_2 as P32
    from prism.report.facts_v3_1 import facts_v3_1
    from prism.report.facts_v3_2 import facts_v3_2
    (OUT / "llm").mkdir(parents=True, exist_ok=True)
    for s in a.sets:
        for v, msg, sch in (("v3_1", lambda r: P31.grounded_v3_1(facts_v3_1(r)), P31.SCHEMA),
                            ("v3_2", lambda r: P32.grounded_v3_2(facts_v3_2(r)), P32.SCHEMA)):
            if v not in a.versions:
                continue
            rows = [{"id": f"{s}|{rid}", "messages": msg(r), "max_tokens": 2048, "schema": sch}
                    for rid, r in load_set(s).items()]
            with open(OUT / "llm" / f"requests_{s}_{v}.jsonl", "w") as f:
                f.writelines(json.dumps(r) + "\n" for r in rows)
            print(f"{s} {v}: {len(rows)} requests", flush=True)


def generate_step(a):
    for s in a.sets:
        for v in a.versions:
            R31.run_vllm(R31.PRIMARY, OUT / "llm" / f"requests_{s}_{v}.jsonl", OUT / "llm" / f"outputs_{s}_{v}.jsonl")


def freeze_step(_a=None):
    files = ["prism/report/facts_v3_2.py", "prism/report/prompts_v3_2.py", "prism/report/facts_v3_1.py",
             "prism/report/prompts_v3_1.py", "prism/report/checker.py"]
    h = {f: subprocess.run(["git", "hash-object", f], cwd=REPO, capture_output=True, text=True).stdout.strip()
         for f in files}
    assert h["prism/report/checker.py"].startswith("26d6637a"), "checker changed"
    dirty = subprocess.run(["git", "status", "--porcelain", *files], cwd=REPO, capture_output=True, text=True).stdout
    assert not dirty.strip(), f"uncommitted changes: {dirty}"
    p = OUT / "FROZEN_hashes.txt"
    assert not (OUT / "llm" / "outputs_eval_v3_2.jsonl").exists(), "an evaluation run exists; freeze must precede it"
    p.write_text(json.dumps({"frozen_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), **h},
                            indent=1))
    print(p.read_text(), flush=True)


# ---------------------------------------------------------------- evaluation
def flesch(text: str) -> float:
    """Flesch reading ease (syllables by vowel groups; a rough measure, used only to compare two versions)."""
    sents = max(1, len(re.findall(r"[.!?](\s|$)", text)))
    words = re.findall(r"[A-Za-z]+", text)
    if not words:
        return np.nan
    syl = sum(max(1, len(re.findall(r"[aeiouy]+", w.lower())) - (w.lower().endswith("e") and len(w) > 2)) for w in words)
    return 206.835 - 1.015 * len(words) / sents - 84.6 * syl / len(words)


def template_claims(rec):
    """R3: the deterministic template (unit-test good_claims with the v3.1 volume label; LUMIERE rater sentence)."""
    from prism.analyses.checker_mutation import correct
    from prism.report.facts_v3_1 import facts_v3_1
    F = facts_v3_1(rec)
    return correct(F, rec["cohort"] == "lumiere")


def row(sid, rec, claims, r, version, out=None):
    from prism.report.facts_v3_1 import facts_v3_1
    F = facts_v3_1(rec)
    text = " ".join(c["text"] for c in claims) if claims else ""
    return {"scan_id": sid, "cohort": rec["cohort"], "version": version, "pass": r["pass"], "parsed": r["parsed"],
            "finish_reason": (out or {}).get("finish_reason"), "words": len(text.split()),
            "fields_cited": len({k for c in claims or [] for k in c.get("fields", [])}),
            "sentences": len(claims or []), "flesch": flesch(text),
            "old_names": bool(re.search(r"\btimeline\b|\bpathways?\b", text, re.I)),
            "card_tier_required": F["card.tier"] in ("few cases", "not tested"),
            "card_tier_stated": bool(r.get("card_tier_stated")),
            **{f"fail_{k}": v for k, v in R31.categories(r).items()}}


def evaluate_step(a):
    from prism.report import checker
    from prism.report.facts_v3_1 import facts_v3_1
    from prism.report.facts_v3_2 import check_v3_2
    rows, fails = [], {}
    for s in a.sets:
        recs = load_set(s)
        for v in a.versions + (["template"] if s == "eval" else []):
            outs = {} if v == "template" else {o["id"]: o for o in map(json.loads, open(OUT / "llm" / f"outputs_{s}_{v}.jsonl"))}
            for sid, rec in recs.items():
                o = outs.get(f"{s}|{sid}")
                if v == "template":
                    claims = template_claims(rec)
                    r = checker.check(claims, facts_v3_1(rec), card=True)
                else:
                    claims = checker.parse_structured(o["text"]) if o else None
                    r = check_v3_2(claims, rec) if v == "v3_2" else checker.check(claims, facts_v3_1(rec), card=True)
                rows.append({"set": s, **row(sid, rec, claims, r, v, o)})
                if not r["pass"]:
                    fails[f"{s}|{v}|{sid}"] = {k: r.get(k) for k in ("unsupported", "flags_omitted", "flags_spurious",
                                                                    "forbidden", "conformal", "agreement", "required",
                                                                    "card")}
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "checks.csv", index=False)
    (OUT / "check_details.json").write_text(json.dumps(fails, indent=1, default=str))
    summ = []
    for (s, v, coh), g in list(df.groupby(["set", "version", "cohort"])) + \
            [((s, v, "all"), g) for (s, v), g in df.groupby(["set", "version"])]:
        k, n = int(g["pass"].sum()), len(g)
        lo, hi = R3.wilson(k, n)
        req = g[g.card_tier_required]
        summ.append({"set": s, "version": v, "cohort": coh, "n": n, "pass": k, "pass_rate": k / n, "ci_low": lo,
                     "ci_high": hi, "S5_met": k / n >= 0.95, "tier_required": len(req),
                     "tier_stated": int(req.card_tier_stated.sum()), "words_median": float(g.words.median()),
                     "fields_cited_median": float(g.fields_cited.median()), "flesch_median": float(g.flesch.median()),
                     "old_names": int(g.old_names.sum()), "truncated": int((g.finish_reason == "length").sum()),
                     **{f"fail_{c}": int(g[f"fail_{c}"].sum()) for c in R31.CATEGORIES}})
    sm = pd.DataFrame(summ)
    sm.to_csv(OUT / "summary.csv", index=False)
    pd.set_option("display.width", 250)
    print(sm.drop(columns=[c for c in sm if c.startswith("fail_")]).round(3).to_string(index=False), flush=True)
    print(sm[["set", "version", "cohort"] + [c for c in sm if c.startswith("fail_")]].to_string(index=False), flush=True)


STEPS = {"select": select_step, "sets": sets_step, "requests": requests_step, "generate": generate_step,
         "freeze": freeze_step, "evaluate": evaluate_step}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", nargs="+", required=True, choices=list(STEPS))
    ap.add_argument("--sets", nargs="+", default=["dev"])
    ap.add_argument("--versions", nargs="+", default=["v3_1", "v3_2"])
    a = ap.parse_args(argv)
    for s in a.steps:
        STEPS[s](a)


if __name__ == "__main__":
    main()
