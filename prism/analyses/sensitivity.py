"""Label / horizon / population sensitivity of the primary comparison (C3: ridge baseline vs baseline + radiomics,
nested choice over all 70 radiomics configurations).

Sensitivities (each changes one thing relative to the primary: grade 4, verified 120-d label, IPCW AUC(120 d)):
  h90 / h180      horizon 90 / 180 d (label_H, AUC(H))
  composite       event = progression or death (label_120_composite; event/time_to_event_composite)
  altdate         the other progression-date field (label_120_altdate; time from progression_day_alt); the 5 grade-4
                  scans whose alternative date is on/before the scan are dropped
  imgfu           non-progressor follow-up from MRIs only (label_120_imgfu; censoring time = imaging follow-up)
  all_glioma      all gliomas instead of grade 4
  excl_post_rt    scans in the 12-week post-RT window removed (early_post_rt == 1; unknown RT end kept)

Folds: outputs/data/folds.csv (stratified on the primary 120-d status) for every sensitivity; subsets keep each
patient's fold. The c3 pipeline (prism.experiments.c3_radiomics.fit_predict / inner_auc) is reused unchanged; the
sensitivity label is written into the label_{H} / event / time_to_event columns it and metrics.py read.
Headline = mean over repeats of per-repeat pooled-OOF IPCW AUC; ΔAUC with a paired patient-cluster bootstrap.

    python -m prism.analyses.sensitivity [--workers 48 --n-boot 1000 --only h90,composite]
    -> $PRISM_OUTPUTS/results/analyses/sensitivity/{summary.csv, nested_choices.csv, oof_repeats.csv.gz, forest.png}
"""

from __future__ import annotations

import argparse
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

from prism.config import RESULTS
from prism.experiments import c3_radiomics as c3
from prism.models.metrics import counted_warnings, evaluate_repeated

OUT = RESULTS / "analyses" / "sensitivity"
# name -> (population, horizon, label variant, label for tables)
SENS = {
    "primary": ("grade4", 120, "", "Primary: grade 4, 120 d"),
    "h90": ("grade4", 90, "", "Horizon 90 d"),
    "h180": ("grade4", 180, "", "Horizon 180 d"),
    "composite": ("grade4", 120, "composite", "Composite (progression or death)"),
    "altdate": ("grade4", 120, "altdate", "Alternative progression date"),
    "imgfu": ("grade4", 120, "imgfu", "Imaging-only follow-up"),
    "all_glioma": ("all_glioma", 120, "", "All gliomas"),
    "excl_post_rt": ("grade4", 120, "excl_post_rt", "Excluding 12-wk post-RT scans"),
}
_CACHE = {}


def prepare(name):
    """(cohort, folds, base, rad, er, H) with the sensitivity outcome in label_H / event / time_to_event."""
    if name in _CACHE:
        return _CACHE[name]
    population, H, variant, _ = SENS[name]
    cohort, folds, base, rad, er = c3.load(population)
    cohort = cohort.copy()
    keep = np.ones(len(cohort), bool)
    t, ev = cohort.time_to_event.to_numpy(float), cohort.event.to_numpy(bool)
    if variant in ("composite", "altdate", "imgfu"):
        cohort[f"label_{H}"] = cohort[f"label_{H}_{variant}"]
    if variant == "composite":
        ev, t = cohort.event_composite.to_numpy(bool), cohort.time_to_event_composite.to_numpy(float)
    elif variant == "altdate":
        t_alt = (cohort.progression_day_alt - cohort.days_from_diagnosis_to_mri).to_numpy(float)
        keep = ~(ev & ~(t_alt > 0))
        t = np.where(ev, t_alt, t)
    elif variant == "imgfu":
        t = np.where(ev, t, np.maximum(cohort.follow_up_imaging_days.to_numpy(float), 0.5))
    elif variant == "excl_post_rt":
        keep = ~cohort.early_post_rt.eq(1).to_numpy()
    cohort["event"], cohort["time_to_event"] = ev, t
    if variant in ("composite", "altdate"):  # naive label of this outcome (only used for the secondary auc_naive)
        cohort[f"naive_label_{H}"] = (ev & (t <= H)).astype(int)
    # the label columns must agree with the time-to-event pair the IPCW metrics read
    lab = cohort[f"label_{H}"].to_numpy(float)
    assert np.all((lab[keep] == 1) == (ev & (t <= H))[keep]), name
    assert np.all(np.isnan(lab[keep]) == (~ev & (t < H))[keep]), name
    sub = lambda x: x.loc[keep].reset_index(drop=True)
    out = (sub(cohort), folds, sub(base), {k: sub(v) for k, v in rad.items()}, sub(er), H)
    _CACHE[name] = out
    return out


@counted_warnings
def run_fold(job):
    """Baseline ridge and nested radiomics (inner choice over c3.RAD_CONFIGS) for one (repeat, fold)."""
    name, r, k = job
    threadpool_limits(1)
    cohort, folds, base, rad, er, H = prepare(name)
    c3.H = H  # c3 reads its module-level horizon
    f = c3._fold_ids(cohort, folds, r)
    tr, te = np.where(f != k)[0], np.where(f == k)[0]
    t0 = time.time()
    p_base = c3.fit_predict(c3.BASELINES[0], cohort, base, rad, er, tr, te, seed=r)
    scores = {c: c3.inner_auc(c, cohort, base, rad, er, tr) for c in c3.RAD_CONFIGS}
    best = max(scores, key=scores.get)
    p_nest = c3.fit_predict(best, cohort, base, rad, er, tr, te, seed=r)
    return name, r, k, te, p_base, p_nest, "|".join(map(str, best)), scores[best], time.time() - t0


def counts(cohort, H):
    lab = cohort[f"label_{H}"]
    return {"n_scans": len(cohort), "n_patients": cohort.patient_id.nunique(), "n_events": int((lab == 1).sum()),
            "n_verified_neg": int((lab == 0).sum()), "n_censored": int(lab.isna().sum())}


def forest(summary, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    s = summary.iloc[::-1].reset_index(drop=True)
    y = np.arange(len(s))
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(9.5, 0.45 * len(s) + 1.3), sharey=True,
                                 gridspec_kw={"width_ratios": [1, 1], "wspace": 0.08})
    ink, muted = "#1f2328", "#8c959f"
    for ax, col, ref, title in ((a1, "auc_baseline", 0.5, "Baseline AUC(H) [95% CI]"),
                                (a2, "d_auc", 0.0, "ΔAUC, + radiomics (nested) [95% CI]")):
        ax.axvline(ref, color=muted, lw=1, ls="--", zorder=0)
        ax.hlines(y, s[f"{col}_lo"], s[f"{col}_hi"], color=ink, lw=2)
        ax.scatter(s[col], y, s=36, color=ink, zorder=3, marker="s" if col == "d_auc" else "o")
        ax.set_title(title, fontsize=10, loc="left", color=ink)
        ax.grid(axis="x", color="#eaeef2", lw=0.8)
        ax.set_axisbelow(True)
        for sp in ("top", "right", "left"):
            ax.spines[sp].set_visible(False)
        ax.tick_params(axis="y", length=0)
    a1.set_yticks(y, [f"{lab}  (n={n}, ev={e})" for lab, n, e in zip(s.label, s.n_scans, s.n_events)], fontsize=9)
    a1.set_xlim(0.45, 0.9)
    lim = max(0.08, float(np.abs(s[["d_auc_lo", "d_auc_hi"]].to_numpy()).max()) + 0.01)
    a2.set_xlim(-lim, lim)
    a2.set_xticks(np.arange(-0.08, 0.081, 0.04), [f"{v:+.2f}" if v else "0" for v in np.arange(-0.08, 0.081, 0.04)])
    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="prism.analyses.sensitivity", description=__doc__)
    ap.add_argument("--workers", type=int, default=48)
    ap.add_argument("--n-boot", type=int, default=1000)
    ap.add_argument("--only", default=None, help="comma-separated subset of " + ",".join(SENS))
    a = ap.parse_args(argv)
    names = a.only.split(",") if a.only else list(SENS)
    OUT.mkdir(parents=True, exist_ok=True)
    n_rep = c3.load_folds().repeat.nunique()
    jobs = [(n, r, k) for n in names for r in range(n_rep) for k in range(5)]
    t0 = time.time()
    with ProcessPoolExecutor(a.workers) as ex:
        res = list(ex.map(run_fold, jobs))
    print(f"fits done in {time.time() - t0:.0f} s (max job {max(x[-1] for x in res):.0f} s)", flush=True)

    rows, choices, oof_cols = [], [], {}
    for n in names:
        cohort, _, _, _, _, H = prepare(n)
        P = {"baseline": np.full((n_rep, len(cohort)), np.nan), "nested": np.full((n_rep, len(cohort)), np.nan)}
        for name, r, k, te, pb, pn, ch, sc, _ in res:
            if name == n:
                P["baseline"][r, te], P["nested"][r, te] = pb, pn
                choices.append({"sensitivity": n, "repeat": r, "fold": k, "chosen": ch, "inner_auc": sc})
        assert not np.isnan(P["baseline"]).any() and not np.isnan(P["nested"]).any()
        ev = evaluate_repeated(cohort, P, H, reference="baseline", n_boot=a.n_boot)
        b, m = ev.loc["baseline"], ev.loc["nested"]
        rows.append({"sensitivity": n, "label": SENS[n][3], "population": SENS[n][0], "horizon": H, **counts(cohort, H),
                     "auc_baseline": b.auc_ipcw, "auc_baseline_lo": b.auc_ipcw_lo, "auc_baseline_hi": b.auc_ipcw_hi,
                     "auc_nested": m.auc_ipcw, "auc_nested_lo": m.auc_ipcw_lo, "auc_nested_hi": m.auc_ipcw_hi,
                     "d_auc": m["d_auc_ipcw_vs_baseline"], "d_auc_lo": m.d_auc_ipcw_lo, "d_auc_hi": m.d_auc_ipcw_hi,
                     "d_auc_p_le0": m.d_auc_ipcw_p_le0, "auc_baseline_repeat_sd": b.auc_ipcw_repeat_sd,
                     "cal_slope_baseline": b.cal_slope, "cal_slope_nested": m.cal_slope,
                     "d_brier": m.d_brier_ipcw, "d_brier_lo": m.d_brier_ipcw_lo, "d_brier_hi": m.d_brier_ipcw_hi,
                     "n_boot_ok": int(m.n_boot_ok)})
        for k, o in P.items():
            for r in range(n_rep):
                oof_cols[(n, k, r)] = pd.Series(o[r], index=cohort.scan_id)
    summary = pd.DataFrame(rows)
    summary.to_csv(OUT / "summary.csv", index=False)
    pd.DataFrame(choices).to_csv(OUT / "nested_choices.csv", index=False)
    pd.DataFrame({f"{n}|{k}#r{r}": s for (n, k, r), s in oof_cols.items()}).rename_axis("scan_id").reset_index(
    ).to_csv(OUT / "oof_repeats.csv.gz", index=False)
    forest(summary, OUT / "forest.png")
    cols = ["sensitivity", "n_scans", "n_patients", "n_events", "n_censored", "auc_baseline", "auc_baseline_lo",
            "auc_baseline_hi", "auc_nested", "d_auc", "d_auc_lo", "d_auc_hi"]
    print(summary[cols].round(3).to_string(index=False))
    print(f"total {time.time() - t0:.0f} s -> {OUT}")


if __name__ == "__main__":
    main()
