"""Christodoulou 2026 setting (single-scan 4-sequence radiomics, LightGBM + Optuna, Platt) on the MU detection task.

ANALYSIS PLAN: docs/results/CHRISTODOULOU_REPLICATION.md, section "Plan (pre-specified, 2026-10-25)", written before
any run; snapshotted to outputs/results/analyses/christodoulou/PLAN_snapshot.md by the first run.

Label / rows / folds: prism.analyses.detection (positives = progression scans, training negatives = primary negatives).
CH   v2 radiomics (all 4 sequences, 2316 columns) -> 256 by |univariate AUC - 0.5| on the training rows -> LightGBM,
     Optuna TPE (40 trials, inner 5-fold patient-grouped stratified CV, selection redone per inner fold) -> Platt on
     the best trial's inner cross-fitted logits; final model refitted on all training rows.
References on the same rows and folds: B1 (timeline + clinical), I_scan, I_pure (ridge, as in DETECTION_TASK.md).
Evaluation: (1) shared 5 x 5 folds, plain AUC + patient bootstrap, Brier raw vs Platt; (2) 100 random single
patient hold-outs (20%, grade 4); (3) intended use and within phase (detection.eval_sets / evaluate_set);
(4) EXPLORATORY locked model on UCSF grade-4 scan 2 (--ucsf; radiomics extracted with the MU code).

    PYTHONPATH=. .venv/bin/python -m prism.analyses.christodoulou_replication [--workers 10] [--n-boot 1000] [--ucsf]
    -> $PRISM_OUTPUTS/results/analyses/christodoulou/
"""

from __future__ import annotations

import argparse
import json
import time
import warnings
from concurrent.futures import ProcessPoolExecutor
from functools import lru_cache

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedGroupKFold

from prism.analyses import detection as D
from prism.config import REPO, RESULTS

OUT = RESULTS / "analyses" / "christodoulou"
K_FEATURES, N_TRIALS, N_INNER, MAX_MISSING = 256, 40, 5, 0.2
N_SPLITS, TEST_FRAC = 100, 0.2
ARMS = ("CH", "B1", "I_scan", "I_pure")
CONTRASTS = [("CH", "B1"), ("CH", "I_scan"), ("CH", "I_pure"), ("I_pure", "B1")]
_logit = lambda p: np.log(np.clip(p, 1e-6, 1 - 1e-6) / (1 - np.clip(p, 1e-6, 1 - 1e-6)))


# ---------------------------------------------------------------- data
@lru_cache(maxsize=4)
def data(pop: str):
    """(detection frame, label with NaN outside training rows, radiomics matrix, ridge designs B1 / I_scan / I_pure)."""
    from prism.analyses.triage_feasibility import _features_one
    from prism.features.tabular import measurement_groups
    _, _, _, meas = D._base()
    d, X, rad, _, F = D.context(pop, "primary")
    R = rad["v2_all4"].drop(columns="scan_id", errors="ignore").astype(float)
    assert R.shape[1] == 2316 and not R.columns.str.contains("log-sigma|wavelet").any()
    mg = measurement_groups(d)
    by_pat = {p: g.sort_values("mri_day") for p, g in meas.groupby("patient_id")}
    nad = []
    for pid, day in zip(d.patient_id, d.mri_day):
        g = by_pat[pid]
        f = _features_one(g[g.mri_day <= day], day, -np.inf)
        nad.append({"nadir_all_et": f["traj_logratio_nadir_et"], "nadir_all_lesion": f["traj_logratio_nadir_lesion"]})
    nad = pd.DataFrame(nad, index=d.index)
    prevr = F[[c for c in F.columns if c.startswith("logratio_prev_")]]
    iscan = pd.concat([mg["volumes"], mg["morphology"]], axis=1)
    ridge = {"B1": X["B1"], "I_scan": iscan, "I_pure": pd.concat([iscan, prevr, nad], axis=1)}
    return d, d.label_120.to_numpy(), R, ridge


# ---------------------------------------------------------------- the CH pipeline
def select(R: np.ndarray, y: np.ndarray, k=K_FEATURES) -> np.ndarray:
    """Column indices: <= 20% missing, non-constant, top k by |AUC - 0.5| (all on the rows given)."""
    ok = (np.isnan(R).mean(0) <= MAX_MISSING) & (np.nanstd(R, 0) > 0)
    score = np.full(R.shape[1], -1.0)
    for j in np.where(ok)[0]:
        m = ~np.isnan(R[:, j])
        if (y[m] == 1).any() and (y[m] == 0).any():
            score[j] = abs(roc_auc_score(y[m], R[m, j]) - 0.5)
    return np.argsort(-score, kind="stable")[: min(k, int((score >= 0).sum()))]


def lgbm(params, seed):
    from lightgbm import LGBMClassifier
    return LGBMClassifier(**params, subsample_freq=1, random_state=seed, n_jobs=1, verbose=-1)


def fit_ch(R: np.ndarray, y: np.ndarray, groups: np.ndarray, tr: np.ndarray, te: np.ndarray, seed: int, keep=False):
    """Train on labelled rows of tr; return (raw test prob, Platt test prob, best params, best inner AUC[, objects])."""
    import optuna
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    tr = tr[~np.isnan(y[tr])]
    Rt, yt = R[tr], y[tr].astype(int)
    inner = list(StratifiedGroupKFold(N_INNER, shuffle=True, random_state=seed).split(Rt, yt, groups[tr]))
    sel = [select(Rt[a], yt[a]) for a, _ in inner]  # selection depends on the inner split only, not on the trial
    oofs = {}

    def objective(trial):
        p = {"num_leaves": trial.suggest_int("num_leaves", 4, 31), "max_depth": trial.suggest_int("max_depth", 2, 6),
             "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.2, log=True),
             "n_estimators": trial.suggest_int("n_estimators", 50, 500),
             "min_child_samples": trial.suggest_int("min_child_samples", 5, 40),
             "subsample": trial.suggest_float("subsample", 0.5, 1.0),
             "colsample_bytree": trial.suggest_float("colsample_bytree", 0.2, 1.0),
             "reg_lambda": trial.suggest_float("reg_lambda", 1e-3, 10, log=True)}
        oof, aucs = np.full(len(tr), np.nan), []
        for (a, b), cols in zip(inner, sel):
            oof[b] = lgbm(p, seed).fit(Rt[a][:, cols], yt[a]).predict_proba(Rt[b][:, cols])[:, 1]
            aucs.append(roc_auc_score(yt[b], oof[b]))
        oofs[trial.number] = oof
        return float(np.mean(aucs))

    st = optuna.create_study(direction="maximize", sampler=optuna.samplers.TPESampler(seed=seed))
    st.optimize(objective, n_trials=N_TRIALS)
    best = st.best_params
    platt = LogisticRegression(C=1e6).fit(_logit(oofs[st.best_trial.number])[:, None], yt)
    cols = select(Rt, yt)
    model = lgbm(best, seed).fit(Rt[:, cols], yt)
    raw = model.predict_proba(R[te][:, cols])[:, 1]
    out = (raw, platt.predict_proba(_logit(raw)[:, None])[:, 1], best, float(st.best_value))
    return out + ({"model": model, "cols": cols, "platt": platt},) if keep else out


def job(j):
    from threadpoolctl import threadpool_limits
    threadpool_limits(1)
    warnings.filterwarnings("ignore")
    kind, pop, a, b = j
    d, y, R, ridge = data(pop)
    Rv, g = R.to_numpy(), d.patient_id.to_numpy()
    if kind == "cv":  # a = repeat, b = fold
        f = D.fold_ids(d, a)
        tr, te = np.where(f != b)[0], np.where(f == b)[0]
        return j, te, *fit_ch(Rv, y, g, tr, te, seed=a)
    if kind == "split":  # a = split seed; test = 20% of the patients with a training-label row
        from prism.experiments import c3_radiomics as c3
        pats = np.unique(g[~np.isnan(y)])
        test_p = np.random.default_rng(a).choice(pats, int(round(TEST_FRAC * len(pats))), replace=False)
        te_m = np.isin(g, test_p) & ~np.isnan(y)
        tr, te = np.where(~np.isin(g, test_p))[0], np.where(te_m)[0]
        raw, cal, best, inner = fit_ch(Rv, y, g, tr, te, seed=a)
        b1 = c3.fit_predict(c3.BASELINES[0], d, ridge["B1"], {}, None, tr, te, seed=a)
        return j, te, raw, cal, best, inner, b1
    if kind == "lock":  # all labelled rows
        tr = np.arange(len(d))
        return j, None, *fit_ch(Rv, y, g, tr, tr[:1], seed=0, keep=True)


# ---------------------------------------------------------------- evaluation helpers
def brier(y, p):
    return float(np.mean((p - y) ** 2))


def brier_boot(y, P_raw, P_cal, groups, n_boot, seed=20261025):
    """Mean over repeats of Brier (raw, Platt, difference) with a patient-cluster bootstrap."""
    stat = lambda ii: [np.mean([brier(y[ii], P[r, ii]) for r in range(len(P))]) for P in (P_raw, P_cal)]
    pt = stat(np.arange(len(y)))
    by = {p: np.where(groups == p)[0] for p in np.unique(groups)}
    pats, rng = np.array(list(by)), np.random.default_rng(seed)
    dr = np.array([stat(np.concatenate([by[p] for p in rng.choice(pats, len(pats))])) for _ in range(n_boot)])
    q = lambda x: np.percentile(x, [2.5, 97.5])
    return {"brier_raw": pt[0], "brier_raw_lo": q(dr[:, 0])[0], "brier_raw_hi": q(dr[:, 0])[1],
            "brier_platt": pt[1], "brier_platt_lo": q(dr[:, 1])[0], "brier_platt_hi": q(dr[:, 1])[1],
            "platt_minus_raw": pt[1] - pt[0], "diff_lo": q(dr[:, 1] - dr[:, 0])[0],
            "diff_hi": q(dr[:, 1] - dr[:, 0])[1], "prevalence": float(y.mean())}


def ridge_oofs(pop):
    from prism.experiments import c3_radiomics as c3
    d, _, _, ridge = data(pop)
    out = {a: np.full((5, len(d)), np.nan) for a in ridge}
    for a, Xa in ridge.items():
        for r in range(5):
            f = D.fold_ids(d, r)
            for k in range(5):
                tr, te = np.where(f != k)[0], np.where(f == k)[0]
                out[a][r, te] = c3.fit_predict(c3.BASELINES[0], d, Xa, {}, None, tr, te, seed=r)
    return out


# ---------------------------------------------------------------- (4) EXPLORATORY: UCSF
def ucsf_radiomics(workers):
    """MU radiomics code (extract_scan) on UCSF grade-4 scan 2 (patched paths; same normalisation and settings)."""
    from prism.analyses.ucsf_external import ucsf_frame
    path = OUT / "ucsf_radiomics_scan2.csv"
    u = ucsf_frame()
    u = u[u.timepoint.eq(2) & u.grade4]
    if path.exists():
        return pd.read_csv(path, dtype={"scan_id": str})
    jobs = [(str(s), 2) for s in u.subject_id]
    with ProcessPoolExecutor(workers) as ex:
        rows = list(ex.map(_ucsf_one, jobs, chunksize=1))
    out = pd.DataFrame(rows)
    out.to_csv(path, index=False)
    return out


def _ucsf_one(args):
    from prism.features import radiomics as rf
    from prism.features.ucsf_imaging import ucsf_paths
    rf.mu_scan_paths = ucsf_paths
    full, _ = rf.extract_scan(args)
    full["scan_id"] = f"{args[0]}_time{args[1]}"
    return full


def run_ucsf(workers, n_boot):
    from prism.analyses.ucsf_external import detection_sets
    t0 = time.time()
    from prism.analyses.ucsf_external import ucsf_frame
    feats = ucsf_radiomics(workers)
    print(f"UCSF radiomics {time.time() - t0:.0f}s, {len(feats)} scans", flush=True)
    u = ucsf_frame().reset_index(drop=True)
    import pickle
    lock = pickle.loads((OUT / "locked_model.pkl").read_bytes())
    Ru = feats.set_index("scan_id").reindex(u.scan_id).reindex(columns=lock["columns"]).to_numpy(float)
    raw = lock["model"].predict_proba(Ru[:, lock["cols"]])[:, 1]
    cal = lock["platt"].predict_proba(_logit(raw)[:, None])[:, 1]
    res = []
    for name, _pop, rows, lab, _ in detection_sets(u):
        if not name.startswith(("grade4|scan2|pm30", "grade4|scan2|et_inc")):
            continue
        m = rows & ~np.isnan(Ru).all(1)
        yy, gg = lab[m], u.patient_id.to_numpy()[m]
        pt, dr = D.bootstrap(yy, {"CH": raw[m][None]}, gg, n_boot, seed=20261025)
        lo, hi = D.ci(dr[("CH", "all")])
        res.append({"set": name, "n_pos": int(yy.sum()), "n_neg": int((yy == 0).sum()), "auc": pt[("CH", "all")],
                    "auc_lo": lo, "auc_hi": hi, "brier_raw": brier(yy, raw[m]), "brier_platt": brier(yy, cal[m]),
                    "n_missing_radiomics": int((rows & np.isnan(Ru).all(1)).sum())})
    res = pd.DataFrame(res)
    res.to_csv(OUT / "ucsf_locked.csv", index=False)
    print(res.round(3).to_string(index=False))


# ---------------------------------------------------------------- main
def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workers", type=int, default=10)
    ap.add_argument("--n-boot", type=int, default=1000)
    ap.add_argument("--ucsf", action="store_true", help="only the EXPLORATORY UCSF step (needs the locked model)")
    a = ap.parse_args(argv)
    warnings.filterwarnings("ignore")
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    pd.set_option("display.width", 250)
    if a.ucsf:
        run_ucsf(a.workers, a.n_boot)
        return
    snap = OUT / "PLAN_snapshot.md"
    if not snap.exists():
        from prism.audit.provenance import git_state
        doc = (REPO / "docs" / "results" / "CHRISTODOULOU_REPLICATION.md").read_text()
        plan = doc.split("## Plan (pre-specified", 1)[1].split("\n## ", 1)[0]
        snap.write_text(f"# PLAN snapshot ({time.strftime('%Y-%m-%dT%H:%M:%S')}, git {git_state()['commit'][:10]})\n\n"
                        "## Plan (pre-specified" + plan)
    pops = ("grade4", "all_glioma")
    jobs = ([("lock", "grade4", 0, 0)] + [("cv", p, r, k) for p in pops for r in range(5) for k in range(5)]
            + [("split", "grade4", s, 0) for s in range(N_SPLITS)])
    with ProcessPoolExecutor(a.workers) as ex:
        results = list(ex.map(job, jobs, chunksize=1))
    print(f"fits {time.time() - t0:.0f}s", flush=True)

    # locked model (fitted once on all grade-4 training rows; for --ucsf)
    import pickle
    (_, _, _, _, best, inner, obj), = [x for x in results if x[0][0] == "lock"]
    R4 = data("grade4")[2]
    (OUT / "locked_model.pkl").write_bytes(pickle.dumps({**obj, "columns": list(R4.columns), "params": best}))
    (OUT / "locked_params.json").write_text(json.dumps({"params": best, "inner_auc": inner,
                                                        "features": [R4.columns[c] for c in obj["cols"]]}, indent=1))

    T = {"auc": [], "contrasts": [], "within_phase": [], "brier": []}
    params = []
    for pop in pops:
        d, y, _, _ = data(pop)
        raw, cal = np.full((5, len(d)), np.nan), np.full((5, len(d)), np.nan)
        for (kind, p, r, k), te, pr, pc, best, inner in [x for x in results if x[0][0] == "cv"]:
            if p == pop:
                raw[r, te], cal[r, te] = pr, pc
                params.append({"population": pop, "repeat": r, "fold": k, "inner_auc": inner, **best})
        assert np.isfinite(raw).all() and np.isfinite(cal).all()
        oofs = {"CH": cal, **ridge_oofs(pop)}
        saved = pd.read_csv(D.OUT / f"oof_{pop}_primary.csv.gz")
        assert (saved.scan_id.to_numpy() == d.scan_id.to_numpy()).all()
        dev = np.nanmax(np.abs(saved[[f"B1#r{r}" for r in range(5)]].to_numpy().T - oofs["B1"]))
        assert dev < 1e-9, f"B1 differs from the detection run ({dev})"
        pd.DataFrame({**{f"{a}#r{r}": o[r] for a, o in oofs.items() for r in range(5)},
                      **{f"CHraw#r{r}": raw[r] for r in range(5)}, "scan_id": d.scan_id}).to_csv(
            OUT / f"oof_{pop}.csv.gz", index=False)
        for name, rows in D.eval_sets(d, "primary").items():
            rows = np.where(rows)[0]
            r_, c_, w_ = D.evaluate_set(f"{pop}|{name}", d, rows, oofs, a.n_boot, contrasts=CONTRASTS)
            T["auc"] += r_
            T["contrasts"] += c_
            T["within_phase"] += w_
            yy = d.label_det.to_numpy()[rows]
            T["brier"].append({"set": f"{pop}|{name}", "n_pos": int(yy.sum()), "n_neg": int((yy == 0).sum()),
                               **brier_boot(yy, raw[:, rows], cal[:, rows], d.patient_id.to_numpy()[rows],
                                            a.n_boot)})
        print(f"{pop} evaluated {time.time() - t0:.0f}s", flush=True)
    for k, v in T.items():
        pd.DataFrame(v).to_csv(OUT / f"{k}.csv", index=False)
    pd.DataFrame(params).to_csv(OUT / "cv_params.csv", index=False)

    # (2) 100 single splits
    d, y, _, _ = data("grade4")
    iu = d.intended_use.to_numpy()
    sp = []
    for (kind, p, s, _), te, raw, cal, best, inner, b1 in [x for x in results if x[0][0] == "split"]:
        yy, m = y[te].astype(int), iu[te]
        ok = 0 < yy.sum() < len(yy)
        okm = 0 < yy[m].sum() < m.sum()
        sp.append({"seed": s, "n_test_patients": int(d.patient_id.iloc[te].nunique()), "n_test_scans": len(te),
                   "n_pos": int(yy.sum()), "inner_auc": inner,
                   "auc_CH": roc_auc_score(yy, raw) if ok else np.nan, "auc_B1": roc_auc_score(yy, b1) if ok else np.nan,
                   "auc_CH_intended_use": roc_auc_score(yy[m], raw[m]) if okm else np.nan,
                   "auc_B1_intended_use": roc_auc_score(yy[m], b1[m]) if okm else np.nan,
                   "brier_raw": brier(yy, raw), "brier_platt": brier(yy, cal)})
    sp = pd.DataFrame(sp)
    sp.to_csv(OUT / "splits.csv", index=False)
    summ = []
    for c in [c for c in sp.columns if c.startswith(("auc_", "brier_"))]:
        x = sp[c].dropna()
        summ.append({"metric": c, "n_splits": len(x), "mean": x.mean(), "sd": x.std(), "p2.5": x.quantile(.025),
                     "p97.5": x.quantile(.975), "min": x.min(), "max": x.max(), "share_ge_0.80": (x >= 0.80).mean()})
    summ = pd.DataFrame(summ)
    summ.to_csv(OUT / "splits_summary.csv", index=False)
    (OUT / "run_info.json").write_text(json.dumps({"argv": vars(a), "seconds": round(time.time() - t0),
                                                   "k_features": K_FEATURES, "n_trials": N_TRIALS,
                                                   "n_inner": N_INNER, "n_splits": N_SPLITS}, indent=1))
    auc, con = pd.DataFrame(T["auc"]), pd.DataFrame(T["contrasts"])
    print(auc.round(3).to_string(index=False))
    print(con.round(3).to_string(index=False))
    print(pd.DataFrame(T["within_phase"]).query("phase in ['later_post_rt', 'phase_stratified']").round(3)
          .to_string(index=False))
    print(pd.DataFrame(T["brier"]).round(4).to_string(index=False))
    print(summ.round(3).to_string(index=False))
    print(f"total {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
