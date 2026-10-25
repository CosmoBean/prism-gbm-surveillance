"""PRISM report version 3 for detection at the scan (docs/results/SYSTEM_PLAN.md sections 3-5, S5-S7;
docs/results/REPORT_V3.md).

    PYTHONPATH=. .venv/bin/python -m prism.analyses.report_v3 --steps <step> [<step> ...] [--sets dev eval stress]

Steps
  select     the 20 MU development patients, seed 20261026 (SYSTEM_PLAN section 4), chosen before any report exists;
             written once to outputs/results/analyses/report_v3/dev_patients.json and never overwritten
  sets       the development and evaluation record sets from the system records (records_{mu,lumiere,ucsf}.jsonl)
  requests   LLM requests (facts v3 + prompt v3) for a set
  generate   local vLLM run (separate LLM env, one GPU; prism.report.vllm_run)
  evaluate   frozen checker v3 (S5, S6) and, for the stress set, the perturbation rule (S7)
  stress     build the 30-record perturbation set (SYSTEM_PLAN section 4) from the evaluation records
  render     full reports (markdown, and HTML with the segmentation figure) for the examples
The LLM never sees images: the figure is attached by the renderer only.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import time
from pathlib import Path

import numpy as np
import pandas as pd

from prism.config import MEASUREMENTS, OUTPUTS, REPO, RESULTS

OUT = RESULTS / "analyses" / "report_v3"
SYSTEM = RESULTS / "analyses" / "system"
DEV_SEED = 20261026
N_DEV = 20
LLM_ENV = os.environ.get("PRISM_LLM_ENV", "/project/community/sbandred/envs/prism-llm")
WRITER = ("Qwen/Qwen3.8-27B", "1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0", {"enable_thinking": False})
SMALL = ("Qwen/Qwen3.5-9B", "c202236235762e1c871ad0ccb60c8ee5ba337b9a", {"enable_thinking": False})


# ---------------------------------------------------------------- development patients
def dev_population() -> pd.DataFrame:
    """MU grade-4 detection scans in the intended use (RT started by the scan day), primary set (progression scans
    and verified stable negatives), as in DETECTION_TASK.md."""
    from prism.analyses.detection import COHORT_CSV
    d = pd.read_csv(COHORT_CSV)
    return d[d.grade4 & d.intended_use & (d.label_det.eq(1) | d.neg_primary)]


def select_step():
    p = OUT / "dev_patients.json"
    if p.exists():
        print(f"{p} exists; selection is fixed, not redone", flush=True)
        return json.loads(p.read_text())
    pop = dev_population()
    pats = sorted(pop.patient_id.unique())
    rng = np.random.default_rng(DEV_SEED)
    dev = sorted(rng.choice(pats, N_DEV, replace=False).tolist())
    obj = {"seed": DEV_SEED, "n": N_DEV, "population": "MU grade 4, intended use (RT started by the scan day), "
           "primary detection set (progression scans + verified stable negatives); outputs/data/detection_cohort.csv",
           "n_patients_in_population": len(pats), "n_scans_in_population": int(len(pop)),
           "rule": "numpy default_rng(seed).choice(sorted patient ids, 20, replace=False), sorted",
           "selected_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
           "n_dev_scans": int(pop.patient_id.isin(dev).sum()), "patients": dev}
    OUT.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=1))
    print(f"dev: {len(dev)} of {len(pats)} patients, {obj['n_dev_scans']} scans -> {p}", flush=True)
    return obj


# ---------------------------------------------------------------- record sets
def records_ready() -> bool:
    return (SYSTEM / "RECORDS_READY").exists()


def load_set(s: str) -> dict:
    p = OUT / "records" / f"{s}.jsonl"
    return {r["record_id"]: r for r in map(json.loads, open(p))}


def _members(cohort: str) -> set:
    """Evaluation-set membership from the EVALUATION_ONLY file: only the membership column is read, never the
    label. MU: eval_intended_use (grade 4, intended use, primary detection set); LUMIERE: all detection scans;
    UCSF: every grade-4 scan-2 record (SYSTEM_PLAN section 4)."""
    col = {"mu": "eval_intended_use", "lumiere": "eval_all", "ucsf": None}[cohort]
    if col is None:
        return None
    m = pd.read_csv(SYSTEM / f"records_{cohort}_EVALUATION_ONLY.csv", usecols=["record_id", col])
    return set(m.record_id[m[col].astype(bool)])


def sets_step(_sets=None):
    """dev: the development patients' MU intended-use scans; eval: MU intended-use scans of all other patients,
    all LUMIERE detection scans, all UCSF grade-4 scan-2 records."""
    assert records_ready(), "system records not ready"
    dev = set(json.loads((OUT / "dev_patients.json").read_text())["patients"])
    out = {"dev": [], "eval": []}
    for coh in ("mu", "lumiere", "ucsf"):
        recs = [json.loads(l) for l in open(SYSTEM / f"records_{coh}.jsonl")]
        mem = _members(coh)
        for r in recs:
            if r["population"] != "grade4" or (mem is not None and r["record_id"] not in mem):
                continue
            if coh == "ucsf" and not r["population_flags"].get("scan2"):
                continue
            out["dev" if coh == "mu" and r["patient_id"] in dev else "eval"].append(r)
    (OUT / "records").mkdir(parents=True, exist_ok=True)
    for s, rs in out.items():
        with open(OUT / "records" / f"{s}.jsonl", "w") as f:
            f.writelines(json.dumps(r) + "\n" for r in rs)
    summ = {s: pd.Series([r["cohort"] for r in rs]).value_counts().to_dict() for s, rs in out.items()}
    summ["dev_patients"] = len({r["patient_id"] for r in out["dev"]})
    (OUT / "sets.json").write_text(json.dumps(summ, indent=1))
    print(summ, flush=True)


# ---------------------------------------------------------------- requests / generation
def _facts(rec):
    from prism.report.facts_v3 import facts_v3
    return facts_v3(rec)


def requests_step(sets, tag=""):
    from prism.report import prompts_v3
    (OUT / "llm").mkdir(parents=True, exist_ok=True)
    for s in sets:
        recs = load_set(s)
        rows = [{"id": f"{s}|{sid}", "messages": prompts_v3.grounded_v3(_facts(r)), "max_tokens": 2048,
                 "schema": prompts_v3.SCHEMA_V3} for sid, r in recs.items()]
        with open(OUT / "llm" / f"requests_{s}.jsonl", "w") as f:
            f.writelines(json.dumps(r) + "\n" for r in rows)
        print(f"{s}: {len(rows)} requests (prompt {prompts_v3.VERSION})", flush=True)


def run_vllm(model, req, out, max_len=8192, gpu_mem=0.90, extra=()):
    mid, rev, ck = model
    cmd = [f"{LLM_ENV}/bin/python", "-m", "prism.report.vllm_run", "--model", mid, "--revision", rev, "--requests",
           str(req), "--out", str(out), "--tp", "1", "--chat-kwargs", json.dumps(ck), "--max-model-len",
           str(max_len), "--gpu-mem", str(gpu_mem), *extra]
    env = {**os.environ, "PYTHONPATH": str(REPO), "PATH": f"{LLM_ENV}/bin:{os.environ['PATH']}", "HF_HUB_OFFLINE": "1",
           "VLLM_NO_USAGE_STATS": "1", "DO_NOT_TRACK": "1"}
    print(" ".join(cmd), flush=True)
    t = time.time()
    subprocess.run(cmd, env=env, check=True, cwd=REPO)
    print(f"{out.name} done in {time.time() - t:.0f}s", flush=True)


def generate_step(sets):
    small = os.environ.get("REPORT_V3_MODEL") == "small"
    for s in sets:
        tag = "_small" if small else ""
        run_vllm(SMALL if small else WRITER, OUT / "llm" / f"requests_{s}.jsonl",
                 OUT / "llm" / f"outputs_{s}{tag}.jsonl")


def load_outputs(s, tag=""):
    p = OUT / "llm" / f"outputs_{s}{tag}.jsonl"
    return {r["id"]: r for r in map(json.loads, open(p))} if p.exists() else {}


# ---------------------------------------------------------------- evaluation
def wilson(k, n, z=1.96):
    if n == 0:
        return (np.nan, np.nan)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (c - h, c + h)


def check_row(sid, rec, out):
    from prism.report import checker
    F = _facts(rec)
    claims = checker.parse_structured(out["text"]) if out else None
    r = checker.check(claims, F, card=True)
    words = len(" ".join(c["text"] for c in claims).split()) if claims else 0
    row = {"scan_id": sid, "cohort": rec["cohort"], "pass": r["pass"], "parsed": r["parsed"],
           "finish_reason": (out or {}).get("finish_reason"), "words": words,
           "card_tier": F["card.tier"], "card_tier_required": F["card.tier"] in ("few cases", "not tested")}
    if r["parsed"]:
        row.update({"n_claims": r["n_claims"], "n_unsupported": r["n_unsupported"],
                    "n_invalid_citations": r["n_invalid_citations"], "flags_active": len(r["active_flags"]),
                    "flags_omitted": len(r["flags_omitted"]), "flags_spurious": len(r["flags_spurious"]),
                    "any_forbidden": r["any_forbidden"], "conformal_pass": r["conformal"]["conformal_pass"],
                    "agreement_pass": r["agreement"]["agreement_pass"], "required_pass": r["required"]["required_pass"],
                    "card_pass": r["card"]["card_pass"], "card_tier_stated": r["card_tier_stated"],
                    "n_output_tokens": out.get("n_output_tokens")})
        for k, v in r["forbidden"].items():
            row[f"forbidden_{k}"] = bool(v)
    return row, r, F, claims


def evaluate_set(s, tag=""):
    recs, outs = load_set(s), load_outputs(s, tag)
    rows, details = [], {}
    for sid, rec in recs.items():
        row, r, F, claims = check_row(sid, rec, outs.get(f"{s}|{sid}"))
        rows.append(row)
        if not r["pass"]:
            details[sid] = {k: r.get(k) for k in ("unsupported", "flags_omitted", "flags_spurious", "forbidden",
                                                  "conformal", "agreement", "required", "card")}
            details[sid]["claims"] = claims
    df = pd.DataFrame(rows)
    df.to_csv(OUT / f"checks_{s}{tag}.csv", index=False)
    (OUT / f"check_details_{s}{tag}.json").write_text(json.dumps(details, indent=1, default=str))
    return df


def summarise(df: pd.DataFrame) -> pd.DataFrame:
    out = []
    for coh, g in [("all", df)] + list(df.groupby("cohort")):
        n, k = len(g), int(g["pass"].sum())
        req = g[g.card_tier_required]
        ks = int(req.get("card_tier_stated", pd.Series(dtype=bool)).fillna(False).sum())
        row = {"cohort": coh, "n": n, "pass": k, "pass_rate": k / n if n else np.nan,
               "pass_ci_low": wilson(k, n)[0], "pass_ci_high": wilson(k, n)[1],
               "S5_met": (k / n >= 0.95) if n else None,
               "tier_required": len(req), "tier_stated": ks, "S6_met": (ks == len(req)) if len(req) else None,
               "parsed": int(g.parsed.sum()), "truncated": int((g.finish_reason == "length").sum()),
               "words_median": float(g.words.median()) if n else np.nan}
        for c in ("n_unsupported", "flags_omitted", "flags_spurious", "n_invalid_citations"):
            if c in g:
                row[f"reports_with_{c}"] = int((g[c].fillna(0) > 0).sum())
        for c in [c for c in g.columns if c.startswith("forbidden_")] + ["conformal_pass", "agreement_pass",
                                                                          "required_pass", "card_pass"]:
            if c in g:
                row[c if c.startswith("forbidden_") else c.replace("_pass", "_fail")] = int(
                    g[c].fillna(False).sum() if c.startswith("forbidden_") else (~g[c].fillna(False).astype(bool)).sum())
        out.append(row)
    return pd.DataFrame(out)


def evaluate_step(sets):
    tag = "_small" if os.environ.get("REPORT_V3_MODEL") == "small" else ""
    for s in sets:
        if s == "stress":
            stress_evaluate(tag)
            continue
        df = evaluate_set(s, tag)
        sm = summarise(df)
        sm.to_csv(OUT / f"summary_{s}{tag}.csv", index=False)
        print(sm.to_string(index=False), flush=True)


# ---------------------------------------------------------------- perturbation set (S7)
KINDS = ("card_tier", "agreement", "et_change", "out_of_range", "conformal")
N_PER_KIND = 6
NEW_OOD = "age = 95 outside training 1-99% [31, 84]"


def _eligible(kind, r):
    if kind == "et_change":
        return bool(r["measurements"].get("previous")) and r["measurements"]["volumes_cc"].get("et") is not None
    return True


def perturb_one(kind: str, r: dict) -> tuple[dict, dict]:
    """One field of the record changed (with what follows from it mechanically); returns (record, log)."""
    import copy
    x = copy.deepcopy(r)
    c, fl = x["card"], x["flags"]
    own = c["own_cohort"]
    log = {"record_id": r["record_id"], "kind": kind}
    if kind == "card_tier":
        e = c["evidence"][own]
        old = e["tier"]
        new, (npos, nneg) = {"tested": ("few cases", (4, 6)), "few cases": ("not tested", (0, 0)),
                             "not tested": ("few cases", (2, 3))}[old]
        c["evidence"][own] = {"cohort": own, "cohort_text": e.get("cohort_text"), "tier": new, "n_scans": npos + nneg,
                              "n_progression": npos, "n_no_progression": nneg}
        c["tier"], fl["tier"], fl["tier_flag"] = new, new, new != "tested"
        log.update(old=old, new=new)
    elif kind == "agreement":
        a = c["agreement"]
        med = a["medians"]["images"]
        new_side = "below" if a["images_side"] == "above" else "above"
        s = float(np.clip(med + (0.15 if new_side == "above" else -0.15), 0.01, 0.99))
        x["scores"]["images"] = s
        a.update(images_side=new_side, images_score=s, agree=new_side == a["timeline_side"])
        for k in ("measured", "progression_rate_same_direction"):
            a.pop(k, None)
        fl["pathways_disagree"] = not a["agree"]
        log.update(old=f"agree={not a['agree']}, images {r['scores']['images']:.2f}",
                   new=f"agree={a['agree']}, images {s:.2f}", new_image_score=round(s, 2),
                   old_image_score=round(r["scores"]["images"], 2))
    elif kind == "et_change":
        m = x["measurements"]
        cur = m["volumes_cc"]["et"]
        old = m["change_from_previous_cc"]["et"]
        prev = cur + 5.0 if old >= 0 else max(cur - 5.0, 0.0)
        m["previous"]["volumes_cc"]["et"] = prev
        m["change_from_previous_cc"]["et"] = cur - prev
        log.update(old=round(old, 1), new=round(cur - prev, 1))
    elif kind == "out_of_range":
        old = list(fl.get("out_of_range_reasons") or [])
        new = [] if fl["out_of_range"] else [NEW_OOD]
        fl["out_of_range"], fl["out_of_range_reasons"] = bool(new), new
        if c.get("inputs_in_range") is not None:
            c["inputs_in_range"] = {"in_range": not new, "reasons": new}
        log.update(old="; ".join(old) or "off", new="; ".join(new) or "off")
    elif kind == "conformal":
        old = x["conformal"]["alpha_0.2"]["combined"]
        new = ("{0}" if x["scores"]["combined"] < 0.5 else "{1}") if old == "{0, 1}" else "{0, 1}"
        x["conformal"]["alpha_0.2"]["combined"] = new
        fl["conformal_uncertain"] = new == "{0, 1}"
        log.update(old=old, new=new)
    fl["any_flag"] = any(fl[k] for k in ("pathways_disagree", "out_of_range", "tier_flag", "conformal_uncertain"))
    x["record_id"] = r["record_id"] + f"|perturbed:{kind}"
    log["perturbed_id"] = x["record_id"]
    return x, log


def stress_step(_sets=None, seed=0):
    ev = list(load_set("eval").values())
    rng = np.random.default_rng(seed)
    used, recs, logs = set(), [], []
    for kind in KINDS:
        pool = [r for r in ev if _eligible(kind, r) and r["record_id"] not in used]
        idx = rng.choice(len(pool), N_PER_KIND, replace=False)
        for i in sorted(idx):
            r = pool[i]
            used.add(r["record_id"])
            x, log = perturb_one(kind, r)
            recs.append(x)
            logs.append(log)
    with open(OUT / "records" / "stress.jsonl", "w") as f:
        f.writelines(json.dumps(r) + "\n" for r in recs)
    pd.DataFrame(logs).to_csv(OUT / "stress_log.csv", index=False)
    print(f"stress: {len(recs)} perturbed records", flush=True)


def follows(kind: str, log: dict, F_old: dict, F: dict, claims: list | None, r: dict) -> bool:
    """Pre-specified S7 rule (REPORT_V3.md): the report states the changed field's new value and not the old one."""
    import re
    from prism.report import checker as K
    if claims is None:
        return False
    text = " ".join(c["text"] for c in claims)
    if kind == "card_tier":
        new, old = log["new"], log["old"]
        said_new = r["card_tier_stated"] if new != "tested" else True
        said_old = re.search(K.CARD_TIER_WORDS.get(old, r"\bAUC\b"), text, re.I) is not None
        return bool(said_new) and not said_old
    if kind == "agreement":
        nums = [float(n) for n in K.numbers(text)]
        return (r["agreement"]["agreement_pass"] and log["new_image_score"] in nums
                and (log["old_image_score"] not in nums or log["old_image_score"] == log["new_image_score"]))
    if kind == "et_change":
        new, old = abs(float(log["new"])), abs(float(log["old"]))
        nums = [abs(float(n)) for n in K.numbers(text)]
        st = F.get("meas.enhancing_change_since_previous_statement", "")
        direction = "larger" if float(log["new"]) > 0 else "smaller"
        ok_dir = re.search(direction if direction == "larger" else r"smaller|less|decreas|lower|fell|reduc", text, re.I)
        return new in nums and (old not in nums or old == new) and bool(ok_dir) and bool(st)
    if kind == "out_of_range":
        if log["new"] != "off":
            return "out_of_range" not in r["flags_omitted"]
        old_plain = F_old["flags.out_of_range.reason"].split(";")[0].strip()[:25].lower()
        return "out_of_range" not in r["flags_spurious"] and old_plain not in text.lower()
    if kind == "conformal":
        return r["conformal"]["conformal_pass"]
    raise ValueError(kind)


def stress_evaluate(tag=""):
    from prism.report import checker
    recs, outs = load_set("stress"), load_outputs("stress", tag)
    orig = load_set("eval")
    logs = pd.read_csv(OUT / "stress_log.csv").set_index("perturbed_id")
    rows = []
    for rid, rec in recs.items():
        lg = logs.loc[rid].to_dict()
        F = _facts(rec)
        F_old = _facts(orig[lg["record_id"]])
        o = outs.get(f"stress|{rid}")
        claims = checker.parse_structured(o["text"]) if o else None
        r = checker.check(claims, F, card=True)
        fol = follows(lg["kind"], lg, F_old, F, claims, r) if r["parsed"] else False
        rows.append({"perturbed_id": rid, "cohort": rec["cohort"], "kind": lg["kind"], "old": lg["old"],
                     "new": lg["new"], "follows": fol, "check_pass": r["pass"], "follows_and_pass": fol and r["pass"]})
    df = pd.DataFrame(rows)
    df.to_csv(OUT / f"stress{tag}.csv", index=False)
    sm = df.groupby("kind")[["follows", "check_pass", "follows_and_pass"]].sum().reset_index()
    sm.loc[len(sm)] = ["total", df.follows.sum(), df.check_pass.sum(), df.follows_and_pass.sum()]
    sm["n"] = list(df.groupby("kind").size()) + [len(df)]
    sm["S7_met"] = sm.follows / sm.n >= 0.90
    sm.to_csv(OUT / f"summary_stress{tag}.csv", index=False)
    print(sm.to_string(index=False), flush=True)


# ---------------------------------------------------------------- rendering
def figure_path(rec: dict):
    p = SYSTEM / "figures" / rec["cohort"] / f"{rec['scan_id']}.png"
    return p if p.exists() else None


def render_set(s: str, ids=None, tag="", html_too=False):
    from prism.report import prompts_v3, sections_v3
    recs, outs = load_set(s), load_outputs(s, tag)
    d = OUT / "reports" / f"{s}{tag}"
    d.mkdir(parents=True, exist_ok=True)
    for rid, rec in recs.items():
        if ids is not None and rid not in ids:
            continue
        F = _facts(rec)
        o = outs.get(f"{s}|{rid}")
        prose = prompts_v3.sectioned(o["text"]) if o else None
        fig = figure_path(rec)
        name = rid.replace("|", "__")
        (d / f"{name}.md").write_text(sections_v3.render_md(rec["scan_id"], F, prose, str(fig) if fig else None))
        if html_too:
            (d / f"{name}.html").write_text(sections_v3.render_html(rec["scan_id"], F, prose, fig))


def render_step(sets):
    tag = "_small" if os.environ.get("REPORT_V3_MODEL") == "small" else ""
    for s in sets:
        render_set(s, tag=tag)
        print(f"rendered {s}{tag}", flush=True)


def examples_step(_sets=None):
    """Three example reports with the figure (HTML), chosen by rule before reading any evaluation text: per cohort,
    the first record id (sort order) that has a segmentation figure."""
    recs = load_set("eval")
    pick = []
    for coh in ("mu", "lumiere", "ucsf"):
        ids = sorted(k for k, r in recs.items() if r["cohort"] == coh and figure_path(r) is not None)
        if ids:
            pick.append(ids[0])
    render_set("eval", ids=set(pick), html_too=True)
    (OUT / "examples.json").write_text(json.dumps(pick, indent=1))
    print("examples:", len(pick), flush=True)


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", nargs="+", required=True)
    ap.add_argument("--sets", nargs="+", default=["dev"])
    a = ap.parse_args(argv)
    for s in a.steps:
        globals()[f"{s}_step"](*([a.sets] if s != "select" else []))


if __name__ == "__main__":
    main()
