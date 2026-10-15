"""Clinician report generator written only from the per-scan audit record, and its faithfulness evaluation.

ANALYSIS PLAN: docs/results/REPORT_AGENT.md, section "Plan" (snapshot written before any evaluated report was generated:
outputs/results/analyses/report_agent/PLAN_snapshot.md). Summary:
  records   audit records (prism.audit.record.build) for every grade-4 out-of-fold scan of CV repeat 0 (249), plus risk
            tier cut points and indicative volumes; development set = non-grade-4 all-glioma scans (prompt work only)
  requests  arms A grounded (facts JSON + field citations, PRISM v2), B original PRISM prompt on the same record,
            C grounded with a smaller model; 30 perturbed records (stress test)
  generate  local vLLM in the separate LLM env (greedy, seed 0); no external API
  evaluate  deterministic checker (prism.report.checker): primary = share of arm-A reports with zero unsupported claims
            and every active flag mentioned (Wilson 95% CI, target >= 0.95); secondary rates, A vs B paired
            patient-cluster bootstrap, stress test, runtime
  render    full reports (markdown) and the Fig 5A example page / architecture diagram

    python -m prism report [--steps records requests generate evaluate render] [--sets dev|eval|stress]
    -> $PRISM_OUTPUTS/results/analyses/report_agent/
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time

import numpy as np
import pandas as pd

from prism.config import REPO, RESULTS
from prism.report import checker, prompts
from prism.report.facts import facts, tier_of

OUT = RESULTS / "analyses" / "report_agent"
LLM_ENV = os.environ.get("PRISM_LLM_ENV", "/project/community/sbandred/envs/prism-llm")
MODELS = {"large": ("Qwen/Qwen3.8-27B", "1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0", 4),
          "small": ("Qwen/Qwen3.5-9B", "c202236235762e1c871ad0ccb60c8ee5ba337b9a", 1)}
ARMS = {"A": ("large", "grounded"), "B": ("large", "original"), "C": ("small", "grounded")}
MAX_TOKENS = {"grounded": 1024, "original": 500}
N_STRESS, N_BOOT = 30, 2000


# ---------------------------------------------------------------- records
def records_step():
    from prism.report.records import build_records
    for name, pop, keep in (("eval", "grade4", None), ("dev", "all_glioma", "non_grade4")):
        scans = None
        if keep:
            from prism.data.mu import load_cohort
            c = load_cohort("all_glioma")
            scans = set(c.scan_id[~c.grade4.astype(bool)])
        recs, outc = build_records(pop, 0, scans)
        d = OUT / "records" / name
        d.mkdir(parents=True, exist_ok=True)
        for r in recs:
            (d / f"{r['scan_id']}.json").write_text(json.dumps(r, indent=1, default=float))
        outc.to_csv(OUT / f"outcomes_{name}_EVALUATION_ONLY.csv", index=False)
        print(f"{name}: {len(recs)} records (max |risk - audit cv| = {outc.max_abs_dev_vs_audit_cv.iloc[0]:.1e})")


def load_records(name):
    d = OUT / "records" / name
    return {p.stem: json.loads(p.read_text()) for p in sorted(d.glob("*.json"))}


# ---------------------------------------------------------------- stress test
def perturb(recs: dict, n=N_STRESS, seed=0) -> tuple[dict, pd.DataFrame]:
    """10 risk changes (to another tier), 10 flags switched on, 10 switched off (OOD / uncertain only)."""
    rng = np.random.default_rng(seed)
    ids = sorted(recs)
    out, log = {}, []
    has = lambda r, f: any(x["flag"] == f for x in r["referral"]["flags"])
    pools = {"risk": ids,
             "flag_on": [s for s in ids if not (has(recs[s], "uncertain") and has(recs[s], "out_of_distribution"))],
             "flag_off": [s for s in ids if has(recs[s], "uncertain") or has(recs[s], "out_of_distribution")]}
    for kind in ("risk", "flag_on", "flag_off"):
        for sid in rng.choice(pools[kind], n // 3, replace=False):
            r = json.loads(json.dumps(recs[sid]))
            pr, cuts = r["prediction"], r["risk_tier"]["cuts"]
            p0 = pr["risk_progression_within_120d"]
            if kind == "risk":
                t0 = tier_of(p0, cuts)
                targets = {"lower third": cuts[0] / 2, "middle third": (cuts[0] + cuts[1]) / 2,
                           "upper third": (cuts[1] + 1) / 2}
                new = targets[rng.choice([t for t in targets if t != t0])]
                lg = lambda p: np.log(p / (1 - p))
                sh = lg(new) - lg(p0)
                pr["interval_95"] = [float(1 / (1 + np.exp(-(lg(x) + sh)))) for x in pr["interval_95"]]
                pr["risk_progression_within_120d"] = float(new)
                detail = f"risk {p0:.2f} -> {new:.2f}"
            else:
                cand = [f for f in ("uncertain", "out_of_distribution") if has(r, f) == (kind == "flag_off")]
                f = str(rng.choice(cand))
                if kind == "flag_on":
                    reason = ("the alpha = 0.2 conformal prediction set contains both classes" if f == "uncertain" else
                              "rt_dose_gy = 80 outside training 1-99% [40, 60]")
                    r["referral"]["flags"].append({"flag": f, "reason": reason})
                    if f == "uncertain":
                        pr["conformal_sets"]["0.2"] = "{0, 1}"
                else:
                    r["referral"]["flags"] = [x for x in r["referral"]["flags"] if x["flag"] != f]
                    if f == "uncertain":
                        pr["conformal_sets"]["0.2"] = "{1}" if p0 >= 0.5 else "{0}"
                r["referral"]["refer"] = bool(r["referral"]["flags"])
                detail = f
            key = f"{sid}~{kind}"
            out[key] = r
            log.append({"id": key, "scan_id": sid, "kind": kind, "detail": detail, "orig_risk": round(p0, 2),
                        "orig_risk_percent": int(round(100 * p0))})
    return out, pd.DataFrame(log)


# ---------------------------------------------------------------- requests / generation
def requests_step(sets):
    for s in sets:
        recs = load_records("eval" if s == "stress" else s)
        if s == "stress":
            recs, log = perturb(recs)
            log.to_csv(OUT / "stress_log.csv", index=False)
            (OUT / "records" / "stress").mkdir(parents=True, exist_ok=True)
            for k, r in recs.items():
                (OUT / "records" / "stress" / f"{k}.json").write_text(json.dumps(r, indent=1, default=float))
        for model in MODELS:
            rows = []
            for arm, (m, kind) in ARMS.items():
                if m != model:
                    continue
                for sid, r in recs.items():
                    F = facts(r)
                    msgs = prompts.grounded(F) if kind == "grounded" else prompts.original(F, r["scan_id"])[0]
                    rows.append({"id": f"{s}|{arm}|{sid}", "messages": msgs, "json_schema": kind == "grounded",
                                 "max_tokens": MAX_TOKENS[kind]})
            (OUT / "llm").mkdir(parents=True, exist_ok=True)
            with open(OUT / "llm" / f"requests_{s}_{model}.jsonl", "w") as f:
                for row in rows:
                    f.write(json.dumps(row) + "\n")
            print(f"{s}/{model}: {len(rows)} requests")


def generate_step(sets, latency=10):
    for s in sets:
        for model, (mid, rev, tp) in MODELS.items():
            req = OUT / "llm" / f"requests_{s}_{model}.jsonl"
            cmd = [f"{LLM_ENV}/bin/python", "-m", "prism.report.llm", "--model", mid, "--revision", rev, "--requests",
                   str(req), "--out", str(OUT / "llm" / f"outputs_{s}_{model}.jsonl"), "--tp", str(tp),
                   "--latency", str(latency if s == "eval" else 0)]
            env = {**os.environ, "PYTHONPATH": str(REPO), "PATH": f"{LLM_ENV}/bin:{os.environ['PATH']}", "HF_HUB_OFFLINE": "1", "VLLM_NO_USAGE_STATS": "1",
                   "DO_NOT_TRACK": "1", "CUDA_VISIBLE_DEVICES": os.environ.get("REPORT_GPUS", "0,1,2,3")[: 2 * tp - 1]}
            print(" ".join(cmd), flush=True)
            t = time.time()
            subprocess.run(cmd, env=env, check=True, cwd=REPO)
            print(f"{s}/{model} done in {time.time() - t:.0f}s", flush=True)


def load_outputs(s):
    out = {}
    for model in MODELS:
        p = OUT / "llm" / f"outputs_{s}_{model}.jsonl"
        if p.exists():
            out.update({r["id"]: r for r in map(json.loads, open(p))})
    return out


# ---------------------------------------------------------------- evaluation
def wilson(k, n, z=1.959964):
    if n == 0:
        return (np.nan, np.nan)
    p = k / n
    c = (p + z * z / (2 * n)) / (1 + z * z / n)
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return (c - h, c + h)


def claims_of(arm, text):
    if ARMS[arm][1] == "grounded":
        return checker.parse_structured(text)
    return [{"text": t, "fields": []} for t in checker.split_sentences(text)]


def check_set(s):
    recs = load_records(s)
    outs = load_outputs(s)
    rows, details = [], {}
    for key, o in outs.items():
        _, arm, sid = key.split("|")
        r = recs[sid]
        F = facts(r)
        cl = claims_of(arm, o["text"])
        if ARMS[arm][1] == "grounded":
            c = checker.check(cl, F)
        else:
            c = checker.check(cl, F, cited=False, context={"prompt": prompts.original(F, r["scan_id"])[1]["_prompt_text"]})
            c["pass_vs_record"] = c["parsed"] and c["n_unsupported_vs_record"] == 0 and c["all_flags_mentioned"]
        kw = checker.flag_mentions(cl or [], F, require_citation=False)
        act = c.get("active_flags", [])
        rows.append({"set": s, "arm": arm, "scan_id": sid, "patient_id": r["patient_id"], "phase": r["phase_of_care"],
                     "pass": c["pass"], "parsed": c["parsed"], "n_claims": c["n_claims"],
                     "n_unsupported": c["n_unsupported"], "n_unsupported_vs_record": c.get("n_unsupported_vs_record"),
                     "n_invalid_citations": c.get("n_invalid_citations"), "n_active_flags": len(act),
                     "n_flags_omitted": len(c.get("flags_omitted", act)),
                     "n_flags_omitted_keyword": sum(not kw[n]["mentioned"] for n in act),
                     "flags_spurious": "|".join(c.get("flags_spurious", [])),
                     "all_flags_mentioned": c["all_flags_mentioned"], "any_forbidden": c.get("any_forbidden"),
                     **{f"forbidden_{k}": "|".join(v) for k, v in c.get("forbidden", {}).items()},
                     "tier_stated": c.get("tier_stated"), "tier_inconsistent": c.get("tier_inconsistent"),
                     "pass_vs_record": c.get("pass_vs_record", c["pass"]),
                     "finish_reason": o["finish_reason"], "n_output_tokens": o["n_output_tokens"],
                     "latency_s": o.get("latency_s")})
        details[key] = {"claims": cl, "check": c}
    return pd.DataFrame(rows), details


def paired_boot(df, a, b, col, n=N_BOOT, seed=0):
    x = df[df.arm == a].set_index("scan_id")[col].astype(float)
    y = df[df.arm == b].set_index("scan_id")[col].astype(float).loc[x.index]
    pid = df[df.arm == a].set_index("scan_id").patient_id.loc[x.index].to_numpy()
    d = (x - y).to_numpy()
    u, inv = np.unique(pid, return_inverse=True)
    S = np.bincount(inv, d)
    N = np.bincount(inv)
    rng = np.random.default_rng(seed)
    bs = []
    for _ in range(n):
        w = np.bincount(rng.integers(0, len(u), len(u)), minlength=len(u))
        bs.append((w * S).sum() / (w * N).sum())
    return d.mean(), np.percentile(bs, 2.5), np.percentile(bs, 97.5)


def summarise(df):
    rows = []
    for arm, g in df.groupby("arm"):
        k, n = int(g["pass"].sum()), len(g)
        lo, hi = wilson(k, n)
        act = g.n_active_flags.sum()
        rows.append({"arm": arm, "model": MODELS[ARMS[arm][0]][0], "prompt": ARMS[arm][1], "n_reports": n,
                     "pass": k, "pass_rate": k / n, "pass_lo": lo, "pass_hi": hi,
                     "pass_vs_record": int(g.pass_vs_record.sum()), "parsed": int(g.parsed.sum()),
                     "unsupported_per_report": g.n_unsupported.mean(),
                     "reports_with_unsupported": int((g.n_unsupported > 0).sum()),
                     "unsupported_vs_record_per_report": g.n_unsupported_vs_record.mean(),
                     "reports_with_unsupported_vs_record": int((g.n_unsupported_vs_record > 0).sum()),
                     "claims_per_report": g.n_claims.mean(), "active_flags": int(act),
                     "flag_omission_rate": g.n_flags_omitted.sum() / max(act, 1),
                     "flag_omission_rate_keyword": g.n_flags_omitted_keyword.sum() / max(act, 1),
                     "reports_with_flag_omitted": int((g.n_flags_omitted > 0).sum()),
                     "reports_with_spurious_flag": int((g.flags_spurious != "").sum()),
                     "forbidden_rate": g.any_forbidden.mean(),
                     **{f"forbidden_{c}_rate": (g[f"forbidden_{c}"] != "").mean() for c in checker.FORBIDDEN},
                     "tier_stated_rate": g.tier_stated.mean(), "tier_inconsistent_rate": g.tier_inconsistent.mean(),
                     "truncated": int((g.finish_reason == "length").sum()),
                     "output_tokens_mean": g.n_output_tokens.mean(),
                     "single_latency_s_median": g.latency_s.median()})
    return pd.DataFrame(rows)


def stress_eval(df_stress):
    log = pd.read_csv(OUT / "stress_log.csv").set_index("id")
    recs = load_records("stress")
    outs = load_outputs("stress")
    rows = []
    for key, o in outs.items():
        _, arm, sid = key.split("|")
        F = facts(recs[sid])
        L = log.loc[sid]
        row = df_stress[(df_stress.arm == arm) & (df_stress.scan_id == sid)].iloc[0]
        cl = claims_of(arm, o["text"]) or []
        text = " ".join(c["text"] for c in cl)
        nums = set(checker.numbers(text))
        if L.kind == "risk":
            new_ok = f"{F['risk.value']:.2f}" in nums or str(F["risk.percent"]) in nums
            old_present = (f"{L.orig_risk:.2f}" in nums or str(L.orig_risk_percent) in nums) and \
                abs(L.orig_risk - F["risk.value"]) > 0.005
            follows = new_ok and not old_present and not row.tier_inconsistent
        elif L.kind == "flag_on":
            follows = L.detail not in str(row.flags_spurious) and checker.flag_mentions(
                cl, F, require_citation=ARMS[arm][1] == "grounded")[L.detail]["mentioned"]
        else:
            fm = checker.flag_mentions(cl, F, require_citation=False)[L.detail]
            follows = not fm["spurious"] and not (L.detail == "uncertain" and "both outcomes" in text.lower())
        rows.append({"arm": arm, "id": sid, "kind": L.kind, "detail": L.detail, "follows_record": bool(follows),
                     "passes_checks": bool(row["pass"]), "stress_pass": bool(follows and row["pass"]), "text": text})
    return pd.DataFrame(rows)


def evaluate_step(sets):
    for s in sets:
        df, det = check_set(s)
        df.to_csv(OUT / f"checks_{s}.csv", index=False)
        (OUT / f"check_details_{s}.json").write_text(json.dumps(det, indent=1, default=str))
        sm = summarise(df)
        if s == "eval":
            for arm in ("B", "C"):
                if arm in set(df.arm):
                    for col, name in (("pass", "pass"), ("n_unsupported", "unsupported_per_report"),
                                      ("n_flags_omitted_keyword", "flags_omitted_keyword_per_report"),
                                      ("any_forbidden", "forbidden"), ("pass_vs_record", "pass_vs_record")):
                        d, lo, hi = paired_boot(df, "A", arm, col)
                        sm.loc[sm.arm == arm, f"A_minus_{arm}_{name}"] = d
                        sm.loc[sm.arm == arm, f"A_minus_{arm}_{name}_lo"] = lo
                        sm.loc[sm.arm == arm, f"A_minus_{arm}_{name}_hi"] = hi
            meta = {m: json.load(open(OUT / "llm" / f"outputs_{s}_{m}.jsonl.meta.json")) for m in MODELS
                    if (OUT / "llm" / f"outputs_{s}_{m}.jsonl.meta.json").exists()}
            for arm, (m, _) in ARMS.items():
                if m in meta:
                    sm.loc[sm.arm == arm, "batch_s_per_report_model"] = meta[m]["batch_s_per_report"]
            sm["primary_target_met"] = (sm.arm == "A") & (sm.pass_rate >= 0.95)
            by_phase = df.groupby(["arm", "phase"]).agg(n=("pass", "size"), pass_rate=("pass", "mean"),
                                                        forbidden_rate=("any_forbidden", "mean"),
                                                        flags_omitted=("n_flags_omitted", "sum")).reset_index()
            by_phase.to_csv(OUT / "by_phase.csv", index=False)
        if s == "stress":
            st = stress_eval(df)
            st.to_csv(OUT / "stress.csv", index=False)
            print(st.groupby(["arm", "kind"]).stress_pass.agg(["sum", "size"]))
        sm.to_csv(OUT / f"summary_{s}.csv", index=False)
        print(sm.T.to_string())


# ---------------------------------------------------------------- render
def render_step(sets):
    from prism.report import sections
    for s in sets:
        recs, outs = load_records(s), load_outputs(s)
        for key, o in outs.items():
            _, arm, sid = key.split("|")
            F = facts(recs[sid])
            cl = claims_of(arm, o["text"])
            summ = [c["text"] for c in cl] if cl else [o["text"]]
            d = OUT / "reports" / s / arm
            d.mkdir(parents=True, exist_ok=True)
            (d / f"{sid}.md").write_text(sections.render(recs[sid], F, summ))


EXAMPLE_PHASES = ("pre_rt", "early_post_rt", "later_post_rt")
FIG = REPO / "docs" / "manuscript" / "figures"


def examples():
    """Pre-specified: first scan id (sort order) per phase among the evaluation records."""
    recs = load_records("eval")
    return {ph: min(s for s, r in recs.items() if r["phase_of_care"] == ph) for ph in EXAMPLE_PHASES}


def figures_step(figure_phase="early_post_rt"):
    import shutil
    from prism.report.figures import architecture, example_report
    FIG.mkdir(parents=True, exist_ok=True)
    architecture(FIG / "fig5a_architecture")
    recs, outs = load_records("eval"), load_outputs("eval")
    det = json.loads((OUT / "check_details_eval.json").read_text())
    ex = examples()
    (OUT / "examples.json").write_text(json.dumps(ex, indent=1))
    sid = ex[figure_phase]
    key = f"eval|A|{sid}"
    cl = claims_of("A", outs[key]["text"])
    example_report(recs[sid], facts(recs[sid]), [c["text"] for c in cl], OUT / "example_report", det[key]["check"])
    for ext in ("pdf", "png"):
        shutil.copy(OUT / f"example_report.{ext}", FIG / f"fig5a_example_report.{ext}")
    print("examples:", ex, "figure:", sid)


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="prism report", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--steps", nargs="+", default=["records", "requests", "generate", "evaluate", "render"])
    ap.add_argument("--sets", nargs="+", default=["eval", "stress"])
    a = ap.parse_args(argv)
    OUT.mkdir(parents=True, exist_ok=True)
    for st in a.steps:
        print(f"== report {st}", flush=True)
        {"records": lambda: records_step(), "requests": lambda: requests_step(a.sets),
         "generate": lambda: generate_step(a.sets), "evaluate": lambda: evaluate_step(a.sets),
         "render": lambda: render_step(a.sets), "figures": figures_step}[st]()


if __name__ == "__main__":
    main()
