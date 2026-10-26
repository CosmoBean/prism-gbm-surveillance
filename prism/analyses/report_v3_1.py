"""PRISM report version 3.1: the LUMIERE rater-flag fix, external records in development, and a model-size ladder
(docs/results/REPORT_V3_1_PLAN.md, commit 4f7e7b9; results docs/results/REPORT_V3_1.md).

    PYTHONPATH=. .venv/bin/python -m prism.analyses.report_v3_1 --steps <step> [...] [--sets dev eval stress]
        [--model qwen3.8-27b] [--tag <suffix>]

Steps
  select     10 LUMIERE + 10 UCSF grade-4 development patients, seed 20261027 (plan section 2), chosen before any
             v3.1 report; written once to outputs/results/analyses/report_v3_1/dev_patients_v3_1.json, never redone
  sets       development (MU dev patients of v3 + the 20 external) and evaluation record sets
  requests   LLM requests (facts v3.1 + prompt v3.4) for a set
  generate   local vLLM run, offline, one GPU (prism.report.vllm_run); --model picks a ladder model
  evaluate   frozen checker (v3 rules; facts keep system.version "v3") -> S5, S6; stress set -> S7
  stress     the new 30-record perturbation set (seed 1, 6 per kind) from the v3.1 evaluation records
  render     markdown reports (no figure); examples: 3 HTML reports with the figure (v3.1 title, no RANO)
  ladder     one table over the ladder models (plan section 4)
v3 (prism/analyses/report_v3.py, outputs/results/analyses/report_v3/) is untouched. Labels are never read: only the
membership column of the *_EVALUATION_ONLY.csv files (via report_v3._members).
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import time
from pathlib import Path

import numpy as np
import pandas as pd

from prism.analyses import report_v3 as R3
from prism.config import REPO, RESULTS

OUT = RESULTS / "analyses" / "report_v3_1"
SYSTEM = R3.SYSTEM
DEV_SEED = 20261027
N_DEV_EXT = 10
STRESS_SEED = 1
NT = {"enable_thinking": False}
# key -> (hf id, pinned revision, chat-template kwargs, vllm_run extra args). Qwen: non-thinking mode (as v3);
# Gemma: its default chat template.
MODELS = {
    "qwen3.5-2b": ("Qwen/Qwen3.5-2B", "15852e8c16360a2fea060d615a32b45270f8a8fc", NT, ()),
    "qwen3.5-4b": ("Qwen/Qwen3.5-4B", "851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a", NT, ()),
    "qwen3.5-9b": ("Qwen/Qwen3.5-9B", "c202236235762e1c871ad0ccb60c8ee5ba337b9a", NT, ()),
    "qwen3.8-27b": ("Qwen/Qwen3.8-27B", "1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0", NT, ()),
    "qwen3.5-35b-a3b": ("Qwen/Qwen3.5-35B-A3B", "59d61f3ce65a6d9863b86d2e96597125219dc754", NT, ()),
    "gemma-4-e4b-it": ("google/gemma-4-E4B-it", "ee0ef6023621cff504d758262d4e04895a5af4a2", {},
                       ("--mm-limit", '{"image": 0, "video": 0, "audio": 0}')),
    "gemma-4-31b-it": ("google/gemma-4-31B-it", "842da3794eaa0b77d5f08bae87a17459d91ff475", {}, ()),
}
PRIMARY = "qwen3.8-27b"
assert MODELS[PRIMARY][1] == R3.WRITER[1]  # same pinned revision as v3


def _tag(model: str, tag: str = "") -> str:
    return ("" if model == PRIMARY else f"_{model}") + tag


# ---------------------------------------------------------------- development patients (plan section 2)
def _external_population(coh: str) -> list[dict]:
    """The v3 evaluation population of an external cohort: LUMIERE all detection scans (eval_all), UCSF every
    grade-4 scan-2 record. Membership column only."""
    mem = R3._members(coh)
    out = []
    for l in open(SYSTEM / f"records_{coh}.jsonl"):
        r = json.loads(l)
        if r["population"] != "grade4" or (mem is not None and r["record_id"] not in mem):
            continue
        if coh == "ucsf" and not r["population_flags"].get("scan2"):
            continue
        out.append(r)
    return out


def select_step(_sets=None):
    p = OUT / "dev_patients_v3_1.json"
    if p.exists():
        print(f"{p} exists; selection is fixed, not redone", flush=True)
        return json.loads(p.read_text())
    assert not (OUT / "llm").exists(), "a v3.1 generation exists; selection must precede it"
    obj = {"seed": DEV_SEED, "n_per_cohort": N_DEV_EXT,
           "rule": "per cohort: numpy.random.default_rng(20261027).choice(sorted patient ids, 10, replace=False), "
                   "sorted (a fresh generator per cohort)",
           "population": {"lumiere": "patients with a LUMIERE detection scan (eval_all)",
                          "ucsf": "patients with a UCSF grade-4 scan-2 record"},
           "selected_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "cohorts": {}}
    for coh in ("lumiere", "ucsf"):
        recs = _external_population(coh)
        pats = sorted({r["patient_id"] for r in recs})
        dev = sorted(np.random.default_rng(DEV_SEED).choice(pats, N_DEV_EXT, replace=False).tolist())
        obj["cohorts"][coh] = {"n_patients_in_population": len(pats), "n_scans_in_population": len(recs),
                               "n_dev_scans": sum(r["patient_id"] in dev for r in recs), "patients": dev}
    OUT.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=1))
    print({c: {k: v for k, v in d.items() if k != "patients"} for c, d in obj["cohorts"].items()}, flush=True)
    return obj


# ---------------------------------------------------------------- record sets (plan sections 2-3)
def load_set(s: str) -> dict:
    return {r["record_id"]: r for r in map(json.loads, open(OUT / "records" / f"{s}.jsonl"))}


def sets_step(_sets=None):
    """dev: the 20 MU development patients' intended-use scans (v3 dev_patients.json) + all records of the 10 + 10
    external development patients; eval: every other record of the v3 evaluation population."""
    assert R3.records_ready(), "system records not ready"
    mu_dev = set(json.loads((R3.OUT / "dev_patients.json").read_text())["patients"])
    ext = json.loads((OUT / "dev_patients_v3_1.json").read_text())["cohorts"]
    dev = {"mu": mu_dev, "lumiere": set(ext["lumiere"]["patients"]), "ucsf": set(ext["ucsf"]["patients"])}
    out = {"dev": [], "eval": []}
    for coh in ("mu", "lumiere", "ucsf"):
        if coh == "mu":
            mem = R3._members("mu")
            recs = [r for r in map(json.loads, open(SYSTEM / "records_mu.jsonl"))
                    if r["population"] == "grade4" and r["record_id"] in mem]
        else:
            recs = _external_population(coh)
        for r in recs:
            out["dev" if r["patient_id"] in dev[coh] else "eval"].append(r)
    (OUT / "records").mkdir(parents=True, exist_ok=True)
    for s, rs in out.items():
        with open(OUT / "records" / f"{s}.jsonl", "w") as f:
            f.writelines(json.dumps(r) + "\n" for r in rs)
    summ = {s: pd.Series([r["cohort"] for r in rs]).value_counts().to_dict() for s, rs in out.items()}
    summ["patients"] = {s: pd.Series([r["cohort"] for r in {r["patient_id"]: r for r in rs}.values()])
                        .value_counts().to_dict() for s, rs in out.items()}
    ev_p = {(r["cohort"], r["patient_id"]) for r in out["eval"]}
    assert not ev_p & {(r["cohort"], r["patient_id"]) for r in out["dev"]}
    (OUT / "sets.json").write_text(json.dumps(summ, indent=1))
    print(summ, flush=True)


# ---------------------------------------------------------------- requests / generation
def _facts(rec):
    from prism.report.facts_v3_1 import facts_v3_1
    return facts_v3_1(rec)


def requests_step(sets):
    from prism.report import prompts_v3_1 as P
    (OUT / "llm").mkdir(parents=True, exist_ok=True)
    for s in sets:
        rows = [{"id": f"{s}|{rid}", "messages": P.grounded_v3_1(_facts(r)), "max_tokens": 2048, "schema": P.SCHEMA}
                for rid, r in load_set(s).items()]
        with open(OUT / "llm" / f"requests_{s}.jsonl", "w") as f:
            f.writelines(json.dumps(r) + "\n" for r in rows)
        print(f"{s}: {len(rows)} requests (prompt {P.VERSION})", flush=True)


def run_vllm(model: str, req: Path, out: Path, max_len=8192, gpu_mem=0.90):
    mid, rev, ck, extra = MODELS[model]
    cmd = [f"{R3.LLM_ENV}/bin/python", "-m", "prism.report.vllm_run", "--model", mid, "--revision", rev,
           "--requests", str(req), "--out", str(out), "--tp", "1", "--chat-kwargs", json.dumps(ck),
           "--max-model-len", str(max_len), "--gpu-mem", str(gpu_mem), *extra]
    env = {**os.environ, "PYTHONPATH": str(REPO), "PATH": f"{R3.LLM_ENV}/bin:{os.environ['PATH']}",
           "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1", "VLLM_NO_USAGE_STATS": "1", "DO_NOT_TRACK": "1"}
    log = out.with_suffix(".log")
    print(" ".join(cmd), "->", log, flush=True)
    t = time.time()
    smi = subprocess.Popen(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits", "-lms", "2000"],
                           stdout=open(out.with_suffix(".gpumem"), "w"))
    try:
        with open(log, "w") as lf:
            subprocess.run(cmd, env=env, check=True, cwd=REPO, stdout=lf, stderr=subprocess.STDOUT)
    finally:
        smi.terminate()
    print(f"{out.name} done in {time.time() - t:.0f}s", flush=True)


def generate_step(sets, model=PRIMARY, tag=""):
    for s in sets:
        run_vllm(model, OUT / "llm" / f"requests_{s}.jsonl", OUT / "llm" / f"outputs_{s}{_tag(model, tag)}.jsonl")


def load_outputs(s, tg=""):
    p = OUT / "llm" / f"outputs_{s}{tg}.jsonl"
    return {r["id"]: r for r in map(json.loads, open(p))} if p.exists() else {}


# ---------------------------------------------------------------- evaluation (frozen checker, v3 rules)
CATEGORIES = ("unparsed", "unsupported_number", "missing_flag", "spurious_flag", "forbidden_wording",
              "conformal_or_agreement_error", "invalid_citation", "required_missing", "card_rule")


def categories(r: dict) -> dict:
    """Failure categories of one checker result (plan section 4; required content and the card rule added so that
    every failing report has a category)."""
    if not r["parsed"]:
        return {c: c == "unparsed" for c in CATEGORIES}
    return {"unparsed": False,
            "unsupported_number": any(u["unsupported_numbers"] or u.get("number_words") for u in r["unsupported"]),
            "missing_flag": bool(r["flags_omitted"]), "spurious_flag": bool(r["flags_spurious"]),
            "forbidden_wording": r["any_forbidden"],
            "conformal_or_agreement_error": not (r["conformal"]["conformal_pass"] and r["agreement"]["agreement_pass"]),
            "invalid_citation": r["n_invalid_citations"] > 0, "required_missing": not r["required"]["required_pass"],
            "card_rule": not r["card"]["card_pass"]}


def check_row(sid, rec, out):
    from prism.report import checker
    F = _facts(rec)
    claims = checker.parse_structured(out["text"]) if out else None
    r = checker.check(claims, F, card=True)
    row = {"scan_id": sid, "cohort": rec["cohort"], "pass": r["pass"], "parsed": r["parsed"],
           "finish_reason": (out or {}).get("finish_reason"), "n_output_tokens": (out or {}).get("n_output_tokens"),
           "words": len(" ".join(c["text"] for c in claims).split()) if claims else 0,
           "card_tier": F["card.tier"], "card_tier_required": F["card.tier"] in ("few cases", "not tested"),
           "card_tier_stated": bool(r.get("card_tier_stated"))}
    row.update({f"fail_{k}": v for k, v in categories(r).items()})
    if r["parsed"]:
        for k, v in r["forbidden"].items():
            row[f"forbidden_{k}"] = bool(v)
    return row, r, claims


def evaluate_set(s, tg=""):
    recs, outs = load_set(s), load_outputs(s, tg)
    assert outs, f"no outputs for {s}{tg}"
    rows, details = [], {}
    for sid, rec in recs.items():
        row, r, claims = check_row(sid, rec, outs.get(f"{s}|{sid}"))
        rows.append(row)
        if not r["pass"]:
            details[sid] = {k: r.get(k) for k in ("unsupported", "flags_omitted", "flags_spurious", "forbidden",
                                                  "conformal", "agreement", "required", "card")}
            details[sid]["claims"] = claims
    df = pd.DataFrame(rows)
    df.to_csv(OUT / f"checks_{s}{tg}.csv", index=False)
    (OUT / f"check_details_{s}{tg}.json").write_text(json.dumps(details, indent=1, default=str))
    return df


def summarise(df: pd.DataFrame) -> pd.DataFrame:
    out = []
    for coh, g in [("all", df)] + list(df.groupby("cohort")):
        n, k = len(g), int(g["pass"].sum())
        req = g[g.card_tier_required]
        ks = int(req.card_tier_stated.sum())
        lo, hi = R3.wilson(k, n)
        row = {"cohort": coh, "n": n, "pass": k, "pass_rate": k / n, "pass_ci_low": lo, "pass_ci_high": hi,
               "S5_met": k / n >= 0.95, "tier_required": len(req), "tier_stated": ks,
               "S6_met": ks == len(req) if len(req) else None, "parsed": int(g.parsed.sum()),
               "truncated": int((g.finish_reason == "length").sum()), "words_median": float(g.words.median())}
        row.update({f"fail_{c}": int(g[f"fail_{c}"].sum()) for c in CATEGORIES})
        out.append(row)
    return pd.DataFrame(out)


def evaluate_step(sets, model=PRIMARY, tag=""):
    tg = _tag(model, tag)
    for s in sets:
        if s == "stress":
            stress_evaluate(tg)
            continue
        sm = summarise(evaluate_set(s, tg))
        sm.to_csv(OUT / f"summary_{s}{tg}.csv", index=False)
        print(sm.to_string(index=False), flush=True)


# ---------------------------------------------------------------- perturbation set (S7; kinds and rule as v3)
def stress_step(_sets=None):
    p = OUT / "records" / "stress.jsonl"
    if p.exists():
        print(f"{p} exists; perturbation set is fixed, not redone", flush=True)
        return
    ev = list(load_set("eval").values())
    rng = np.random.default_rng(STRESS_SEED)
    used, recs, logs = set(), [], []
    for kind in R3.KINDS:
        pool = [r for r in ev if R3._eligible(kind, r) and r["record_id"] not in used]
        for i in sorted(rng.choice(len(pool), R3.N_PER_KIND, replace=False)):
            r = pool[i]
            used.add(r["record_id"])
            x, log = R3.perturb_one(kind, r)
            recs.append(x)
            logs.append(log)
    with open(p, "w") as f:
        f.writelines(json.dumps(r) + "\n" for r in recs)
    pd.DataFrame(logs).to_csv(OUT / "stress_log.csv", index=False)
    print(f"stress: {len(recs)} perturbed records (seed {STRESS_SEED})", flush=True)


def stress_evaluate(tg=""):
    from prism.report import checker
    recs, outs, orig = load_set("stress"), load_outputs("stress", tg), load_set("eval")
    assert outs, f"no outputs for stress{tg}"
    logs = pd.read_csv(OUT / "stress_log.csv").set_index("perturbed_id")
    rows = []
    for rid, rec in recs.items():
        lg = logs.loc[rid].to_dict()
        F, F_old = _facts(rec), _facts(orig[lg["record_id"]])
        o = outs.get(f"stress|{rid}")
        claims = checker.parse_structured(o["text"]) if o else None
        r = checker.check(claims, F, card=True)
        fol = R3.follows(lg["kind"], lg, F_old, F, claims, r) if r["parsed"] else False
        rows.append({"perturbed_id": rid, "cohort": rec["cohort"], "kind": lg["kind"], "old": lg["old"],
                     "new": lg["new"], "follows": fol, "check_pass": r["pass"], "follows_and_pass": fol and r["pass"]})
    df = pd.DataFrame(rows)
    df.to_csv(OUT / f"stress{tg}.csv", index=False)
    sm = df.groupby("kind")[["follows", "check_pass", "follows_and_pass"]].sum().reset_index()
    sm.loc[len(sm)] = ["total", df.follows.sum(), df.check_pass.sum(), df.follows_and_pass.sum()]
    sm["n"] = list(df.groupby("kind").size()) + [len(df)]
    sm["S7_met"] = sm.follows / sm.n >= 0.90
    sm.to_csv(OUT / f"summary_stress{tg}.csv", index=False)
    print(sm.to_string(index=False), flush=True)


# ---------------------------------------------------------------- rendering (no RANO: figure title and limitations)
def figure_v3_1(rec: dict):
    """The segmentation figure re-rendered with the v3.1 title (no RANO) into report_v3_1/figures; the v3 figures
    in system/figures are left as they are. None if the scan has no v3 figure (no images)."""
    if R3.figure_path(rec) is None:
        return None
    from prism.report import seg_figure
    p = OUT / "figures" / rec["cohort"] / f"{rec['scan_id']}.png"
    if not p.exists():
        seg_figure.render(rec["cohort"], rec["scan_id"], p, title=seg_figure.TITLE_V3_1)
    return p


def render_set(s: str, ids=None, tg="", html_too=False):
    from prism.report import prompts_v3_1 as P, sections_v3
    recs, outs = load_set(s), load_outputs(s, tg)
    d = OUT / "reports" / f"{s}{tg}"
    d.mkdir(parents=True, exist_ok=True)
    for rid, rec in recs.items():
        if ids is not None and rid not in ids:
            continue
        F = _facts(rec)
        o = outs.get(f"{s}|{rid}")
        prose = P.sectioned(o["text"]) if o else None
        fig = figure_v3_1(rec) if html_too else None
        name = rid.replace("|", "__")
        (d / f"{name}.md").write_text(sections_v3.render_md(rec["scan_id"], F, prose, str(fig) if fig else None))
        if html_too:
            (d / f"{name}.html").write_text(sections_v3.render_html(rec["scan_id"], F, prose, fig))


def render_step(sets, model=PRIMARY, tag=""):
    for s in sets:
        render_set(s, tg=_tag(model, tag))
        print(f"rendered {s}{_tag(model, tag)}", flush=True)


def examples_step(_sets=None, model=PRIMARY, tag=""):
    """Per cohort, the first evaluation record id (sort order) that has a segmentation figure (rule as v3)."""
    recs = load_set("eval")
    pick = []
    for coh in ("mu", "lumiere", "ucsf"):
        ids = sorted(k for k, r in recs.items() if r["cohort"] == coh and R3.figure_path(r) is not None)
        pick += ids[:1]
    render_set("eval", ids=set(pick), tg=_tag(model, tag), html_too=True)
    (OUT / "examples.json").write_text(json.dumps(pick, indent=1))
    print("examples:", len(pick), flush=True)


# ---------------------------------------------------------------- model ladder (plan section 4)
def _serving(path: Path) -> dict:
    meta = json.loads(Path(str(path) + ".meta.json").read_text()) if Path(str(path) + ".meta.json").exists() else {}
    log = path.with_suffix(".log").read_text() if path.with_suffix(".log").exists() else ""
    m = re.search(r"Model loading took ([\d.]+) GiB", log)
    g = path.with_suffix(".gpumem")
    peak = max((int(x) for x in g.read_text().split() if x.isdigit()), default=None) if g.exists() else None
    return {"batch_s_per_request": meta.get("batch_s_per_request"), "n_requests": meta.get("n"),
            "weights_gib": float(m.group(1)) if m else None, "gpu_peak_mib": peak}


def ladder_step(_sets=None, model=None, tag=""):
    rows = []
    for key, (mid, rev, ck, _) in MODELS.items():
        tg = _tag(key, tag)
        p = OUT / f"summary_eval{tg}.csv"
        if not p.exists():
            rows.append({"model": key, "hf_id": mid, "revision": rev, "status": "not run"})
            continue
        sm = pd.read_csv(p).set_index("cohort")
        st = pd.read_csv(OUT / f"summary_stress{tg}.csv").set_index("kind").loc["total"]
        sv = _serving(OUT / "llm" / f"outputs_eval{tg}.jsonl")
        row = {"model": key, "hf_id": mid, "revision": rev, "status": "run"}
        for coh in ("mu", "lumiere", "ucsf", "all"):
            row.update({f"S5_{coh}": f"{int(sm.loc[coh, 'pass'])}/{int(sm.loc[coh, 'n'])}",
                        f"S5_{coh}_rate": sm.loc[coh, "pass_rate"], f"S5_{coh}_ci_low": sm.loc[coh, "pass_ci_low"],
                        f"S5_{coh}_ci_high": sm.loc[coh, "pass_ci_high"], f"S5_{coh}_met": bool(sm.loc[coh, "S5_met"])})
        row["S6"] = f"{int(sm.loc['all', 'tier_stated'])}/{int(sm.loc['all', 'tier_required'])}"
        row["S7_follows"] = f"{int(st.follows)}/{int(st.n)}"
        row.update({f"fail_{c}": int(sm.loc["all", f"fail_{c}"]) for c in CATEGORIES})
        row.update(sv)
        row["S5_all_cohorts_met"] = all(row[f"S5_{c}_met"] for c in ("mu", "lumiere", "ucsf"))
        rows.append(row)
    df = pd.DataFrame(rows)
    df.to_csv(OUT / f"ladder{tag}.csv", index=False)
    print(df.to_string(index=False), flush=True)


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", nargs="+", required=True)
    ap.add_argument("--sets", nargs="+", default=["dev"])
    ap.add_argument("--model", default=PRIMARY, choices=list(MODELS))
    ap.add_argument("--tag", default="", help="suffix for development iterations, e.g. _iter1")
    a = ap.parse_args(argv)
    for s in a.steps:
        fn = globals()[f"{s}_step"]
        if s in ("generate", "evaluate", "render", "examples"):
            fn(a.sets, model=a.model, tag=a.tag)
        elif s == "ladder":
            fn(tag=a.tag)
        else:
            fn(a.sets)


if __name__ == "__main__":
    main()
