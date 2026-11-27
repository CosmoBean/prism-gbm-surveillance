"""What each group of inputs contributes to PRISM's scores at MU (exploratory, 2026-11-26).

Two measures, both in the paper's 5 x 5 patient-grouped cross validation and on the 146 intended-use scans:
  1. leave one group out: refit without the group in the same folds; paired AUC difference (full minus reduced),
     95% CI from 2,000 bootstrap samples of patients, AUC averaged over the five repeats in each sample;
  2. share of the score: for each held-out scan, each group's part of the linear score is the sum over its inputs
     (and their missing-value indicators) of weight x standardised value; its share is |part| / sum of |parts|.
     Shares are averaged over the five repeats, then summarised by the median over scans.

Run from the repo root: PYTHONPATH=. python scripts/prism_feature_contributions.py [workers]
Outputs: outputs/results/analyses/feature_contributions/{logo.csv, shares.csv, scan_shares.csv}
"""
import sys, warnings, numpy as np, pandas as pd
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
from sklearn.base import clone
from sklearn.metrics import roc_auc_score
warnings.filterwarnings("ignore")
from prism.analyses import christodoulou_replication as CR
from prism.analyses import detection as D
from prism.experiments import c3_radiomics as c3

GROUPS = {
    "Patient characteristics": ["age", "male", "idh_mutant", "mgmt_methylated", "biopsy_before_resection",
                                "previous_brain_tumor"],
    "Treatment course and dates": ["days_from_diagnosis", "days_since_rt_end", "rt_date_unknown", "early_post_rt",
                                   "early_post_rt_x_mgmt_methylated", "visit_index", "rt_started", "rt_completed",
                                   "rt_dose_gy", "rt_fractions", "rt_hypofractionated", "rt_start_day",
                                   "rt_duration_days", "chemo_started", "surgery_day"],
    "Volumes": ["log_et_cc", "log_netc_cc", "log_snfh_cc", "log_rc_cc", "log_tumor_cc", "log_lesion_cc"],
    "Composition, shape and position": ["et_fraction_of_tumor", "log_snfh_to_tumor", "has_cavity", "et_n_components",
                                        "et_largest_component_fraction", "log_et_max_axial",
                                        "et_near_cavity_fraction", "et_cavity_distance"],
    "Intensity": ["t1c_et_rel", "t1c_et_p90_rel", "t1c_netc_rel", "flair_snfh_rel", "flair_netc_rel"],
    "Change since earlier scans": ["logratio_prev_et", "logratio_prev_netc", "logratio_prev_snfh", "logratio_prev_rc",
                                   "logratio_prev_tumor", "logratio_prev_lesion", "nadir_all_et", "nadir_all_lesion"],
}
OUT = Path("outputs/results/analyses/feature_contributions")


def designs():
    d, y, _, ridge = CR.data("grade4")
    X = {"history": ridge["B1"], "imaging": ridge["I_pure"],
         "combined": pd.concat([ridge["B1"], ridge["I_pure"]], axis=1)}
    grouped = sum(GROUPS.values(), [])
    for k, Xa in X.items():
        assert set(Xa.columns) <= set(grouped), set(Xa.columns) - set(grouped)
    jobs = {}
    for k, Xa in X.items():
        jobs[(k, "all")] = Xa
        for gname, cols in GROUPS.items():
            if set(cols) & set(Xa.columns) and set(Xa.columns) - set(cols):
                jobs[(k, gname)] = Xa.drop(columns=[c for c in cols if c in Xa.columns])
    return d, jobs


def fit_parts(d, Xa, tr, te, seed):
    """c3.fit_predict for the ridge baseline, also returning each held-out scan's per-group part of the score."""
    y = d[f"label_{c3.H}"].to_numpy()
    tr = tr[~np.isnan(y[tr])]
    bp = clone(c3.BASE_PRE).fit(Xa.iloc[tr])
    Xtr, Xte = bp.transform(Xa.iloc[tr]), bp.transform(Xa.iloc[te])
    model = c3._ridge(Xtr, d, tr, seed)
    cols = list(Xa.columns)
    ind = bp.named_steps["imp"].indicator_
    names = cols + ([cols[j] for j in ind.features_] if ind is not None else [])
    contrib = Xte * model.coef_[0]
    owner = {c: g for g, cs in GROUPS.items() for c in cs}
    parts = pd.DataFrame(contrib, columns=names).T.groupby(lambda c: owner[c]).sum().T
    return model.predict_proba(Xte)[:, 1], parts.to_numpy(), list(parts.columns)


def job(j):
    from threadpoolctl import threadpool_limits
    threadpool_limits(1); warnings.filterwarnings("ignore")
    key, r, k = j
    d, jobs = designs()
    f = D.fold_ids(d, r)
    tr, te = np.where(f != k)[0], np.where(f == k)[0]
    p, parts, gnames = fit_parts(d, jobs[key], tr, te, seed=r)
    ref = c3.fit_predict(c3.BASELINES[0], d, jobs[key], {}, None, tr, te, seed=r)
    assert np.allclose(p, ref), "contribution fit differs from the paper's fit"
    return j, te, p, (parts if key[1] == "all" else None), gnames


def fast_auc(y, s):
    from scipy.stats import rankdata
    r = rankdata(s); n1 = y.sum(); n0 = len(y) - n1
    return (r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)


if __name__ == "__main__":
    d, jobs = designs()
    tasks = [(key, r, k) for key in jobs for r in range(5) for k in range(5)]
    with ProcessPoolExecutor(int(sys.argv[1]) if len(sys.argv) > 1 else 16) as ex:
        res = list(ex.map(job, tasks, chunksize=1))
    ev = D.eval_sets(d, "primary")["intended_use"]
    yl = d.label_det.to_numpy()[ev].astype(int)
    pid = d.patient_id.to_numpy()[ev]
    oof = {key: np.full((5, len(d)), np.nan) for key in jobs}
    parts = {m: {} for m in ("history", "imaging", "combined")}
    for (key, r, k), te, p, pa, gn in res:
        oof[key][r, te] = p
        if pa is not None:
            parts[key[0]].setdefault(r, {}).update({i: dict(zip(gn, row)) for i, row in zip(te, pa)})
    S = {key: oof[key][:, ev] for key in jobs}
    auc = {key: np.mean([fast_auc(yl, S[key][r]) for r in range(5)]) for key in jobs}
    print("full models (should be 0.82 / 0.71 / 0.82):",
          {m: round(auc[(m, "all")], 3) for m in ("combined", "imaging", "history")})

    rng = np.random.default_rng(0)
    pats = np.unique(pid); idx = {p: np.where(pid == p)[0] for p in pats}
    boot = {key: [] for key in jobs}
    for _ in range(2000):
        b = np.concatenate([idx[p] for p in rng.choice(pats, len(pats))])
        if yl[b].min() == yl[b].max():
            continue
        for key in jobs:
            boot[key].append(np.mean([fast_auc(yl[b], S[key][r][b]) for r in range(5)]))
    rows = []
    for (m, g) in jobs:
        if g == "all":
            continue
        diff = np.array(boot[(m, "all")]) - np.array(boot[(m, g)])
        rows.append({"model": m, "group_left_out": g, "auc_full": auc[(m, "all")], "auc_without": auc[(m, g)],
                     "drop": auc[(m, "all")] - auc[(m, g)], "lo": np.quantile(diff, .025),
                     "hi": np.quantile(diff, .975)})
    OUT.mkdir(parents=True, exist_ok=True)
    logo = pd.DataFrame(rows); logo.to_csv(OUT / "logo.csv", index=False)
    print(logo.round(3).to_string(index=False))

    srows, scan_rows = [], []
    evi = np.where(ev)[0]
    for m in parts:
        A = np.stack([pd.DataFrame([parts[m][r][i] for i in evi]).abs().to_numpy() for r in range(5)]).mean(0)
        gn = list(pd.DataFrame([parts[m][0][evi[0]]]).columns)
        share = A / A.sum(1, keepdims=True)
        for j, g in enumerate(gn):
            srows.append({"model": m, "group": g, "median_share": np.median(share[:, j]),
                          "q1": np.quantile(share[:, j], .25), "q3": np.quantile(share[:, j], .75),
                          "median_share_progression": np.median(share[yl == 1, j]),
                          "median_share_no_progression": np.median(share[yl == 0, j])})
        sc = pd.DataFrame(share, columns=gn); sc.insert(0, "model", m)
        sc.insert(1, "scan_id", d.scan_id.to_numpy()[evi]); sc.insert(2, "label", yl)
        scan_rows.append(sc)
    shares = pd.DataFrame(srows); shares.to_csv(OUT / "shares.csv", index=False)
    pd.concat(scan_rows).to_csv(OUT / "scan_shares.csv", index=False)
    print(shares.round(3).to_string(index=False))
