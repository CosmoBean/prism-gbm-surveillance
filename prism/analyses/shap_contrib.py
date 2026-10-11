"""SHAP contributions of the C3 / external models, computed out-of-fold in log-odds (margin) space.

Models (C3 setup: cohort, verified labels, shared 5x5 folds and in-fold preprocessing of prism.experiments.c3_radiomics)
  base_{ridge,gbm}   clinical + timing + treatment (the headline baseline)
  full_{ridge,gbm}   + volumes + morphology + delta (all non-radiomics groups; same imputer + scaler as the baseline)
  rad_ridge          baseline + radiomics, the C3 configuration chosen most often in nested selection
                     (outputs/results/c3/<population>/nested_choices.csv)
  lumiere_{ridge,gbm} shared clinical + timing + volumes (prism.experiments.external_lumiere): MU out-of-fold SHAP on the
                     shared folds, and the locked all-MU model explained on MU (in-sample) and on LUMIERE

For every fold of every repeat the model is fitted on the training patients and the held-out scans are explained.
Ridge: exact linear SHAP with an independent (interventional) masker, phi_j = beta_j (x_j - mean_train x_j) on the
in-fold standardised features (= shap.LinearExplainer). Boosting: shap.TreeExplainer on the sklearn
HistGradientBoostingClassifier itself (supported natively; additivity checked to 1e-6), tree_path_dependent, i.e. the
training rows enter through the node covers. (shap 0.49 "interventional" mode with these HGB models gives a wrong
expected value and breaks additivity by up to 0.77 logits on some folds, so it is not used.) Both sum to the model's decision function (logit). Group SHAP = per-scan sum of the group's
feature SHAP values (missingness indicators belong to their column's group); mean |group SHAP| is reported with its
share of the sum over groups. Stability: features ranked by mean |SHAP| on each of the 25 held-out folds.

    python -m prism.analyses.shap_contrib [--population grade4 all_glioma] [--workers 32]
    -> $PRISM_OUTPUTS/results/analyses/shap/<population>/{features,groups,imaging_share,model_auc,lumiere_*}.csv, *.png
"""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd
from sklearn.base import clone
from threadpoolctl import threadpool_limits

from prism.config import RESULTS
from prism.models.metrics import counted_warnings, point_metrics, repeated_point_metrics

H = 120
OUT = RESULTS / "analyses" / "shap"
BASE_GROUPS = ("clinical", "timing", "treatment")
FULL_GROUPS = BASE_GROUPS + ("volumes", "morphology", "delta")
IMAGING = ("volumes", "morphology", "delta", "radiomics")
# Time-since-event features outside the timing group (sensitivity for "schedule-coupled" contributions).
TIME_LIKE = ("surgery_day", "rt_start_day", "rt_duration_days", "has_prior", "n_prior_scans", "days_since_prior")
OUTLIER_PHI = 50.0
MAIN = ("base_ridge", "base_gbm", "full_ridge", "full_gbm", "rad_ridge")


def chosen_config(population):
    c = pd.read_csv(RESULTS / "c3" / population / "nested_choices.csv").chosen.value_counts()
    v, s, sel, i, l = c.index[0].split("|")
    return (v, s, sel, i, l), int(c.iloc[0]), int(c.sum())


# ---------------------------------------------------------------- explainers
def linear_shap(model, Xbg, X, ref=None):
    beta = model.coef_[0]
    ref = Xbg.mean(0) if ref is None else ref
    return (X - ref) * beta, float(model.intercept_[0] + ref @ beta)


def tree_shap(model, Xbg, X):
    import shap
    e = shap.TreeExplainer(model, feature_perturbation="tree_path_dependent", model_output="raw")
    s = np.asarray(e.shap_values(X, check_additivity=False)).reshape(len(X), -1)
    ev = float(np.ravel(e.expected_value)[0])
    err = np.abs(s.sum(1) + ev - model.decision_function(X)).max()
    assert err < 1e-6, f"TreeSHAP additivity error {err}"
    return s, ev


def explain(learner, model, Xbg, X, ref=None):
    s, ev = linear_shap(model, Xbg, X, ref) if learner == "ridge" else tree_shap(model, Xbg, X)
    if learner == "ridge":
        assert np.abs(s.sum(1) + ev - model.decision_function(X)).max() < 1e-8
    return s, ev


# ---------------------------------------------------------------- MU design matrices (mirror c3.fit_predict)
def _mu_context(population):
    from prism.experiments import c3_radiomics as c3
    from prism.features.tabular import groups as feature_groups
    cohort, folds, base, rad, er = c3.load(population)
    g = feature_groups(cohort)
    col_group = {c: k for k, x in g.items() if k != "radiomics" for c in x.columns}
    full = pd.concat([g[k] for k in FULL_GROUPS], axis=1)
    return cohort, folds, base, full, rad, er, col_group


def design(model_name, ctx, cfg, tr, te, seed):
    """(Xtr_known, ytr, Xte, names, learner). Same steps as c3.fit_predict for the baseline / chosen radiomics config."""
    from prism.experiments import c3_radiomics as c3
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import GroupKFold
    cohort, folds, base, full, rad, er, _ = ctx
    y = cohort[f"label_{H}"].to_numpy()
    tr = tr[~np.isnan(y[tr])]
    B = full if model_name.startswith("full") else base
    bp = clone(c3.BASE_PRE).fit(B.iloc[tr])
    Btr, Bte, names = bp.transform(B.iloc[tr]), bp.transform(B.iloc[te]), list(bp.get_feature_names_out())
    learner = model_name.split("_")[-1]
    if model_name.startswith("rad"):
        variant, stab, sel, integ, learner = cfg
        R = rad[variant]
        cols = list(R.columns)
        if stab == "icc":
            shared = [c for c in cols if c in er.columns]
            icc = c3.icc_consistency(R.loc[R.index[tr], shared].to_numpy(float), er.loc[er.index[tr], shared].to_numpy(float))
            cols = [c for c in cols if c not in {c for c, v in zip(shared, icc) if not (v >= c3.ICC_MIN)}]
        Rtr, Rte = R.iloc[tr][cols].to_numpy(float), R.iloc[te][cols].to_numpy(float)
        if integ == "concat":
            sp = clone(c3.selector(sel)).fit(Rtr, y[tr].astype(int))
            Str, Ste = sp.transform(Rtr), sp.transform(Rte)
            names += [f"radiomics_{sel}_{j + 1}" for j in range(Str.shape[1])]
            Btr, Bte = np.hstack([Btr, Str]), np.hstack([Bte, Ste])
        else:
            score_tr = np.zeros(len(tr))
            for a, b in GroupKFold(n_splits=4).split(tr, groups=cohort.patient_id.iloc[tr]):
                sp = clone(c3.selector(sel)).fit(Rtr[a], y[tr][a].astype(int))
                m = LogisticRegression(C=0.1, max_iter=5000).fit(sp.transform(Rtr[a]), y[tr][a].astype(int))
                score_tr[b] = m.decision_function(sp.transform(Rtr[b]))
            sp = clone(c3.selector(sel)).fit(Rtr, y[tr].astype(int))
            m = LogisticRegression(C=0.1, max_iter=5000).fit(sp.transform(Rtr), y[tr].astype(int))
            Btr = np.hstack([Btr, score_tr[:, None]])
            Bte = np.hstack([Bte, m.decision_function(sp.transform(Rte))[:, None]])
            names.append("radiomics_score")
    return tr, Btr, y[tr].astype(int), Bte, names, learner


def fit_model(learner, Xtr, cohort, tr, ytr, seed):
    from prism.experiments import c3_radiomics as c3
    if learner == "ridge":
        return c3._ridge(Xtr, cohort, tr, seed)
    return clone(c3.GBM).set_params(random_state=seed).fit(Xtr, ytr)


@counted_warnings
def run_mu(job):
    population, model_name, r = job
    threadpool_limits(1)
    from prism.experiments import c3_radiomics as c3
    ctx = _mu_context(population)
    cohort, folds = ctx[0], ctx[1]
    cfg = chosen_config(population)[0] if model_name.startswith("rad") else None
    f = c3._fold_ids(cohort, folds, r)
    rows, xs, names = [], [], None
    for k in np.unique(f):
        tr, te = np.where(f != k)[0], np.where(f == k)[0]
        trk, Xtr, ytr, Xte, names, learner = design(model_name, ctx, cfg, tr, te, r)
        model = fit_model(learner, Xtr, cohort, trk, ytr, r)
        ref, extra = None, {}
        if names[-1] == "radiomics_score":
            # The stacked score has extreme inner-OOF training values (legacy ngtdm Coarseness = 1e6 sentinel, see
            # SHAP.md), so the training mean is a useless reference: use the training median for this column.
            ref = Xtr.mean(0)
            ref[-1] = np.median(Xtr[:, -1])
            extra = {"phi_score_meanref": (Xte[:, -1] - Xtr[:, -1].mean()) * model.coef_[0][-1],
                     "score_train_maxabs": np.abs(Xtr[:, -1]).max()}
        s, ev = explain(learner, model, Xtr, Xte, ref)
        rows.append(pd.DataFrame(s, columns=names).assign(repeat=r, fold=k, row=te, base_value=ev,
                                                          pred=model.predict_proba(Xte)[:, 1], **extra))
        xs.append(pd.DataFrame(Xte, columns=names).assign(row=te))
    return population, model_name, pd.concat(rows, ignore_index=True), pd.concat(xs, ignore_index=True)


@counted_warnings
def run_lumiere(job):
    """MU OOF SHAP on the shared MU folds, then the locked all-MU model on MU and LUMIERE; also the 25 MU-CV fold
    models applied to LUMIERE (rank stability of the LUMIERE profile)."""
    population, learner = job
    threadpool_limits(1)
    from prism.experiments import external_lumiere as ex
    cols = ex.FEATURE_SETS["clinical+timing+volumes"]
    lc, LX = ex.lumiere_table()
    mc, MX = ex.mu_table(population == "grade4")
    ids = ex.mu_fold_ids(mc)
    y = mc[f"label_{H}"].to_numpy()
    out = {"mu_oof": [], "lumiere_folds": []}

    def parts(rows, seed):
        _, pre, model = ex.fit(learner, MX[cols].iloc[rows], mc.iloc[rows].reset_index(drop=True), seed=seed,
                               return_parts=True)
        k = rows[~np.isnan(y[rows])]
        return pre, model, pre.transform(MX[cols].iloc[k])
    names = None
    for r, f in enumerate(ids):
        for fk in np.unique(f):
            tr, te = np.where(f != fk)[0], np.where(f == fk)[0]
            pre, model, Xbg = parts(tr, r)
            names = list(pre.get_feature_names_out())
            for key, Z, rws in (("mu_oof", MX[cols].iloc[te], te), ("lumiere_folds", LX[cols], np.arange(len(lc)))):
                s, ev = explain(learner, model, Xbg, pre.transform(Z))
                out[key].append(pd.DataFrame(s, columns=names).assign(repeat=r, fold=fk, row=rws, base_value=ev))
    pre, model, Xbg = parts(np.arange(len(mc)), 0)
    for key, Z in (("locked_mu", MX[cols]), ("locked_lumiere", LX[cols])):
        Xz = pre.transform(Z)
        s, ev = explain(learner, model, Xbg, Xz)
        out[key] = [pd.DataFrame(s, columns=names).assign(repeat=0, fold=0, row=np.arange(len(Z)), base_value=ev,
                                                          pred=model.predict_proba(Xz)[:, 1])]
    zs = pd.DataFrame({"feature": names, "mu_mean_z": Xbg.mean(0), "lumiere_mean_z": pre.transform(LX[cols]).mean(0),
                       "lumiere_missing_frac": [LX[c].isna().mean() if c in LX else np.nan for c in names]})
    return population, learner, {k: pd.concat(v, ignore_index=True) for k, v in out.items()}, zs


# ---------------------------------------------------------------- aggregation
META = ("repeat", "fold", "row", "base_value", "pred", "phi_score_meanref", "score_train_maxabs")


def feat_cols(S):
    return [c for c in S.columns if c not in META]


def group_of(name, col_group):
    c = name.removeprefix("missingindicator_")
    if c.startswith("radiomics"):
        return "radiomics"
    return col_group.get(c, "other")


def summarise(S, col_group, model):
    F = feat_cols(S)
    A = S[F].abs()
    per_fit = A.groupby([S.repeat, S.fold]).mean()
    ranks = per_fit.rank(axis=1, ascending=False)
    feats = pd.DataFrame({"model": model, "feature": F, "group": [group_of(c, col_group) for c in F],
                          "mean_abs_shap": A.mean().to_numpy(),
                          "median_abs_shap": A.median().to_numpy(), "mean_shap": S[F].mean().to_numpy(),
                          "rank_median": ranks.median().to_numpy(), "rank_q25": ranks.quantile(.25).to_numpy(),
                          "rank_q75": ranks.quantile(.75).to_numpy(), "rank_sd": ranks.std().to_numpy(),
                          "top5_frac": (ranks <= 5).mean().to_numpy(), "n_fits": len(per_fit)})
    feats["share"] = feats.mean_abs_shap / feats.mean_abs_shap.sum()
    feats = feats.sort_values("mean_abs_shap", ascending=False)
    feats.insert(2, "rank", np.arange(1, len(feats) + 1))
    gmap = dict(zip(feats.feature, feats.group))
    G = S[F].T.groupby(lambda c: gmap[c]).sum().T  # per-scan group SHAP
    Gabs = G.abs()
    gfit = Gabs.groupby([S.repeat, S.fold]).mean()
    gshare_fit = gfit.div(gfit.sum(1), axis=0)
    granks = gfit.rank(axis=1, ascending=False)
    groups = pd.DataFrame({"model": model, "group": G.columns, "mean_abs_group_shap": Gabs.mean().to_numpy(),
                           "mean_group_shap": G.mean().to_numpy(),
                           "sum_feature_mean_abs": [feats.loc[feats.group == g, "mean_abs_shap"].sum() for g in G.columns],
                           "share_sd_over_fits": gshare_fit.std().to_numpy(), "rank_median": granks.median().to_numpy(),
                           "rank_min": granks.min().to_numpy(), "rank_max": granks.max().to_numpy(),
                           "n_features": [int((feats.group == g).sum()) for g in G.columns]})
    groups["share"] = groups.mean_abs_group_shap / groups.mean_abs_group_shap.sum()
    groups["share_of_feature_sum"] = groups.sum_feature_mean_abs / groups.sum_feature_mean_abs.sum()
    return feats, groups.sort_values("mean_abs_group_shap", ascending=False), G


def imaging_share(S, G, feats, model):
    """Imaging vs non-imaging share of |block SHAP| (per-scan sum within block), also with the time-like delta
    features (has_prior, n_prior_scans, days_since_prior) counted as non-imaging; timing-group and time-like shares."""
    F = feat_cols(S)
    grp = feats.set_index("feature").group
    timelike = [c for c in F if grp[c] == "timing" or c.removeprefix("missingindicator_") in TIME_LIKE]
    img_strict = [c for c in F if grp[c] in IMAGING and c.removeprefix("missingindicator_") not in TIME_LIKE]
    block = lambda cols, f="mean": getattr(S[cols].sum(1).abs(), f)() if cols else 0.0
    img, non = block([c for c in F if grp[c] in IMAGING]), block([c for c in F if grp[c] not in IMAGING])
    img_m, non_m = (block([c for c in F if grp[c] in IMAGING], "median"),
                    block([c for c in F if grp[c] not in IMAGING], "median"))
    img2, non2 = block(img_strict), block([c for c in F if c not in img_strict])
    return {"model": model, "imaging_mean_abs": img, "nonimaging_mean_abs": non, "imaging_share": img / (img + non),
            "imaging_share_median": img_m / (img_m + non_m),
            "imaging_share_timelike_as_nonimaging": img2 / (img2 + non2),
            "timing_group_share": float(G["timing"].abs().mean() / G.abs().mean().sum()),
            "timing_top_feature_rank": int(feats[feats.group == "timing"]["rank"].min()),
            "timelike_share_of_feature_sum": float(feats[feats.feature.isin(timelike)].share.sum())}


def per_scan_mean(S):
    """One explanation per scan: average of its 5 out-of-fold explanations (one per repeat)."""
    F = feat_cols(S)
    return S.groupby("row")[F].mean()


# ---------------------------------------------------------------- plots
C_POS, C_NEG = "#eb6834", "#2a78d6"


def raw_values(names, raw, Z):
    """Raw feature values for plotting (indicator -> 0/1; features without a raw column, e.g. the stacked radiomics
    score, use their in-fold design value averaged over repeats)."""
    out = {}
    for c in names:
        b = c.removeprefix("missingindicator_")
        out[c] = raw[b].isna().astype(float) if c != b else raw[c] if c in raw else Z[c]
    return pd.DataFrame(out)


def plot_model(S, X, raw, feats, groups, title, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import shap
    M = per_scan_mean(S)
    Z = X.groupby("row").mean().reindex(M.index)
    V = raw_values(M.columns, raw.iloc[M.index].set_axis(M.index), Z)
    top = feats.feature.head(15).tolist()
    plt.figure()
    shap.summary_plot(M[top].to_numpy(), V[top].to_numpy(), feature_names=top, show=False, max_display=15,
                      plot_size=(8, 6))
    plt.title(f"{title}\nSHAP (log-odds), per scan mean over 5 OOF repeats", fontsize=9)
    plt.tight_layout(); plt.savefig(f"{path}_beeswarm.png", dpi=150); plt.close()

    fig, axes = plt.subplots(1, 2, figsize=(12, 5.5), gridspec_kw={"width_ratios": [3, 2]})
    f = feats.head(15)[::-1]
    axes[0].barh(f.feature, f.mean_abs_shap, color=C_NEG, height=0.6)
    for i, (v, rm, q1, q3) in enumerate(zip(f.mean_abs_shap, f.rank_median, f.rank_q25, f.rank_q75)):
        axes[0].text(v, i, f"  rank {rm:.0f} [{q1:.0f}-{q3:.0f}]", va="center", fontsize=7, color="#555")
    axes[0].set_xlabel("mean |SHAP| (log-odds); text = median rank [IQR] over 25 fits")
    axes[0].set_xlim(0, f.mean_abs_shap.max() * 1.45)
    g = groups[::-1]
    axes[1].barh(g.group, g.mean_abs_group_shap, xerr=None, color=C_POS, height=0.6)
    for i, (v, s, sd) in enumerate(zip(g.mean_abs_group_shap, g.share, g.share_sd_over_fits)):
        axes[1].text(v, i, f"  {100 * s:.0f}% (SD {100 * sd:.0f})", va="center", fontsize=8, color="#555")
    axes[1].set_xlim(0, g.mean_abs_group_shap.max() * 1.5)
    axes[1].set_xlabel("mean |group SHAP| (sum within group); share of total")
    for ax in axes:
        ax.spines[["top", "right"]].set_visible(False); ax.tick_params(labelsize=8); ax.grid(axis="x", alpha=.25)
    fig.suptitle(title, fontsize=11)
    fig.tight_layout(); fig.savefig(f"{path}_bar.png", dpi=150); plt.close(fig)

    fig, axes = plt.subplots(1, 4, figsize=(16, 3.8))
    for ax, c in zip(axes, feats.feature.head(4)):
        x, s = V[c], M[c]
        ok = x.notna()
        ax.scatter(x[ok], s[ok], s=10, alpha=.6, color=C_NEG, linewidths=0)
        if (~ok).any():
            ax.scatter(np.full((~ok).sum(), np.nanmin(x) if ok.any() else 0), s[~ok], s=12, marker="x", color=C_POS,
                       label=f"missing (n={(~ok).sum()}, imputed)")
            ax.legend(fontsize=7, frameon=False)
        ax.axhline(0, color="#999", lw=.8)
        ax.set_xlabel(f"{c} (raw value)", fontsize=8); ax.set_ylabel("SHAP (log-odds)", fontsize=8)
        ax.spines[["top", "right"]].set_visible(False); ax.tick_params(labelsize=7)
    fig.suptitle(f"{title}: dependence of the top 4 features", fontsize=10)
    fig.tight_layout(); fig.savefig(f"{path}_dependence.png", dpi=150); plt.close(fig)


def plot_lumiere(prof, title, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    p = prof.sort_values("locked_mu_mean_abs")
    y = np.arange(len(p))
    fig, axes = plt.subplots(1, 2, figsize=(12, 5), sharey=True)
    for ax, (a, b, lab) in zip(axes, [("locked_mu_mean_abs", "locked_lumiere_mean_abs", "mean |SHAP| (log-odds)"),
                                      ("locked_mu_mean", "locked_lumiere_mean", "mean signed SHAP (log-odds)")]):
        ax.barh(y + .2, p[a], height=.38, color=C_NEG, label="MU (locked model, in-sample)")
        ax.barh(y - .2, p[b], height=.38, color=C_POS, label="LUMIERE (locked model)")
        ax.set_xlabel(lab, fontsize=9); ax.axvline(0, color="#999", lw=.8)
        ax.spines[["top", "right"]].set_visible(False); ax.tick_params(labelsize=8); ax.grid(axis="x", alpha=.25)
    axes[0].set_yticks(y, p.feature); axes[0].legend(fontsize=8, frameon=False, loc="lower right")
    fig.suptitle(title, fontsize=11)
    fig.tight_layout(); fig.savefig(path, dpi=150); plt.close(fig)


# ---------------------------------------------------------------- main
def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="prism shap", description=__doc__)
    ap.add_argument("--population", nargs="+", default=["grade4", "all_glioma"])
    ap.add_argument("--workers", type=int, default=32)
    a = ap.parse_args(argv)
    from prism.experiments import external_lumiere as ex
    mu_jobs = [(p, m, r) for p in a.population for m in MAIN for r in range(5)]
    lu_jobs = [(p, l) for p in a.population for l in ("ridge", "gbm")]
    with ProcessPoolExecutor(a.workers) as pool:
        lu_res = pool.map(run_lumiere, lu_jobs)
        mu_res = list(pool.map(run_mu, mu_jobs))
        lu_res = list(lu_res)
    for p in a.population:
        out = OUT / p
        out.mkdir(parents=True, exist_ok=True)
        cohort, folds, base, full, rad, er, col_group = _mu_context(p)
        cfg, n_chosen, n_total = chosen_config(p)
        raw = full.reset_index(drop=True)
        F, Gs, I, A, trimmed = [], [], [], [], []
        for m in MAIN:
            S = pd.concat([s for pp, mm, s, _ in mu_res if pp == p and mm == m], ignore_index=True)
            X = pd.concat([x for pp, mm, _, x in mu_res if pp == p and mm == m], ignore_index=True)
            S.to_csv(out / f"shap_{m}.csv.gz", index=False)
            oof = np.zeros((5, len(cohort)))
            oof[S.repeat.to_numpy(), S.row.to_numpy()] = S.pred.to_numpy()
            ref = pd.read_csv(RESULTS / "c3" / p / "oof_repeats.csv.gz")
            key = {"base_ridge": "None|none|none|none|ridge", "base_gbm": "None|none|none|none|gbm",
                   "rad_ridge": "|".join(cfg)}.get(m)
            dev = np.abs(ref[[f"{key}#r{r}" for r in range(5)]].to_numpy().T - oof).max() if key else np.nan
            A.append({"model": m, "config": "|".join(cfg) if m == "rad_ridge" else "", **repeated_point_metrics(cohort, oof, H),
                      "max_abs_diff_vs_c3_oof": dev})
            title = {"base_ridge": "Baseline ridge", "base_gbm": "Baseline boosting", "full_ridge": "Full non-radiomics ridge",
                     "full_gbm": "Full non-radiomics boosting",
                     "rad_ridge": f"Baseline + radiomics ({'|'.join(cfg[:4])}; chosen {n_chosen}/{n_total})"}[m]
            variants = [(m, S)]
            if "radiomics_score" in S:  # degenerate explanations of the sentinel-outlier scans (|phi| ~ 1e5) dropped
                keep = S.radiomics_score.abs() <= OUTLIER_PHI
                variants.append((f"{m}_trim", S[keep]))
                trimmed.append({"model": m, "rows_dropped": int((~keep).sum()), "rows": len(S),
                                "scans_dropped": ";".join(sorted(cohort.scan_id.iloc[S.row[~keep].unique()])),
                                "fits_with_outlier_score_in_training": int((S.groupby(["repeat", "fold"]).score_train_maxabs
                                                                            .first() > OUTLIER_PHI).sum()),
                                "fits_with_median_abs_score_phi_below_0.01": int((S[keep].groupby(["repeat", "fold"])
                                                                                  .radiomics_score.apply(lambda v: v.abs().median()) < 0.01).sum())})
            for name, Sv in variants:
                feats, groups, G = summarise(Sv, col_group, name)
                F.append(feats); Gs.append(groups); I.append(imaging_share(Sv, G, feats, name))
            plot_model(Sv, X, raw, feats, groups, f"{title} — {p}" + (" (outlier rows dropped)" if Sv is not S else ""),
                       out / m)
        pd.concat(F).to_csv(out / "features.csv", index=False)
        pd.concat(Gs).to_csv(out / "groups.csv", index=False)
        pd.DataFrame(I).to_csv(out / "imaging_share.csv", index=False)
        pd.DataFrame(A).to_csv(out / "model_auc.csv", index=False)
        pd.DataFrame(trimmed).to_csv(out / "radiomics_outliers.csv", index=False)

        lc, LX = ex.lumiere_table()
        mc, MX = ex.mu_table(p == "grade4")
        shared_group = {c: g for g, cs in ex.SHARED.items() for c in cs}
        LP, LG, LA = [], [], []
        locked_ref = pd.read_csv(RESULTS / "external_lumiere" / "locked_predictions.csv")
        for pp, learner, res, zs in lu_res:
            if pp != p:
                continue
            m = f"lumiere_{learner}"
            prof = []
            for key, S in res.items():
                S.to_csv(out / f"shap_{m}_{key}.csv.gz", index=False)
                f, g, _ = summarise(S, shared_group, m) if key in ("mu_oof", "lumiere_folds") else (None, None, None)
                Fk = feat_cols(S)
                d = pd.DataFrame({"feature": Fk, f"{key}_mean_abs": S[Fk].abs().mean().to_numpy(),
                                  f"{key}_mean": S[Fk].mean().to_numpy()}).set_index("feature")
                if f is not None:
                    d[f"{key}_rank_median"] = f.set_index("feature").rank_median
                    d[f"{key}_rank_sd"] = f.set_index("feature").rank_sd
                    LG.append(g.assign(source=key))
                prof.append(d)
                Gk = S[Fk].T.groupby(lambda c: group_of(c, shared_group)).sum().T
                if key.startswith("locked"):
                    LG.append(pd.DataFrame({"model": m, "group": Gk.columns, "mean_abs_group_shap": Gk.abs().mean().to_numpy(),
                                            "mean_group_shap": Gk.mean().to_numpy(),
                                            "share": (Gk.abs().mean() / Gk.abs().mean().sum()).to_numpy(), "source": key}))
            prof = pd.concat(prof, axis=1).reset_index().merge(zs, on="feature")
            prof.insert(0, "model", m)
            prof["group"] = [group_of(c, shared_group) for c in prof.feature]
            LP.append(prof)
            Lk = res["locked_lumiere"]
            pred = Lk.pred.to_numpy()
            refcol = f"{p}|clinical+timing+volumes|{learner}"
            LA.append({"model": m, "lumiere_locked_auc_pooled": point_metrics(lc, pred, H)["auc_ipcw"],
                       "max_abs_diff_vs_locked_predictions": float(np.abs(locked_ref[refcol] - pred).max()),
                       "lumiere_mean_pred": pred.mean(), "mu_mean_pred": res["locked_mu"].pred.mean(),
                       "base_value": float(Lk.base_value.iloc[0]),
                       "lumiere_mean_logit_shift": float(Lk[feat_cols(Lk)].sum(1).mean()),
                       "mu_mean_logit_shift": float(res["locked_mu"][feat_cols(Lk)].sum(1).mean())})
            plot_lumiere(prof, f"Locked {learner} (clinical + timing + volumes, trained on MU {p}): MU vs LUMIERE",
                         out / f"{m}_mu_vs_lumiere.png")
        pd.concat(LP).to_csv(out / "lumiere_features.csv", index=False)
        pd.concat(LG).to_csv(out / "lumiere_groups.csv", index=False)
        pd.DataFrame(LA).to_csv(out / "lumiere_check.csv", index=False)
        print(f"== {p}")
        print(pd.DataFrame(A).round(4).to_string(index=False))
        print(pd.DataFrame(I).round(3).to_string(index=False))
        print(pd.DataFrame(trimmed).to_string(index=False))
        for m in MAIN + ("rad_ridge_trim",):
            print(m, pd.concat(Gs).query("model == @m")[["group", "mean_abs_group_shap", "share", "share_sd_over_fits",
                                                          "rank_median"]].round(3).to_string(index=False), sep="\n")
            print(pd.concat(F).query("model == @m").head(8)[["feature", "group", "mean_abs_shap", "share", "rank_median",
                                                            "rank_q25", "rank_q75", "top5_frac"]].round(3).to_string(index=False))
        print(pd.DataFrame(LA).round(3).to_string(index=False))
        for d in LP:
            print(d[["model", "feature", "mu_oof_mean_abs", "locked_mu_mean_abs", "locked_lumiere_mean_abs",
                     "locked_mu_mean", "locked_lumiere_mean", "lumiere_mean_z", "lumiere_missing_frac"]].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
