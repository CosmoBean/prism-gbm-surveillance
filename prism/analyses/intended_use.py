"""Scan-day intended use, within-phase performance and censoring sensitivity of the deployed model (C2).

ANALYSIS PLAN: docs/results/INTENDED_USE.md, section "Plan (pre-specified)", committed (74eaaf5) before any of the new
quantities was computed; snapshotted to outputs/results/analyses/intended_use/PLAN_snapshot.md by the first real run.

Intended-use population (scan-day information only): scans taken on or after the documented RT start date
(phase_label != pre_rt: during RT, within 12 weeks after RT, later). Grade 4 primary, all gliomas secondary.
No model is retrained: stored OOF predictions are rescored.

  C2 / core         phase_censoring/oof_<pop>_full.csv.gz (full-cohort fit; PRIMARY in intended use = "@full")
                    phase_censoring/oof_<pop>_rt_started.csv.gz (refitted inside intended use; secondary)
  radiomics         c3/grade4/oof_repeats.csv.gz            NESTED|-|-|-|ridge vs None|none|none|none|ridge
  phase ladder      phase_ladder/oof_repeats_grade4_post_rt R2+I2|ridge vs R2|ridge (post-RT surveillance scans)
  fine-tuned stack  finetune/grade4/oof_repeats.csv.gz      core+ft:brats21 vs core

Schemes: marginal_km (headline), phase5_km (Sensitivity 1), deaths_nonevent_km (Sensitivity 2: death without documented
progression within 120 d recoded as a non-event, remaining censoring by marginal KM), deaths_as_controls (existing
unweighted scheme, reference). Paired patient-cluster bootstrap with weights re-estimated in every draw
(phase_censoring.bootstrap); headline AUC CI, O/E and slope from metrics.evaluate_repeated.

    python -m prism intendeduse [--workers 32] [--n-boot 1000] [--populations grade4 all_glioma]
    -> $PRISM_OUTPUTS/results/analyses/intended_use/
       counts.csv, headline.csv, schemes.csv, contrasts.csv, within_phase.csv, rule.csv, checks.csv, run_info.json
"""

from __future__ import annotations

import argparse
import json
import time
import warnings

import numpy as np
import pandas as pd

from prism.analyses import phase_censoring as pc
from prism.audit.provenance import git_state
from prism.config import REPO, RESULTS
from prism.models.metrics import evaluate_repeated

H = pc.H
OUT = RESULTS / "analyses" / "intended_use"
IN_SCOPE = ("during_rt", "early_post_rt", "later_post_rt")
POST_RT = ("early_post_rt", "later_post_rt")
SCHEMES = ("marginal_km", "phase5_km", "deaths_as_controls")
GAIN_BAR = 0.03

RAD = ("c3/grade4/oof_repeats.csv.gz", {"core_c3": "None|none|none|none|ridge", "core+radiomics": "NESTED|-|-|-|ridge"})
FT = ("analyses/finetune/grade4/oof_repeats.csv.gz", {"core_ft": "core", "core+ft": "core+ft:brats21"})
LAD = ("analyses/phase_ladder/oof_repeats_grade4_post_rt.csv.gz", {"R2": "R2|ridge", "R2+I2": "R2+I2|ridge"})
# (arm, reference, label); contrasts that enter the decision rule are flagged
CONTRASTS = [("C2", "R3", "C2 - core", False), ("C2@full", "R3@full", "C2 - core (full-cohort fit)", False),
             ("core+radiomics", "core_c3", "core + nested radiomics - core", True),
             ("core+ft", "core_ft", "core + fine-tuned stack - core", True),
             ("R2+I2", "R2", "R2 + I2 - R2 (post-RT)", True)]


def read_oof(rel: str, cols: dict, scan_ids) -> dict:
    f = pd.read_csv(RESULTS / rel).set_index("scan_id").loc[list(scan_ids)]
    return {k: np.array([f[f"{c}#r{r}"].to_numpy(float) for r in range(5)]) for k, c in cols.items()}


def deaths_nonevent(d: pd.DataFrame) -> tuple[pd.DataFrame, np.ndarray]:
    """Death without documented progression within H of the scan -> non-event (control with status known beyond H)."""
    d = d.copy()
    y = d[f"label_{H}"].to_numpy(float)
    rec = (np.isnan(y) & d["death_without_progression"].to_numpy(bool) & ~d["event"].to_numpy(bool)
           & (d["time_to_event"].to_numpy(float) <= H))
    d.loc[rec, f"label_{H}"] = 0.0
    d.loc[rec, "status_known_indefinitely"] = True
    return d, rec


def analysis_sets(pop: str):
    """{name: (d, oofs, p4, p5)} for the population; d has the full-cohort row order restricted to the set."""
    cohort, _, _, p4, p5 = pc.load(pop)
    full = pd.read_csv(pc.OUT / f"oof_{pop}_full.csv.gz")
    assert (full.scan_id.to_numpy() == cohort.scan_id.to_numpy()).all()
    take = lambda df, a: np.array([df[f"{a}#r{r}"].to_numpy(float) for r in range(5)])
    base = {"R3": take(full, "R3"), "C2": take(full, "C2")}
    if pop == "grade4":
        base.update(read_oof(RAD[0], RAD[1], cohort.scan_id))
        base.update(read_oof(FT[0], FT[1], cohort.scan_id))
    sets = {"full": (cohort.reset_index(drop=True), base, p4, p5)}
    iu = np.isin(p4, IN_SCOPE)
    rs = pd.read_csv(pc.OUT / f"oof_{pop}_rt_started.csv.gz")
    assert (rs.scan_id.to_numpy() == cohort.scan_id[iu].to_numpy()).all()
    oo = {f"{k}@full" if k in ("R3", "C2") else k: v[:, iu] for k, v in base.items()}
    oo.update({"R3": take(rs, "R3"), "C2": take(rs, "C2")})  # refitted inside intended use
    sets["intended_use"] = (cohort[iu].reset_index(drop=True), oo, p4[iu], p5[iu])
    if pop == "grade4":
        pr = np.isin(p4, POST_RT)
        dpr = cohort[pr].reset_index(drop=True)
        sets["post_rt"] = (dpr, read_oof(LAD[0], LAD[1], dpr.scan_id), p4[pr], p5[pr])
    return sets


def count_rows(pop, name, d, p4, rec):
    rows = []
    for lv in ("all",) + tuple(sorted(set(p4))):
        m = np.ones(len(d), bool) if lv == "all" else p4 == lv
        dwp = d["death_without_progression"].to_numpy(bool) & (d["time_to_event"].to_numpy(float) <= H) \
            & ~d["event"].to_numpy(bool)
        rows.append({"population": pop, "set": name, "phase": lv, **pc.counts(d, m),
                     "deaths_wo_progression_within_H": int((m & dwp).sum()), "recoded_sens2": int((m & rec).sum())})
    return rows


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="prism intendeduse", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workers", type=int, default=32)
    ap.add_argument("--n-boot", type=int, default=1000)
    ap.add_argument("--populations", nargs="+", default=list(pc.POPS))
    a = ap.parse_args(argv)
    t0 = time.time()
    warnings.filterwarnings("ignore")
    OUT.mkdir(parents=True, exist_ok=True)
    snap = OUT / "PLAN_snapshot.md"
    if not snap.exists():
        doc = (REPO / "docs" / "results" / "INTENDED_USE.md").read_text()
        plan = doc.split("## Plan (pre-specified)", 1)[1].split("\n## ", 1)[0]
        snap.write_text(f"# PLAN snapshot ({time.strftime('%Y-%m-%dT%H:%M:%S')}, git {git_state()['commit'][:10]})\n\n"
                        "## Plan (pre-specified)" + plan)
    T = {k: [] for k in ("counts", "headline", "schemes", "contrasts", "within_phase", "checks")}
    for pop in a.populations:
        for name, (d, oofs, q4, q5) in analysis_sets(pop).items():
            drec, rec = deaths_nonevent(d)
            T["counts"] += count_rows(pop, name, d, q4, rec)
            # headline machinery: AUC CI, Brier, O/E (KM), slope; marginal and Sensitivity 2 (recoded deaths)
            for lab, dd in (("marginal_km", d), ("deaths_nonevent_km", drec)):
                ev = evaluate_repeated(dd, oofs, H, n_boot=a.n_boot)
                for k, r in ev.iterrows():
                    T["headline"].append({"population": pop, "set": name, "scheme": lab, "arm": k,
                                          **{c: r.get(c) for c in ("auc_ipcw", "auc_ipcw_lo", "auc_ipcw_hi", "brier_ipcw",
                                                                   "oe_ratio", "cal_slope", "auc_verified")}})
            subsets = {f"phase4={lv}": q4 == lv for lv in sorted(set(q4))} if name == "intended_use" else None
            pt, dr = pc.bootstrap(d, oofs, q4, q5, a.n_boot, a.workers, schemes=SCHEMES, subsets=subsets,
                                  pair_strata=q4 if name == "intended_use" else None)
            p2, d2 = pc.bootstrap(drec, oofs, q4, q5, a.n_boot, a.workers, schemes=("marginal_km",))
            pt.update({("deaths_nonevent_km",) + k[1:]: v for k, v in p2.items()})
            dr.update({("deaths_nonevent_km",) + k[1:]: v for k, v in d2.items()})
            for k in oofs:  # bootstrap point == headline estimator
                h = [x for x in T["headline"] if (x["population"], x["set"], x["arm"]) == (pop, name, k)]
                for x in h:
                    assert abs(pt[(x["scheme"], k, "all")] - x["auc_ipcw"]) < 1e-9, (pop, name, k, x["scheme"])
            for sc in SCHEMES + ("deaths_nonevent_km",):
                for k in oofs:
                    key = (sc, k, "all")
                    lo, hi = pc.ci(dr[key])
                    row = {"population": pop, "set": name, "scheme": sc, "arm": k, "auc": pt[key], "auc_lo": lo,
                           "auc_hi": hi}
                    if sc != "marginal_km":
                        row.update({f"vs_marginal_{x}": v for x, v in
                                    pc.contrast(pt, dr, key, ("marginal_km", k, "all")).items()})
                    T["schemes"].append(row)
                for arm, ref, label, rule in CONTRASTS:
                    if arm not in oofs or ref not in oofs:
                        continue
                    ka, kr = (sc, arm, "all"), (sc, ref, "all")
                    c = pc.contrast(pt, dr, ka, kr)
                    dd_ = {}
                    if sc != "marginal_km":
                        m1, m0 = ("marginal_km", arm, "all"), ("marginal_km", ref, "all")
                        x = (dr[ka] - dr[kr]) - (dr[m1] - dr[m0])
                        dd_ = {"change_vs_marginal": (pt[ka] - pt[kr]) - (pt[m1] - pt[m0]),
                               "change_lo": pc.ci(x)[0], "change_hi": pc.ci(x)[1]}
                    T["contrasts"].append({"population": pop, "set": name, "scheme": sc, "contrast": label,
                                           "arm": arm, "reference": ref, "in_rule": rule, **c, **dd_})
            if name == "intended_use":
                y = d[f"label_{H}"].to_numpy(float)
                for k in ("C2@full", "R3@full", "C2", "R3"):
                    for sn, m in {**subsets, "pooled_within_phase": None}.items():
                        key = ("marginal_km", k, sn if m is not None else "phase_stratified")
                        mm = np.ones(len(d), bool) if m is None else m
                        rep = m is None or ((y[m] == 1).sum() >= pc.MIN_STRATUM and (y[m] == 0).sum() >= pc.MIN_STRATUM)
                        lo, hi = pc.ci(dr[key]) if rep else (np.nan, np.nan)
                        T["within_phase"].append({"population": pop, "arm": k, "phase": sn.replace("phase4=", ""),
                                                  **pc.counts(d, mm), "auc": pt[key], "auc_lo": lo, "auc_hi": hi,
                                                  "descriptive_only": not rep})
            print(f"{pop}/{name} done {time.time() - t0:.0f}s", flush=True)
    # checks: stored OOF reproduce published AUCs
    hd = pd.DataFrame(T["headline"])
    g = hd[(hd.scheme == "marginal_km")].set_index(["population", "set", "arm"]).auc_ipcw
    pub = {("grade4", "full", "R3"): 0.698, ("grade4", "full", "C2"): 0.678, ("grade4", "full", "core_c3"): 0.698,
           ("grade4", "full", "core+radiomics"): 0.666, ("grade4", "full", "core_ft"): 0.698,
           ("grade4", "full", "core+ft"): 0.708, ("grade4", "post_rt", "R2"): 0.549,
           ("grade4", "post_rt", "R2+I2"): 0.610, ("grade4", "intended_use", "R3"): 0.617,
           ("grade4", "intended_use", "C2"): 0.595}
    T["checks"] = [{"key": "/".join(k), "published": v, "here": g.get(k, np.nan),
                    "ok": abs(g.get(k, np.nan) - v) < 0.0006} for k, v in pub.items() if k[0] in a.populations]
    # decision rule
    ct = pd.DataFrame(T["contrasts"])
    rule = []
    for _, r in ct[ct.in_rule & ct.scheme.isin(["phase5_km", "deaths_nonevent_km"])
                   & ((ct.set == "full") | (ct.contrast.str.contains("post-RT") & (ct.set == "post_rt")))].iterrows():
        rule.append({"item": f"imaging: {r.contrast}", "scheme": r.scheme, "diff": r["diff"], "lo": r.diff_lo,
                     "hi": r.diff_hi, "fails": bool(r["diff"] >= GAIN_BAR and r.diff_lo > 0)})
    sc = pd.DataFrame(T["schemes"])
    for s in ("marginal_km", "phase5_km", "deaths_nonevent_km"):
        x = sc[(sc.population == "grade4") & (sc.set == "full") & (sc.arm == "C2") & (sc.scheme == s)].iloc[0]
        rule.append({"item": "C2 headline lower CI > 0.5 (grade 4 full)", "scheme": s, "diff": x.auc, "lo": x.auc_lo,
                     "hi": x.auc_hi, "fails": bool(x.auc_lo <= 0.5)})
    for pop in a.populations:
        x = hd[(hd.population == pop) & (hd.set == "intended_use") & (hd.arm == "C2@full")
               & (hd.scheme == "marginal_km")].iloc[0]
        rule.append({"item": f"C2@full intended use ({pop}): "
                             + ("above chance" if x.auc_ipcw_lo > 0.5 else "not distinguishable from chance")
                             + f"; O/E {x.oe_ratio:.2f} " + ("adequate" if 0.8 <= x.oe_ratio <= 1.25 else "not adequate"),
                     "scheme": "marginal_km", "diff": x.auc_ipcw, "lo": x.auc_ipcw_lo, "hi": x.auc_ipcw_hi,
                     "fails": np.nan})
    T["rule"] = rule
    for k, rows in T.items():
        pd.DataFrame(rows).to_csv(OUT / f"{k}.csv", index=False)
    (OUT / "run_info.json").write_text(json.dumps({"argv": vars(a), "seconds": round(time.time() - t0),
                                                   "git": git_state()["commit"][:10]}, indent=1))
    print(pd.DataFrame(T["checks"]).to_string(index=False))
    print(pd.DataFrame(rule).round(3).to_string(index=False))
    print(f"total {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
