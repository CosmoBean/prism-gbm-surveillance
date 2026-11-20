"""Headline AUCs with CIs before and after adopting A and B (docs/results/ADOPT_AB.md), each with the same
bootstrap the paper used for that cohort, so old and new are directly comparable.

  MU       detection.evaluate_set: 1,000 patient draws, seed 20261021, intended use (as DETECTION_TASK.md)
  LUMIERE  detection.bootstrap as detection.lumiere_locked: 1,000 draws, seed 20261021
  UCSF     detection.bootstrap as ucsf_external.evaluate: 1,000 draws, seed 20261025, scan 2, pos_s2_pm30 vs primary

Old scores are read from the pre-adoption backup (outputs/results/analyses/_pre_AB_2026-11-19/reliability_card) and
the published files; their AUCs and CIs must reproduce the published ones (asserted). New scores come from
prism.analyses.system (A: within-window score; B: probability). Also writes the conformal coverage old -> new from the
system's conformal.csv and the backup.

    PRISM_SKIP_UCSF=0 PYTHONPATH=. .venv/bin/python -m prism.analyses.adopt_ab
    -> outputs/results/analyses/adopt_ab/   (aggregate CSVs only)
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from prism.analyses import detection as D
from prism.config import RESULTS

OUT = RESULTS / "analyses" / "adopt_ab"
PRE = RESULTS / "analyses" / "_pre_AB_2026-11-19"
# published (DETECTION_TASK.md, NUMBERS.md 3-4, UCSF_RESULTS.md Part A): arm -> (auc, lo, hi)
PUBLISHED = {("mu", "imaging_old"): (0.709, 0.630, 0.781), ("mu", "combined_old"): (0.821, 0.744, 0.894),
             ("mu", "clinical_history"): (0.822, 0.749, 0.902),
             ("lumiere", "combined_old"): (0.773, 0.679, 0.857), ("lumiere", "imaging_old_T_img_all"): (0.655, 0.565, 0.733),
             ("lumiere", "clinical_history"): (0.689, 0.600, 0.805),
             ("ucsf", "imaging_old"): (0.726, 0.603, 0.835), ("ucsf", "combined_old"): (0.856, 0.758, 0.930),
             ("ucsf", "clinical_history"): (0.561, 0.420, 0.687)}


def _rows(cohort, pt, dr, extra=None):
    out = []
    for a in sorted({k[0] for k in pt}):
        lo, hi = D.ci(dr[(a, "all")])
        out.append({"cohort": cohort, "arm": a, "auc": pt[(a, "all")], "auc_lo": lo, "auc_hi": hi, **(extra or {})})
    return out


def mu():
    from prism.analyses import system as S
    d, _ = S.mu_designs("grade4")
    sid, o = S.mu_oof("grade4", ("images", "combined", "images_prob"))
    assert (sid == d.scan_id.to_numpy()).all()
    old = pd.read_csv(PRE / "reliability_card" / "mu_scores.csv.gz").set_index("scan_id").reindex(d.scan_id)
    pub = pd.read_csv(D.OUT / "oof_grade4_primary.csv.gz").set_index("scan_id").reindex(d.scan_id)
    mat = lambda df, a: np.stack([df[f"{a}#r{r}"].to_numpy() for r in range(5)])
    oofs = {"clinical_history": mat(pub, "B1"), "imaging_old": mat(old, "I_pure"),
            "combined_old": mat(old, "B1+I_pure"), "imaging_A": o["images"], "combined_B": o["combined"],
            "imaging_A_probability": o["images_prob"]}
    rows = np.where(D.eval_sets(d, "primary")["intended_use"])[0]
    res, con, _ = D.evaluate_set("grade4|intended_use", d, rows, oofs, 1000,
                                 contrasts=[("imaging_A", "imaging_old"), ("combined_B", "combined_old")])
    out = [{"cohort": "mu", "arm": r["arm"], "auc": r["auc"], "auc_lo": r["auc_lo"], "auc_hi": r["auc_hi"],
            "n_scans": r["n_scans"], "n_pos": r["n_pos"]} for r in res]
    return out, [{"cohort": "mu", **{k: c[k] for k in ("subset", "contrast", "diff", "diff_lo", "diff_hi")}}
                 for c in con]


def lumiere():
    from prism.analyses import system as S
    c = S.lumiere_cohort()
    L = c["d"]
    old = pd.read_csv(PRE / "reliability_card" / "scans_lumiere.csv.gz").set_index("scan_id").reindex(L.scan_id)
    pub = pd.read_csv(D.OUT / "lumiere_predictions.csv").set_index("scan_id").reindex(L.scan_id)
    preds = {"clinical_history": c["S"]["p_timeline"], "combined_old": pub["T@grade4"].to_numpy()[None, :],
             "imaging_old_T_img_all": old["images#r0"].to_numpy()[None, :],
             "imaging_A": c["S"]["p_images"], "imaging_A_T_img_all": c["check_t_img_all"][None, :],
             "combined_B": c["S"]["p_combined"], "imaging_A_probability": c["S"]["prob_images"]}
    y, g = L.label_det.to_numpy(), L.patient_id.to_numpy()
    sub = {"with_previous": L.prev_scan_id.ne("").to_numpy(), "early_post_rt_flag0": L.early_post_rt.eq(0).to_numpy()}
    pt, dr = D.bootstrap(y, preds, g, 1000, 20261021, subsets=sub)
    return _rows("lumiere", pt, dr, {"n_scans": len(y), "n_pos": int(y.sum())})


def ucsf():
    from prism.analyses import system as S
    from prism.analyses import ucsf_external as UX
    c = S.ucsf_cohort()
    m = c["eval"]["scan2_pm30"]
    pub = pd.read_csv(RESULTS / "analyses" / "ucsf" / "locked" / "scores.csv").set_index("scan_id").reindex(
        c["scan_id"])
    preds = {"clinical_history": c["S"]["p_timeline"][0], "imaging_old": pub["A-Ipure@grade4"].to_numpy(),
             "combined_old": pub["A-T@grade4"].to_numpy(), "imaging_A": c["S"]["p_images"][0],
             "combined_B": c["S"]["p_combined"][0], "imaging_A_probability": c["S"]["prob_images"][0]}
    y, g = c["y"][m].astype(int), c["patient_id"][m]
    pt, dr = D.bootstrap(y, {a: p[None, m] for a, p in preds.items()}, g, 1000, UX.SEED)
    return _rows("ucsf", pt, dr, {"n_scans": len(y), "n_pos": int(y.sum())})


def coverage():
    rows = []
    for tag, p in (("old", PRE / "system" / "conformal.csv"), ("new", RESULTS / "analyses" / "system" / "conformal.csv")):
        t = pd.read_csv(p)
        t = t[t.kind.eq("standard") & t.population.eq("grade4")]
        for r in t.itertuples():
            rows.append({"version": tag, "cohort": r.cohort, "pathway": r.pathway, "alpha": r.alpha,
                         "coverage": r.coverage, "coverage_lo": r.coverage_lo, "coverage_hi": r.coverage_hi,
                         "coverage_events": r.coverage_events, "coverage_non_events": r.coverage_non_events,
                         "singleton_rate": r.singleton_rate, "both_rate": r.both_rate, "empty_rate": r.empty_rate})
    t = pd.DataFrame(rows)
    return t.pivot_table(index=["cohort", "pathway", "alpha"], columns="version",
                         values=["coverage", "coverage_lo", "coverage_hi", "coverage_events", "coverage_non_events",
                                 "singleton_rate", "both_rate"]).reset_index()


def main():
    import warnings
    from prism.config import SKIP_UCSF
    warnings.filterwarnings("ignore")
    OUT.mkdir(parents=True, exist_ok=True)
    r_mu, con = mu()
    rows = r_mu + lumiere() + ([] if SKIP_UCSF else ucsf())
    t = pd.DataFrame(rows)
    chk = []
    for (co, a), (v, lo, hi) in PUBLISHED.items():
        if co == "ucsf" and SKIP_UCSF:
            continue
        r = t[(t.cohort == co) & (t.arm == a)].iloc[0]
        ok = abs(r.auc - v) < 0.0006 and abs(r.auc_lo - lo) < 0.0011 and abs(r.auc_hi - hi) < 0.0011
        chk.append({"cohort": co, "arm": a, "published": (v, lo, hi), "reproduced": (r.auc, r.auc_lo, r.auc_hi),
                    "ok": ok})
    ch = pd.DataFrame(chk)
    print(ch.to_string(index=False))
    assert ch.ok.all(), "old AUCs / CIs do not reproduce the published values"
    t.to_csv(OUT / "auc_old_new.csv", index=False)
    pd.DataFrame(con).to_csv(OUT / "mu_paired_new_minus_old.csv", index=False)
    cv = coverage()
    cv.columns = ["_".join(str(x) for x in c if x) for c in cv.columns]
    cv.to_csv(OUT / "conformal_old_new.csv", index=False)
    pd.set_option("display.width", 250)
    print(t.round(3).to_string(index=False))
    print(pd.DataFrame(con).round(3).to_string(index=False))
    print(cv.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
