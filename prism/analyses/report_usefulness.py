"""Report generator v2: public-report style reference, horizon-citation fix, and usefulness next to the probability.

ANALYSIS PLAN: docs/results/REPORT_USEFULNESS.md, section "Analysis plan (pre-specified)" (snapshot saved before any
evaluation-set report is generated: outputs/results/analyses/report_usefulness/PLAN_snapshot.md). Summary:
  reference  public brain-MRI report corpora (data/public_reports/: RadGenome-Brain MRI BraTS-GLI findings +
             impressions, MIT; MultiCaRe glioma post-treatment case-report MRI sentences, CC BY family) -> section
             structure, length, reading level (FKGL), hedging and post-treatment vocabulary (prism.report.style)
  records    report records (prism.report.records.build_records, unchanged) + a context_v2 block (training-scan average
             risk of the fold model, the same patient's prior-scan out-of-fold risk):
               dev     59 non-grade-4 all-glioma scans, CV repeat 0     (tuning only, as in report_agent)
               eval    249 grade-4 scans, CV repeat 1                   (fresh records, never used for tuning)
               stress  30 perturbed eval records (report_agent.perturb, seed 0)
             LUMIERE is not used: the core model needs treatment / RT-date fields that LUMIERE lacks (AUDIT_SYSTEM.md
             (d)); a LUMIERE record would come from a different model.
  requests   arm v1 = prompts.grounded on facts() (unchanged), arm v2 = prompts_v2.grounded_v2 on facts_v2()
  generate   Qwen3.8-27B (same pinned revision as report_agent), 1 GPU (GPU 0), greedy, seed 0 (prism.report.vllm_run)
  evaluate   same checker (prism.report.checker) on v2 facts + usefulness items U1-U8, safety S1-S2, readability
             (prism.report.usefulness); primary and decision rules in the plan; paired v2 - v1 patient-cluster bootstrap
  judge      EXPLORATORY LLM-as-judge (Gemma 4 31B-it, different family, blinded to arm; prism.report.judge)
  figure     v2 example page for the pre-specified early post-RT scan (docs/manuscript/figures/fig6a_*)

    python -m prism reportuse [--steps reference records requests generate evaluate judge render] [--sets dev|eval|stress]
    -> $PRISM_OUTPUTS/results/analyses/report_usefulness/
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import time

import numpy as np
import pandas as pd

from prism.config import DATA, REPO, RESULTS
from prism.report import checker, judge, prompts, prompts_v2, style, usefulness
from prism.report.facts import facts
from prism.report.facts_v2 import facts_v2

OUT = RESULTS / "analyses" / "report_usefulness"
PUBLIC = DATA / "public_reports"
LLM_ENV = os.environ.get("PRISM_LLM_ENV", "/project/community/sbandred/envs/prism-llm")
WRITER = ("Qwen/Qwen3.8-27B", "1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0", {"enable_thinking": False})
JUDGE = ("google/gemma-4-31B-it", "842da3794eaa0b77d5f08bae87a17459d91ff475", {"enable_thinking": False})
GPU = os.environ.get("REPORTUSE_GPU", "0")
SETS = {"dev": ("all_glioma", 0, "non_grade4"), "eval": ("grade4", 1, None)}
ARMS = ("v1", "v2")
MAX_TOKENS = {"v1": 1024, "v2": 1536}
PRIMARY_PASS, PRIMARY_COMPLETE, MAX_FORBIDDEN, MAX_SAFETY = 0.95, 0.90, 0.02, 0.01
N_BOOT = 2000


# ---------------------------------------------------------------- reference corpora (public, no patient data)
def load_reference() -> dict[str, list[str]]:
    """Public report texts: RadGenome-Brain MRI BraTS-GLI (findings + impression; impression only) and MultiCaRe
    glioma post-treatment case reports (MRI sentences only)."""
    rg = PUBLIC / "radgenome_brain_mri" / "BraTS_GLI"
    g, i = json.loads((rg / "global_finding.json").read_text()), json.loads((rg / "impression.json").read_text())
    full = [f"Findings: {g[k]}\nImpression: {i[k]['impression']}" for k in sorted(g)]
    imp = [i[k]["impression"] for k in sorted(g)]
    c = pd.read_parquet(PUBLIC / "multicare" / "cases.parquet").explode("cases")
    c = pd.concat([c[["article_id"]].reset_index(drop=True), pd.json_normalize(c.cases.tolist())], axis=1)
    sel = c.case_text.str.contains(r"glioblastoma|high-grade glioma|GBM\b", case=False) & c.case_text.str.contains(
        r"pseudoprogression|chemoradiation|chemoradiotherapy|temozolomide|radiation necrosis|radiotherapy", case=False)
    im = r"\b(MRI|MR imaging|magnetic resonance|enhanc\w*|FLAIR|T2|T1|imaging|scan)\b"
    mc = [" ".join(s for s in style.sentences(t) if re.search(im, s)) for t in c.case_text[sel]]
    return {"radgenome_gli_report": full, "radgenome_gli_impression": imp, "multicare_glioma_post_tx": [t for t in mc if t]}


def reference_step():
    OUT.mkdir(parents=True, exist_ok=True)
    ref = load_reference()
    prof = {k: style.profile(v) for k, v in ref.items()}
    big = pd.DataFrame([{"corpus": k, "bigram": b, "count": n} for k, v in ref.items() for b, n in style.top_bigrams(v)])
    big.to_csv(OUT / "reference_bigrams.csv", index=False)
    heads = pd.Series({k: len(re.findall(style.SECTION_HEADS, "\n".join(v))) for k, v in ref.items()})
    (OUT / "reference_profile.json").write_text(json.dumps({"profiles": prof, "section_heads": heads.to_dict()}, indent=1))
    rows = []
    for k, p in prof.items():
        rows.append({"corpus": k, "n": p["n"], **{f"{m}_{q}": p[m][q] for m in ("words", "sentences", "words_per_sentence",
                                                                             "fkgl", "reading_time_s")
                                                  for q in ("median", "q1", "q3")},
                     **{f"hedge:{h}": v for h, v in p["hedge_sentence_share"].items()},
                     **{f"post_tx:{h}": v for h, v in p["post_treatment_sentence_share"].items()}})
    pd.DataFrame(rows).to_csv(OUT / "reference_summary.csv", index=False)
    print(pd.DataFrame(rows).set_index("corpus").T.to_string())


# ---------------------------------------------------------------- records with the v2 context block
def context_blocks(pop: str, repeat: int) -> dict:
    """Per scan: average risk of its fold model over that model's training scans (no labels used) and the prior scan
    of the same patient (out-of-fold risk of the same repeat; same fold because folds are patient-grouped)."""
    from prism.audit.model import design, fit_pipeline
    from prism.data.mu import load_cohort
    from prism.experiments import c3_radiomics as c3
    from prism.models.folds import load_folds
    cohort = load_cohort(pop)
    X, groups = design(cohort)
    f = c3._fold_ids(cohort, load_folds(), repeat)
    cv = pd.read_csv(RESULTS / "analyses" / "audit_system" / f"cv_predictions_{pop}.csv.gz")
    risk = cv[cv.repeat == repeat].set_index("scan_id").risk
    ref = {}
    for k in sorted(np.unique(f)):
        tr = np.where(f != k)[0]
        m = fit_pipeline(X, cohort, tr, groups, seed=repeat)
        ref[k] = float(m.predict(X.iloc[tr]).mean())
    d = cohort[["scan_id", "patient_id", "days_from_diagnosis_to_mri"]].assign(fold=f)
    d = d.sort_values(["patient_id", "days_from_diagnosis_to_mri", "scan_id"])
    out = {}
    for _, g in d.groupby("patient_id"):
        prev = None
        for r in g.itertuples():
            out[r.scan_id] = {"reference_mean": ref[r.fold], "reference_method": "mean predicted risk of the fold model "
                              "on its own training scans", "prior": None if prev is None else {
                                  "scan_id": prev.scan_id, "risk": float(risk[prev.scan_id]),
                                  "days_before": float(r.days_from_diagnosis_to_mri - prev.days_from_diagnosis_to_mri)}}
            prev = r
    return out


def records_step(sets):
    from prism.data.mu import load_cohort
    from prism.report.records import build_records
    for s in [x for x in sets if x in SETS]:
        pop, rep, keep = SETS[s]
        scans = None
        if keep:
            c = load_cohort("all_glioma")
            scans = set(c.scan_id[~c.grade4.astype(bool)])
        recs, outc = build_records(pop, rep, scans)
        ctx = context_blocks(pop, rep)
        d = OUT / "records" / s
        d.mkdir(parents=True, exist_ok=True)
        for r in recs:
            r["context_v2"] = ctx[r["scan_id"]]
            (d / f"{r['scan_id']}.json").write_text(json.dumps(r, indent=1, default=float))
        outc.to_csv(OUT / f"outcomes_{s}_EVALUATION_ONLY.csv", index=False)
        print(f"{s}: {len(recs)} records ({pop}, repeat {rep}; max |risk - audit cv| = "
              f"{outc.max_abs_dev_vs_audit_cv.iloc[0]:.1e}); with prior scan: "
              f"{sum(r['context_v2']['prior'] is not None for r in recs)}")


def load_records(s):
    d = OUT / "records" / s
    return {p.stem: json.loads(p.read_text()) for p in sorted(d.glob("*.json"))}


# ---------------------------------------------------------------- requests / generation
def messages(arm, rec):
    return prompts.grounded(facts(rec)) if arm == "v1" else prompts_v2.grounded_v2(facts_v2(rec))


def requests_step(sets):
    from prism.analyses.report_agent import perturb
    for s in sets:
        if s == "stress":
            recs, log = perturb(load_records("eval"))
            log.to_csv(OUT / "stress_log.csv", index=False)
            (OUT / "records" / "stress").mkdir(parents=True, exist_ok=True)
            for k, r in recs.items():
                (OUT / "records" / "stress" / f"{k}.json").write_text(json.dumps(r, indent=1, default=float))
        else:
            recs = load_records(s)
        rows = [{"id": f"{s}|{arm}|{sid}", "messages": messages(arm, r), "max_tokens": MAX_TOKENS[arm],
                 "schema": prompts.SCHEMA if arm == "v1" else prompts_v2.SCHEMA_V2}
                for arm in ARMS for sid, r in recs.items()]
        (OUT / "llm").mkdir(parents=True, exist_ok=True)
        with open(OUT / "llm" / f"requests_{s}.jsonl", "w") as f:
            f.writelines(json.dumps(r) + "\n" for r in rows)
        print(f"{s}: {len(rows)} requests")


def run_vllm(model, req, out, max_len=8192, gpu_mem=0.90):
    mid, rev, ck = model
    cmd = [f"{LLM_ENV}/bin/python", "-m", "prism.report.vllm_run", "--model", mid, "--revision", rev, "--requests",
           str(req), "--out", str(out), "--tp", "1", "--chat-kwargs", json.dumps(ck), "--max-model-len", str(max_len), "--gpu-mem", str(gpu_mem)]
    env = {**os.environ, "PYTHONPATH": str(REPO), "PATH": f"{LLM_ENV}/bin:{os.environ['PATH']}", "HF_HUB_OFFLINE": "1",
           "VLLM_NO_USAGE_STATS": "1", "DO_NOT_TRACK": "1", "CUDA_VISIBLE_DEVICES": GPU}
    print(" ".join(cmd), flush=True)
    t = time.time()
    subprocess.run(cmd, env=env, check=True, cwd=REPO)
    print(f"{out.name} done in {time.time() - t:.0f}s", flush=True)


def generate_step(sets):
    for s in sets:
        run_vllm(WRITER, OUT / "llm" / f"requests_{s}.jsonl", OUT / "llm" / f"outputs_{s}.jsonl")


def load_outputs(s, kind="outputs"):
    p = OUT / "llm" / f"{kind}_{s}.jsonl"
    return {r["id"]: r for r in map(json.loads, open(p))} if p.exists() else {}


# ---------------------------------------------------------------- evaluation
def evaluate_set(s):
    recs, outs = load_records(s), load_outputs(s)
    rows, det = [], {}
    for key, o in outs.items():
        _, arm, sid = key.split("|")
        r = recs[sid]
        F = facts_v2(r)
        cl = checker.parse_structured(o["text"])
        c = checker.check(cl, F)
        u = usefulness.score(cl, F)
        sec = prompts_v2.sectioned(o["text"]) if arm == "v2" else None
        rows.append({"set": s, "arm": arm, "scan_id": sid, "patient_id": r["patient_id"], "phase": r["phase_of_care"],
                     "pass": c["pass"], "parsed": c["parsed"], "n_claims": c["n_claims"],
                     "n_unsupported": c["n_unsupported"], "n_invalid_citations": c.get("n_invalid_citations"),
                     "n_active_flags": len(c.get("active_flags", [])),
                     "n_flags_omitted": len(c.get("flags_omitted", [])), "flags_spurious": "|".join(c.get("flags_spurious", [])),
                     "any_forbidden": bool(c.get("any_forbidden")),
                     **{f"forbidden_{k}": "|".join(v) for k, v in c.get("forbidden", {}).items()},
                     "tier_stated": c.get("tier_stated"), "tier_inconsistent": c.get("tier_inconsistent"),
                     "has_impression": bool(sec and sec["impression"]), **u,
                     "finish_reason": o["finish_reason"], "n_output_tokens": o["n_output_tokens"]})
        det[key] = {"claims": cl, "check": c}
    return pd.DataFrame(rows), det


def wilson(k, n):
    from prism.analyses.report_agent import wilson as w
    return w(k, n)


def paired(df, col, a="v2", b="v1", n=N_BOOT, seed=0):
    from prism.analyses.report_agent import paired_boot
    return paired_boot(df.assign(**{col: df[col].astype(float)}), a, b, col, n=n, seed=seed)


def summarise(df):
    rows = []
    for arm, g in df.groupby("arm"):
        k, n = int(g["pass"].sum()), len(g)
        lo, hi = wilson(k, n)
        kc = int(g.complete.sum())
        clo, chi = wilson(kc, n)
        r = {"arm": arm, "n": n, "pass": k, "pass_rate": k / n, "pass_lo": lo, "pass_hi": hi,
             "complete": kc, "complete_rate": kc / n, "complete_lo": clo, "complete_hi": chi,
             "usefulness_mean": g.usefulness.mean(), "parsed": int(g.parsed.sum()),
             "unsupported_per_report": g.n_unsupported.mean(), "reports_with_unsupported": int((g.n_unsupported > 0).sum()),
             "invalid_citations": int(g.n_invalid_citations.sum()), "active_flags": int(g.n_active_flags.sum()),
             "flags_omitted": int(g.n_flags_omitted.sum()), "reports_with_spurious_flag": int((g.flags_spurious != "").sum()),
             "forbidden_rate": g.any_forbidden.mean(),
             **{f"forbidden_{c}_rate": (g[f"forbidden_{c}"] != "").mean() for c in checker.FORBIDDEN},
             "S1_false_reassurance": int(g.S1_false_reassurance.sum()), "S2_wording_mismatch": int(g.S2_wording_mismatch.sum()),
             "safety_rate": (g.S1_false_reassurance | g.S2_wording_mismatch).mean(),
             "tier_stated_rate": g.tier_stated.mean(), "has_impression_rate": g.has_impression.mean(),
             "truncated": int((g.finish_reason == "length").sum()), "output_tokens_mean": g.n_output_tokens.mean()}
        for it in usefulness.ITEMS:
            a = g[f"{it}_applicable"].astype(bool)
            r[f"{it}_n_applicable"] = int(a.sum())
            r[f"{it}_rate"] = g.loc[a, it].astype(float).mean() if a.any() else np.nan
        for m in ("words", "sentences", "words_per_sentence", "fkgl", "reading_time_s"):
            r[f"{m}_median"], r[f"{m}_q1"], r[f"{m}_q3"] = g[m].median(), g[m].quantile(.25), g[m].quantile(.75)
        rows.append(r)
    return pd.DataFrame(rows)


def decision(sm, df):
    """Pre-specified decision rules (plan): v2 replaces v1 only if all hold on the evaluation set."""
    v2 = sm.set_index("arm").loc["v2"]
    d, lo, hi = paired(df, "usefulness")
    rules = {"P1_pass_rate_ge_0.95": bool(v2.pass_rate >= PRIMARY_PASS),
             "P2a_complete_rate_ge_0.90": bool(v2.complete_rate >= PRIMARY_COMPLETE),
             "P2b_usefulness_v2_minus_v1_lo_gt_0": bool(lo > 0),
             "G1_forbidden_rate_le_0.02": bool(v2.forbidden_rate <= MAX_FORBIDDEN),
             "G2_safety_rate_le_0.01": bool(v2.safety_rate <= MAX_SAFETY),
             "G3_no_flag_omitted": bool(v2.flags_omitted == 0)}
    return {"rules": rules, "adopt_v2": all(rules.values()), "usefulness_diff": [d, lo, hi]}


def evaluate_step(sets):
    for s in sets:
        df, det = evaluate_set(s)
        df.to_csv(OUT / f"checks_{s}.csv", index=False)
        (OUT / f"check_details_{s}.json").write_text(json.dumps(det, indent=1, default=str))
        sm = summarise(df)
        if set(ARMS) <= set(df.arm):
            for col in ("pass", "complete", "usefulness", "any_forbidden", "S1_false_reassurance", "words", "fkgl"):
                d, lo, hi = paired(df, col)
                sm.loc[sm.arm == "v2", [f"v2_minus_v1_{col}", f"v2_minus_v1_{col}_lo", f"v2_minus_v1_{col}_hi"]] = [d, lo, hi]
        if s == "eval":
            dec = decision(sm, df)
            (OUT / "decision_eval.json").write_text(json.dumps(dec, indent=1, default=float))
            print(json.dumps(dec, indent=1, default=float))
            df.groupby(["arm", "phase"]).agg(n=("pass", "size"), pass_rate=("pass", "mean"),
                                             complete_rate=("complete", "mean"),
                                             usefulness=("usefulness", "mean")).reset_index().to_csv(OUT / "by_phase.csv", index=False)
        if s == "stress":
            stress_eval(df).to_csv(OUT / "stress.csv", index=False)
        sm.to_csv(OUT / f"summary_{s}.csv", index=False)
        print(sm.T.to_string())


def stress_eval(df):
    """Same rule as report_agent: the report passes the checks on the perturbed record and follows the change."""
    log = pd.read_csv(OUT / "stress_log.csv").set_index("id")
    recs, outs = load_records("stress"), load_outputs("stress")
    rows = []
    for key, o in outs.items():
        _, arm, sid = key.split("|")
        F, L = facts_v2(recs[sid]), log.loc[sid]
        row = df[(df.arm == arm) & (df.scan_id == sid)].iloc[0]
        cl = checker.parse_structured(o["text"]) or []
        text = " ".join(c["text"] for c in cl)
        nums = set(checker.numbers(text))
        if L.kind == "risk":
            new_ok = f"{F['risk.value']:.2f}" in nums or str(F["risk.percent"]) in nums
            old = (f"{L.orig_risk:.2f}" in nums or str(L.orig_risk_percent) in nums) and abs(L.orig_risk - F["risk.value"]) > 0.005
            follows = new_ok and not old and not row.tier_inconsistent
        elif L.kind == "flag_on":
            follows = checker.flag_mentions(cl, F)[L.detail]["mentioned"]
        else:
            fm = checker.flag_mentions(cl, F, require_citation=False)[L.detail]
            follows = not fm["spurious"] and not (L.detail == "uncertain" and "both outcomes" in text.lower())
        rows.append({"arm": arm, "id": sid, "kind": L.kind, "detail": L.detail, "follows_record": bool(follows),
                     "passes_checks": bool(row["pass"]), "stress_pass": bool(follows and row["pass"]), "text": text})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- EXPLORATORY: LLM-as-judge
def judge_requests(s, seed=0):
    recs, outs = load_records(s), load_outputs(s)
    rows = []
    rng = np.random.default_rng(seed)
    txt = {k: prompts_v2.render_text(o["text"], k.split("|")[1]) for k, o in outs.items()}
    for sid in sorted(recs):
        F = facts_v2(recs[sid])
        for arm in ARMS:
            rows.append({"id": f"abs|{s}|{arm}|{sid}", "messages": judge.absolute(F, txt[f"{s}|{arm}|{sid}"]),
                         "regex": judge.ABS_REGEX, "max_tokens": 800})
        a, b = txt[f"{s}|v1|{sid}"], txt[f"{s}|v2|{sid}"]
        for order in (("v1", "v2"), ("v2", "v1")):
            x, y = (a, b) if order == ("v1", "v2") else (b, a)
            rows.append({"id": f"pair|{s}|{order[0]}-{order[1]}|{sid}", "messages": judge.pairwise(F, x, y),
                         "schema": judge.PAIR_SCHEMA, "max_tokens": 400, "compact_json": True})
    rows = [rows[i] for i in rng.permutation(len(rows))]  # batch order does not follow arm
    with open(OUT / "llm" / f"judge_requests_{s}.jsonl", "w") as f:
        f.writelines(json.dumps(r) + "\n" for r in rows)
    return len(rows)


def judge_step(sets):
    for s in sets:
        print(f"{s}: {judge_requests(s)} judge requests")
        run_vllm(JUDGE, OUT / "llm" / f"judge_requests_{s}.jsonl", OUT / "llm" / f"judge_outputs_{s}.jsonl", 6144, 0.92)
        judge_summary(s)


def judge_summary(s):
    outs = load_outputs(s, "judge_outputs")
    ab, pr = [], {}
    for k, o in outs.items():
        kind, _, arm, sid = k.split("|")
        j = judge.parse_absolute(o["text"]) if kind == "abs" else judge.parse(o["text"])
        if kind == "abs":
            ab.append({"arm": arm, "scan_id": sid, "parsed": j is not None,
                       **({c: j[c]["score"] for c in judge.RUBRIC} if j else {})})
        else:
            first, second = arm.split("-")
            p = (j or {}).get("preferred")
            pr.setdefault(sid, {})[arm] = {"first": first, "second": second}.get(p, "tie" if p == "tie" else None)
    ab = pd.DataFrame(ab)
    ab.to_csv(OUT / f"judge_absolute_{s}.csv", index=False)
    pw = pd.DataFrame([{"scan_id": sid, "v1_first": v.get("v1-v2"), "v2_first": v.get("v2-v1"),
                        "consistent": v.get("v1-v2") == v.get("v2-v1"),
                        "preferred": v.get("v1-v2") if v.get("v1-v2") == v.get("v2-v1") else "inconsistent"}
                       for sid, v in pr.items()])
    pw.to_csv(OUT / f"judge_pairwise_{s}.csv", index=False)
    sm = ab.groupby("arm")[list(judge.RUBRIC)].agg(["mean", "median"])
    sm.to_csv(OUT / f"judge_summary_{s}.csv")
    print(sm.T.to_string())
    print(pw.preferred.value_counts().to_string())


# ---------------------------------------------------------------- render
def render_step(sets):
    from prism.report import sections
    for s in sets:
        recs, outs = load_records(s), load_outputs(s)
        for key, o in outs.items():
            _, arm, sid = key.split("|")
            d = OUT / "reports" / s / arm
            d.mkdir(parents=True, exist_ok=True)
            (d / f"{sid}.md").write_text(sections.render(recs[sid], facts_v2(recs[sid]),
                                                         [prompts_v2.render_text(o["text"], arm)]))


def figure_step():
    """v2 example page for the pre-specified scan of the v1 figure (first early post-RT scan id, report_agent.examples);
    record from this module's evaluation set (CV repeat 1). Does not touch the v1 figure (fig5a)."""
    import shutil
    from prism.analyses.report_agent import FIG, examples
    from prism.report.figures import example_report
    sid = examples()["early_post_rt"]
    rec, o = load_records("eval")[sid], load_outputs("eval")[f"eval|v2|{sid}"]
    det = json.loads((OUT / "check_details_eval.json").read_text())[f"eval|v2|{sid}"]
    sec = prompts_v2.sectioned(o["text"])
    summ = [f"FINDINGS: {' '.join(sec['findings'])}", f"IMPRESSION: {' '.join(sec['impression'])}"]
    example_report(rec, facts_v2(rec), summ, OUT / "example_report_v2", det["check"])
    FIG.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        shutil.copy(OUT / f"example_report_v2.{ext}", FIG / f"fig6a_example_report_v2.{ext}")
    print("figure:", sid)


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="prism reportuse", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--steps", nargs="+", default=["reference", "records", "requests", "generate", "evaluate", "render"])
    ap.add_argument("--sets", nargs="+", default=["dev"])
    a = ap.parse_args(argv)
    OUT.mkdir(parents=True, exist_ok=True)
    steps = {"reference": reference_step, "records": lambda: records_step(a.sets),
             "requests": lambda: requests_step(a.sets), "generate": lambda: generate_step(a.sets),
             "evaluate": lambda: evaluate_step(a.sets), "judge": lambda: judge_step(a.sets),
             "render": lambda: render_step(a.sets), "figure": figure_step}
    for st in a.steps:
        print(f"== reportuse {st}", flush=True)
        steps[st]()


if __name__ == "__main__":
    main()
