"""EXPLORATORY (designed after S1-S4 had been seen): a reduced confidence design on the same system records.

Why: the pre-specified "any flag" marks 91-100% of scans, the out-of-range flag picks out no errors in any cohort, and
the card tier is reversed on MU (docs/results/SYSTEM_RESULTS.md). This script asks, post hoc, how four reduced flag
rules behave with the same metrics and bootstrap as S2 / S3 (patient-cluster, 1,000 draws, system.SEED):

  D1  pathways disagree                                  (the pre-specified disagreement flag alone)
  D2  combined conformal set {0, 1} at alpha 0.2         (the pre-specified conformal flag alone)
  D3  D1 OR D2
  D4  D1 AND D2

Populations: grade 4 primary only -- MU intended use (out-of-fold, 5 repeats), LUMIERE (locked), UCSF grade-4 scan 2
pos_s2_pm30 vs primary negatives (locked). Per cohort and rule: share flagged; AUC unflagged vs flagged with the CI of
the difference (S2 metric); retained AUC vs composition-matched random removal (S3 metric); error rate (and Brier) at
the cohort-median threshold by flag status.

Nothing in prism/analyses/system.py is changed. The cohorts are rebuilt with the same functions (MU needs all 5 CV
repeats; the records carry repeat 0 only), checked against the published AUCs and against the flags written in
records_<cohort>.jsonl, and evaluate_set is called with the original five flags first and D3 / D4 appended, so the
random streams for D1 / D2 are those of the S2 / S3 run and their rows must equal selective.csv (checked).

    PYTHONPATH=. OMP_NUM_THREADS=1 .venv/bin/python scripts/exploratory_reduced_flags.py [--workers 6]
    -> outputs/results/analyses/system/exploratory_reduced_flags/   (aggregate numbers only)
"""

from __future__ import annotations

import argparse
import json
import time
import warnings

import numpy as np
import pandas as pd

from prism.analyses import reliability_card as RC
from prism.analyses import system as S

OUT = S.OUT / "exploratory_reduced_flags"
STATUS = "EXPLORATORY: reduced confidence design, specified after S1-S4 had been seen"
RULES = {"D1_disagree": "pathways disagree", "D2_conformal": "combined conformal set {0, 1} (alpha 0.2)",
         "D3_disagree_or_conformal": "disagree OR conformal {0, 1}",
         "D4_disagree_and_conformal": "disagree AND conformal {0, 1}"}
SETS = [("mu", "intended_use", "records_mu"), ("lumiere", "all", "records_lumiere"),
        ("ucsf", "scan2_pm30", "records_ucsf")]


def add_rules(c: dict) -> dict:
    f = c["flags"]
    f["D3_disagree_or_conformal"] = f["disagree"] | f["conformal"]
    f["D4_disagree_and_conformal"] = f["disagree"] & f["conformal"]
    return c


def check_against_records(c: dict, name: str) -> dict:
    """Repeat-0 flags of the rebuilt cohort must equal the flags in the written records."""
    rec = {}
    with open(S.OUT / f"{name}.jsonl") as fh:
        for line in fh:
            r = json.loads(line)
            rec[r["scan_id"]] = r["flags"]
    d = np.array([rec[s]["pathways_disagree"] for s in c["scan_id"]])
    k = np.array([rec[s]["conformal_uncertain"] for s in c["scan_id"]])
    return {"check": f"{name}: rebuilt repeat-0 disagree / conformal flags == records",
            "value": int((d != c["flags"]["disagree"][0]).sum() + (k != c["flags"]["conformal"][0]).sum()),
            "published": 0, "ok": bool((d == c["flags"]["disagree"][0]).all() and (k == c["flags"]["conformal"][0]).all())}


def check_aucs(c: dict, setname: str) -> list[dict]:
    m = c["eval"][setname]
    y = c["y"][m].astype(int)
    rows = []
    for p in S.PW:
        key = {"mu": ("mu", "grade4", "intended_use", p), "lumiere": ("lumiere", "grade4", "all", p),
               "ucsf": ("ucsf", "grade4", "scan2", p)}[c["cohort"]]
        if key in S.EXPECTED:
            v = S.auc_m(y, c["S"][f"p_{p}"][:, m], np.ones((c["S"][f"p_{p}"].shape[0], m.sum()), bool))
            rows.append({"check": "|".join(key), "value": v, "published": S.EXPECTED[key],
                         "ok": abs(v - S.EXPECTED[key]) < 0.0006})
    return rows


def error_by_flag(c: dict, setname: str, flags: list[str], n_boot: int) -> list[dict]:
    """Error rate and Brier at the cohort-median threshold (as S4) by flag status, with the same patient resamples
    as system.boot_job (draw i: first call of rng([SEED, i]))."""
    m = c["eval"][setname]
    y, g = c["y"][m].astype(int), c["patient_id"][m]
    P = c["S"]["p_combined"][:, m]
    err = ((P > np.median(P, axis=1, keepdims=True)).astype(int) != y).astype(float)
    brier = (P - y) ** 2
    F = {f: np.asarray(c["flags"][f])[:, m] for f in flags}
    by = {p: np.where(g == p)[0] for p in np.unique(g)}
    pats = np.array(sorted(by))

    def stats(idx):
        out = {}
        for f, M in F.items():
            Mi, e, b = M[:, idx], err[:, idx], brier[:, idx]
            out[f] = tuple(float(x[sel].mean()) if sel.any() else np.nan
                           for sel in (Mi, ~Mi) for x in (e, b))
        return out  # (err flagged, brier flagged, err unflagged, brier unflagged)

    point = stats(np.arange(len(y)))
    B = []
    for i in range(n_boot):
        rng = np.random.default_rng([S.SEED, i])
        B.append(stats(np.concatenate([by[p] for p in rng.choice(pats, len(pats))])))
    rows = []
    for f in flags:
        M = F[f]
        ef, bf, eu, bu = point[f]
        dr = np.array([b[f] for b in B])
        rows.append({"cohort": c["cohort"], "set": setname, "flag": f, "flagged_share": float(M.mean()),
                     "error_flagged": ef, "error_flagged_lo": S.ci(dr[:, 0])[0], "error_flagged_hi": S.ci(dr[:, 0])[1],
                     "error_unflagged": eu, "error_unflagged_lo": S.ci(dr[:, 2])[0],
                     "error_unflagged_hi": S.ci(dr[:, 2])[1], "error_diff_flagged_minus_unflagged": ef - eu,
                     "error_diff_lo": S.ci(dr[:, 0] - dr[:, 2])[0], "error_diff_hi": S.ci(dr[:, 0] - dr[:, 2])[1],
                     "brier_flagged": bf, "brier_unflagged": bu,
                     "pos_rate_flagged": float(np.mean([y[mm].mean() for mm in M if mm.any()])),
                     "pos_rate_unflagged": float(np.mean([y[~mm].mean() for mm in M if (~mm).any()]))})
    return rows


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--n-boot", type=int, default=S.N_BOOT)
    a = ap.parse_args(argv)
    warnings.filterwarnings("ignore")
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    cohorts = {"mu": S.mu_cohort("grade4", a.workers), "lumiere": S.lumiere_cohort(), "ucsf": S.ucsf_cohort()}
    print(f"cohorts {time.time() - t0:.0f}s", flush=True)
    table, _ = RC.load_table()
    checks = []
    for k, setname, name in SETS:
        c = add_rules(S.derive(cohorts[k], table))
        checks += check_aucs(c, setname)
        checks.append(check_against_records(c, name))
    ch = pd.DataFrame(checks)
    print(ch.to_string(index=False), flush=True)
    assert ch.ok.all(), "rebuilt cohorts do not reproduce the system records; stopping"

    published = pd.read_csv(S.OUT / "selective.csv")
    sel, err = [], []
    for k, setname, _ in SETS:
        c = cohorts[k]
        res = S.evaluate_set(c, setname, a.workers, a.n_boot, S.N_REF, S.N_DRAW)
        rows = pd.DataFrame(res["selective"])
        # D1 / D2 must reproduce the pre-specified S2 / S3 rows exactly (same seeds, same order of random draws)
        pub = published[(published.cohort == k) & (published.population == "grade4") & (published.set == setname)]
        for orig in ("disagree", "conformal"):
            a_, b_ = rows[rows.flag == orig].iloc[0], pub[pub.flag == orig].iloc[0]
            dev = max(abs(float(a_[x]) - float(b_[x])) for x in ("flagged_share", "S2_diff", "S2_lo", "S2_hi",
                                                                   "S3_diff", "S3_lo", "S3_hi"))
            checks.append({"check": f"{k}|{orig}: S2 / S3 row == selective.csv (max dev)", "value": dev,
                           "published": 0.0, "ok": dev < 1e-9})
        rows = rows[rows.flag.isin(["disagree", "conformal", *RULES])].copy()
        rows["flag"] = rows.flag.replace({"disagree": "D1_disagree", "conformal": "D2_conformal"})
        sel.append(rows)
        c["flags"]["D1_disagree"], c["flags"]["D2_conformal"] = c["flags"]["disagree"], c["flags"]["conformal"]
        err += error_by_flag(c, setname, list(RULES), a.n_boot)
        print(f"evaluated {k} {time.time() - t0:.0f}s", flush=True)
    ch = pd.DataFrame(checks)
    ch.to_csv(OUT / "checks.csv", index=False)
    assert ch.ok.all(), ch[~ch.ok]
    sel = pd.concat(sel)
    sel.insert(0, "status", STATUS)
    sel["rule"] = sel.flag.map(RULES)
    sel.to_csv(OUT / "selective.csv", index=False)
    err = pd.DataFrame(err)
    err.insert(0, "status", STATUS)
    err.to_csv(OUT / "error_by_flag.csv", index=False)
    pd.set_option("display.width", 250)
    print(sel[["cohort", "flag", "flagged_share", "auc_unflagged", "auc_flagged", "S2_diff", "S2_lo", "S2_hi",
               "auc_composition_matched", "S3_diff", "S3_lo", "S3_hi", "min_unflagged_pos_neg",
               "min_flagged_pos_neg"]].round(3).to_string(index=False))
    print(err.drop(columns=["status", "set"]).round(3).to_string(index=False))
    (OUT / "run_info.json").write_text(json.dumps({"status": STATUS, "n_boot": a.n_boot, "n_ref": S.N_REF,
                                                   "n_draw": S.N_DRAW, "seed": S.SEED, "rules": RULES,
                                                   "seconds": round(time.time() - t0)}, indent=1))


if __name__ == "__main__":
    main()
