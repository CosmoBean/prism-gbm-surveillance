"""SHAP on the PRISM report split (seed 62) and why that split scores high.

1. PRISM report model as shipped (legacy/radiomics/models/calibrated/model_bundle.pkl): its input matrix is rebuilt
   from the legacy feature JSONs + hybrid_basic clinical codes (prism.analyses.split_variance.legacy_table) and its
   probabilities are checked against test_predictions.csv. The classifier is an L2 logistic regression on the
   standardised features, so the exact linear SHAP (interventional, reference = mean of the 231 PRISM training scans,
   i.e. phi_j = beta_j (x_j - mean_train x_j)) is used in its log-odds. The Platt calibrator is monotone on top of it
   (same ranking); a PermutationExplainer on the calibrated probability (100 sampled training rows) is a check.
2. Our models on the same split (train on the 126 non-test patients, explain the 82 test scans of the all-glioma
   cohort): baseline ridge, baseline boosting, baseline + legacy radiomics top10 concat, fitted exactly as in
   prism.analyses.head_to_head / c3.fit_predict, explained with prism.analyses.shap_contrib (linear / TreeSHAP).
3. Split composition: test set vs full cohort vs the 500 design splits (outputs/results/analyses/split_variance),
   phase-of-care subsets (post-RT AUC with patient-cluster bootstrap CI), Spearman correlation across splits between
   per-split AUC and composition, and the test-set SHAP profile vs the cohort-wide OOF profile
   (outputs/results/analyses/shap/all_glioma).

Phases (as of the scan): pre_rt = RT not started (incl. never irradiated); during_rt = started, not completed;
early_post_rt = <= 12 weeks after RT end; later = > 12 weeks after RT end. post_rt = early_post_rt + later.

    python -m prism.analyses.shap_prism_split [--n-boot 1000]
    -> $PRISM_OUTPUTS/results/analyses/shap_prism_split/
"""

from __future__ import annotations

import argparse
import pickle

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.base import clone
from sklearn.metrics import roc_auc_score

from prism.config import RESULTS
from prism.models.metrics import cluster_bootstrap, counted_warnings, point_metrics

H = 120
OUT = RESULTS / "analyses" / "shap_prism_split"
LEGACY_CFG = ("legacy", "none", "top10", "concat", "ridge")
OURS = {"base_ridge": "Baseline ridge", "base_gbm": "Baseline boosting",
        "rad_ridge": "Baseline + legacy radiomics (top10)"}
PHASES = ("pre_rt", "during_rt", "early_post_rt", "later")
C_POS, C_NEG = "#eb6834", "#2a78d6"


# ---------------------------------------------------------------- helpers
def texture_class(f):
    return next((k for k in ("firstorder", "shape", "glcm", "glrlm", "glszm", "gldm", "ngtdm") if f"_{k}_" in f), "other")


def image_filter(f):
    return "wavelet" if "_wavelet-" in f else "log" if "_log-sigma" in f else "original"


def summarise_flat(S, groups):
    """Feature and group tables for one set of explanations (rows = scans). groups: feature -> group."""
    A = S.abs()
    f = pd.DataFrame({"feature": S.columns, "group": [groups[c] for c in S.columns], "mean_abs_shap": A.mean().values,
                      "mean_shap": S.mean().values}).sort_values("mean_abs_shap", ascending=False)
    f["share"] = f.mean_abs_shap / f.mean_abs_shap.sum()
    f.insert(0, "rank", np.arange(1, len(f) + 1))
    G = S.T.groupby(groups).sum().T
    g = pd.DataFrame({"group": G.columns, "mean_abs_group_shap": G.abs().mean().values, "mean_group_shap": G.mean().values,
                      "sum_feature_mean_abs": [f.loc[f.group == k, "mean_abs_shap"].sum() for k in G.columns],
                      "n_features": [int((f.group == k).sum()) for k in G.columns]})
    g["share"] = g.mean_abs_group_shap / g.mean_abs_group_shap.sum()
    g["share_of_feature_sum"] = g.sum_feature_mean_abs / g.sum_feature_mean_abs.sum()
    return f, g.sort_values("mean_abs_group_shap", ascending=False)


def plot(S, V, feats, groups, title, path, n=15):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import shap
    top = feats.feature.head(n).tolist()
    plt.figure()
    shap.summary_plot(S[top].to_numpy(), V[top].to_numpy(float), feature_names=top, show=False, max_display=n,
                      plot_size=(9, 6))
    plt.title(f"{title}\nSHAP (log-odds) on the 82 test scans of the PRISM report split", fontsize=9)
    plt.tight_layout(); plt.savefig(f"{path}_beeswarm.png", dpi=150); plt.close()
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5), gridspec_kw={"width_ratios": [3, 2]})
    f = feats.head(n)[::-1]
    axes[0].barh(f.feature, f.mean_abs_shap, color=C_NEG, height=0.6)
    axes[0].set_xlabel("mean |SHAP| (log-odds), 82 test scans")
    g = groups[::-1]
    axes[1].barh(g.group, g.mean_abs_group_shap, color=C_POS, height=0.6)
    for i, (v, s) in enumerate(zip(g.mean_abs_group_shap, g.share)):
        axes[1].text(v, i, f"  {100 * s:.0f}%", va="center", fontsize=8, color="#555")
    axes[1].set_xlim(0, g.mean_abs_group_shap.max() * 1.3)
    axes[1].set_xlabel("mean |group SHAP| (per-scan sum within group); share")
    for ax in axes:
        ax.spines[["top", "right"]].set_visible(False); ax.tick_params(labelsize=7); ax.grid(axis="x", alpha=.25)
    fig.suptitle(title, fontsize=11)
    fig.tight_layout(); fig.savefig(f"{path}_bar.png", dpi=150); plt.close(fig)


def boot_auc(y, p, pid, n_boot, seed=0):
    """Naive AUC with a patient-cluster bootstrap 95% CI."""
    rng = np.random.default_rng(seed)
    ids = np.unique(pid)
    rows = {k: np.where(pid == k)[0] for k in ids}
    out = []
    for _ in range(n_boot):
        r = np.concatenate([rows[k] for k in rng.choice(ids, len(ids))])
        if len(np.unique(y[r])) == 2:
            out.append(roc_auc_score(y[r], p[r]))
    return roc_auc_score(y, p), *np.percentile(out, [2.5, 97.5])


def phases(cohort):
    from prism.features.tabular import treatment
    t = treatment(cohort)
    ph = np.where(t.rt_started == 0, "pre_rt", np.where(t.rt_completed == 0, "during_rt",
                  np.where(cohort.early_post_rt == 1, "early_post_rt", "later")))
    return pd.Series(ph, index=cohort.index)


# ---------------------------------------------------------------- 1. shipped model
def shipped(test_pids, tp):
    import shap
    from prism.analyses import split_variance as sv
    surv = sv._surv()
    feats, _, _ = sv.legacy_table()
    b = pickle.load(open(sv.BUNDLE, "rb"))
    st, clf, cal = b["preprocessor_state"], b["classifier"], b["calibrator"]
    X = surv.transform_preprocessor(feats[b["selected_columns"]], st)
    X.index = feats.scan_id
    raw = surv.predict_positive_probability(clf, X)
    p = cal.predict_proba(raw.reshape(-1, 1))[:, 1]
    chk = pd.DataFrame({"raw": raw, "cal": p}, index=X.index).reindex(tp.scan_id)
    check = {"n_rows_test_predictions": len(tp), "max_abs_diff_calibrated": float(np.abs(chk.cal.values - tp.calibrated_probability).max()),
             "max_abs_diff_raw": float(np.abs(chk.raw.values - tp.raw_probability).max()),
             "n_selected_columns": len(b["selected_columns"]), "n_model_columns": X.shape[1],
             "dropped_by_preprocessor": ";".join(sorted(set(b["selected_columns"]) - set(st.keep_columns))),
             "calibrator_coef": float(cal.coef_[0, 0]), "calibrator_intercept": float(cal.intercept_[0])}
    is_te = feats.patient_id.isin(test_pids).to_numpy()
    Xtr, Xte = X[~is_te].to_numpy(float), X[is_te]
    check["n_train_scans"], check["n_test_scans_legacy"] = int((~is_te).sum()), int(is_te.sum())
    from prism.analyses.shap_contrib import linear_shap
    s, ev = linear_shap(clf, Xtr, Xte.to_numpy(float))
    assert np.abs(s.sum(1) + ev - clf.decision_function(Xte)).max() < 1e-8
    S = pd.DataFrame(s, columns=X.columns, index=Xte.index)
    Str = pd.DataFrame(linear_shap(clf, Xtr, Xtr)[0], columns=X.columns, index=X.index[~is_te])
    # probability-scale check: permutation SHAP on the calibrated output
    rng = np.random.default_rng(0)
    bg = Xtr[rng.choice(len(Xtr), 100, replace=False)]
    f = lambda Z: cal.predict_proba(surv.predict_positive_probability(clf, pd.DataFrame(Z, columns=X.columns))
                                    .reshape(-1, 1))[:, 1]
    pe = shap.PermutationExplainer(f, shap.maskers.Independent(bg, max_samples=100), seed=0)
    P = pd.DataFrame(pe(Xte.to_numpy(float), max_evals=2 * X.shape[1] + 1, silent=True).values, columns=X.columns,
                     index=Xte.index)
    raw_te = feats.set_index("scan_id").loc[Xte.index, X.columns]
    return S, Str, P, raw_te, check, float(ev)


# ---------------------------------------------------------------- 2. our models
def ours(tr, te, ctx):
    from prism.analyses.shap_contrib import design, explain, fit_model
    from prism.experiments import c3_radiomics as c3
    cohort, folds, base, full, rad, er, col_group = ctx
    out, check = {}, []
    y = cohort[f"label_{H}"].to_numpy()
    for m in OURS:
        if m == "rad_ridge":  # same steps as c3.fit_predict concat, with the selected radiomics names kept
            trk = tr[~np.isnan(y[tr])]
            bp = clone(c3.BASE_PRE).fit(base.iloc[trk])
            R = rad["legacy"]
            sp = clone(c3.selector("top10")).fit(R.iloc[trk].to_numpy(float), y[trk].astype(int))
            imp = sp.named_steps["imp"]
            nm = np.array(list(R.columns) + [f"missing_{R.columns[j]}" for j in imp.flag_cols_])
            nm = nm[sp.named_steps["var"].get_support()][sp.named_steps["sel"].get_support()]
            Xtr = np.hstack([bp.transform(base.iloc[trk]), sp.transform(R.iloc[trk].to_numpy(float))])
            Xte = np.hstack([bp.transform(base.iloc[te]), sp.transform(R.iloc[te].to_numpy(float))])
            names, learner, ytr = list(bp.get_feature_names_out()) + [f"rad:{c}" for c in nm], "ridge", y[trk].astype(int)
        else:
            trk, Xtr, ytr, Xte, names, learner = design(m, ctx, None, tr, te, 0)
        model = fit_model(learner, Xtr, cohort, trk, ytr, 0)
        s, ev = explain(learner, model, Xtr, Xte)
        pred = model.predict_proba(Xte)[:, 1]
        cfg = LEGACY_CFG if m == "rad_ridge" else c3.BASELINES[0 if learner == "ridge" else 1]
        ref = c3.fit_predict(cfg, cohort, base, rad, er, tr, te)
        check.append({"model": m, "max_abs_diff_vs_c3_fit_predict": float(np.abs(ref - pred).max()), "base_value": ev,
                      "auc_naive": roc_auc_score(cohort.naive_label_120.iloc[te], pred),
                      "auc_ipcw": point_metrics(cohort.iloc[te].reset_index(drop=True), pred, H)["auc_ipcw"]})
        grp = {c: ("radiomics" if c.startswith("rad:") else col_group.get(c.removeprefix("missingindicator_"), "other"))
               for c in names}
        out[m] = (pd.DataFrame(s, columns=names, index=cohort.scan_id.iloc[te]), pd.DataFrame(Xte, columns=names,
                  index=cohort.scan_id.iloc[te]), grp, pred)
    return out, pd.DataFrame(check)


# ---------------------------------------------------------------- 3. composition
def composition(c, ph):
    n_pat = c.patient_id.nunique()
    r = {"n_scans": len(c), "n_patients": n_pat, "scans_per_patient": len(c) / n_pat,
         "event_rate_naive": c.naive_label_120.mean(), "event_rate_verified": c.label_120.mean(),
         "censored_before_120d_frac": c.label_120.isna().mean(),
         "patient_progressed_frac": c.groupby("patient_id").event.max().mean(),
         "median_days_from_diagnosis": c.days_from_diagnosis_to_mri.median(),
         "grade4_frac": c.grade4.mean(), "gbm_frac": c.gbm.mean(), "idh_mutant_frac": c.idh.eq("mutant").mean(),
         "mgmt_methylated_frac": c.mgmt.eq("methylated").mean()}
    for p in PHASES:
        r[f"frac_{p}"] = ph.eq(p).mean()
        r[f"event_rate_naive_{p}"] = c.naive_label_120[ph.eq(p)].mean()
    r["frac_post_rt"] = ph.isin(["early_post_rt", "later"]).mean()
    return r


def simple_score_auc(c, ph):
    """No-training reference scores: AUC of fixed rules on a scan set (sign fixed a priori)."""
    y = c.naive_label_120.to_numpy()
    out = {}
    for k, s in {"score_neg_days_from_diagnosis": -c.days_from_diagnosis_to_mri,
                 "score_phase_post_rt": ph.isin(["early_post_rt", "later"]).astype(float),
                 "score_neg_visit_index": -c.visit_index}.items():
        out[k] = roc_auc_score(y, s) if len(np.unique(y)) == 2 else np.nan
    return out


@counted_warnings
def run(n_boot):
    from prism.analyses import shap_contrib as sc
    from prism.config import REPO
    OUT.mkdir(parents=True, exist_ok=True)
    tp = pd.read_csv(REPO / "legacy" / "radiomics" / "models" / "calibrated" / "test_predictions.csv")
    tp["scan_id"] = tp.patient_id + "_" + tp.timepoint
    test_pids = set(tp.patient_id)
    ctx = sc._mu_context("all_glioma")
    cohort = ctx[0]
    ph = phases(cohort)
    is_te = cohort.patient_id.isin(test_pids).to_numpy()
    tr, te = np.where(~is_te)[0], np.where(is_te)[0]
    ct = cohort.iloc[te]

    # 1. shipped model
    S, Str, P, raw_te, check, ev = shipped(test_pids, tp)
    S = S.loc[ct.scan_id]  # the 82 cohort scans (2 of the 84 shipped test scans left the label-fixed cohort)
    P = P.loc[ct.scan_id]
    modality = {c: ("clinical" if c.startswith("clin_") else c.split("_", 1)[0]) for c in S.columns}
    texture = {c: ("clinical" if c.startswith("clin_") else texture_class(c)) for c in S.columns}
    filt = {c: ("clinical" if c.startswith("clin_") else image_filter(c)) for c in S.columns}
    fs, gm = summarise_flat(S, modality)
    fs["texture_class"], fs["filter"] = fs.feature.map(texture), fs.feature.map(filt)
    fs["mean_abs_shap_train"] = fs.feature.map(Str.abs().mean())
    fs["rank_train"] = fs.mean_abs_shap_train.rank(ascending=False)
    fs["mean_abs_shap_prob_permutation"] = fs.feature.map(P.abs().mean())
    shp = pd.read_csv(REPO / "legacy/radiomics/models/calibrated/shap_feature_importance.csv")
    fs = fs.merge(shp.rename(columns={"mean_abs_shap": "mean_abs_shap_shipped_csv"})[["feature", "mean_abs_shap_shipped_csv"]],
                  on="feature", how="left")
    fs["rank_shipped_csv"] = fs.mean_abs_shap_shipped_csv.rank(ascending=False)
    _, gt = summarise_flat(S, texture)
    _, gf = summarise_flat(S, filt)
    groups_shipped = pd.concat([gm.assign(grouping="modality"), gt.assign(grouping="texture_class"),
                                gf.assign(grouping="filter")])
    shm = pd.read_csv(REPO / "legacy/radiomics/models/calibrated/shap_modality_share.csv").set_index("modality").share
    groups_shipped["share_shipped_csv"] = np.where(groups_shipped.grouping == "modality",
                                                   groups_shipped.group.map(shm), np.nan)
    fs.to_csv(OUT / "shipped_features.csv", index=False)
    groups_shipped.to_csv(OUT / "shipped_groups.csv", index=False)
    S.assign(base_value=ev).to_csv(OUT / "shap_shipped_test.csv.gz")
    ok = fs.mean_abs_shap_shipped_csv.notna()
    check.update({"base_value_logit": ev, "n_test_scans_cohort": len(S),
                  "spearman_test_vs_shipped_csv": spearmanr(fs.mean_abs_shap[ok], fs.mean_abs_shap_shipped_csv[ok])[0],
                  "spearman_test_vs_train": spearmanr(fs.mean_abs_shap, fs.mean_abs_shap_train)[0],
                  "spearman_logit_vs_prob_permutation": spearmanr(fs.mean_abs_shap, fs.mean_abs_shap_prob_permutation)[0],
                  "top10_overlap_test_vs_shipped_csv": len(set(fs.feature.head(10)) & set(shp.feature.head(10)))})
    pd.Series(check).to_csv(OUT / "shipped_check.csv", header=["value"])
    plot(S, raw_te.loc[S.index], fs, gm, "PRISM report model (as shipped)", OUT / "shipped")

    # 2. our models
    res, chk2 = ours(tr, te, ctx)
    chk2.to_csv(OUT / "ours_check.csv", index=False)
    oof_f = pd.read_csv(RESULTS / "analyses" / "shap" / "all_glioma" / "features.csv")
    oof_g = pd.read_csv(RESULTS / "analyses" / "shap" / "all_glioma" / "groups.csv")
    F, G, prof = [], [], []
    raw = ctx[3].reset_index(drop=True).set_axis(cohort.scan_id)
    for m, (Sm, Xm, grp, pred) in res.items():
        f, g = summarise_flat(Sm, grp)
        F.append(f.assign(model=m)); G.append(g.assign(model=m))
        Sm.to_csv(OUT / f"shap_{m}_test.csv.gz")
        V = pd.DataFrame({c: (raw[c.removeprefix("missingindicator_")].isna().astype(float) if c.startswith("missingindicator_")
                              else raw[c] if c in raw else Xm[c]) for c in Sm.columns}).loc[Sm.index]
        if m in ("base_ridge", "base_gbm"):
            plot(Sm, V, f, g, OURS[m], OUT / m)
        # test-set profile vs cohort-wide OOF profile (and the OOF profile restricted to these 82 scans)
        if m in ("base_ridge", "base_gbm"):
            O = pd.read_csv(RESULTS / "analyses" / "shap" / "all_glioma" / f"shap_{m}.csv.gz")
            fc = sc.feat_cols(O)
            Oin = O[O.row.isin(te)][fc].abs().mean()
            Oout = O[~O.row.isin(te)][fc].abs().mean()
            of = oof_f[oof_f.model == m].set_index("feature")
            d = pd.DataFrame({"model": m, "feature": f.feature, "group": f.group, "test_mean_abs": f.mean_abs_shap.values,
                              "test_rank": f["rank"].values}).set_index("feature")
            d["oof_mean_abs"], d["oof_rank"] = of.mean_abs_shap, of["rank"]
            d["oof_test_patients_mean_abs"], d["oof_other_patients_mean_abs"] = Oin, Oout
            prof.append(d.reset_index())
            og = oof_g[oof_g.model == m].set_index("group").share
            G[-1]["share_oof_all"] = G[-1].group.map(og)
    F, G = pd.concat(F), pd.concat(G)
    F.to_csv(OUT / "ours_features.csv", index=False)
    G.to_csv(OUT / "ours_groups.csv", index=False)
    prof = pd.concat(prof)
    prof.to_csv(OUT / "profile_test_vs_oof.csv", index=False)
    pc = [{"model": m, "spearman_test_vs_oof": spearmanr(d.test_mean_abs, d.oof_mean_abs)[0],
           "spearman_oof_testpatients_vs_others": spearmanr(d.oof_test_patients_mean_abs, d.oof_other_patients_mean_abs)[0],
           "top5_test": ";".join(d.sort_values("test_rank").feature.head(5)),
           "top5_oof": ";".join(d.sort_values("oof_rank").feature.head(5))} for m, d in prof.groupby("model")]
    pd.DataFrame(pc).to_csv(OUT / "profile_test_vs_oof_summary.csv", index=False)

    # 3a. composition: full cohort / train / test / 500 splits
    sv = pd.read_csv(RESULTS / "analyses" / "split_variance" / "per_split_auc.csv")
    comp = [{"set": "full_cohort", **composition(cohort, ph), **simple_score_auc(cohort, ph)},
            {"set": "train", **composition(cohort.iloc[tr], ph.iloc[tr]), **simple_score_auc(cohort.iloc[tr], ph.iloc[tr])},
            {"set": "prism_report_test", **composition(ct, ph.iloc[te]), **simple_score_auc(ct, ph.iloc[te])}]
    per = []
    for _, r in sv.iterrows():
        k = cohort.patient_id.isin(r.test_patients.split("|")).to_numpy()
        per.append({"seed": r.seed, **composition(cohort[k], ph[k]), **simple_score_auc(cohort[k], ph[k])})
    per = pd.DataFrame(per)
    aucs = [c for c in sv.columns if c.endswith(("_auc_naive", "_auc_ipcw"))]
    per = per.merge(sv[["seed", "prism_report_split", *aucs]], on="seed")
    per.to_csv(OUT / "per_split_composition.csv", index=False)
    comp = pd.DataFrame(comp).set_index("set")
    rep = per[per.prism_report_split].iloc[0]
    metrics = [c for c in comp.columns]
    dist = pd.DataFrame({"splits_mean": per[metrics].mean(), "splits_p2.5": per[metrics].quantile(.025),
                         "splits_p97.5": per[metrics].quantile(.975),
                         "pct_rank_test_in_splits": [100 * (per[c] < rep[c]).mean() + 50 * (per[c] == rep[c]).mean()
                                                     for c in metrics]})
    comp = pd.concat([comp.T, dist], axis=1)
    comp.to_csv(OUT / "composition.csv")
    corr = []
    for a in ("prism_reselect_auc_naive", "prism_reselect_auc_ipcw", "baseline_auc_naive", "baseline_auc_ipcw",
              "prism_fixed_auc_naive"):
        for c in metrics:
            x = per[[a, c]].dropna()
            if x[c].nunique() > 1:
                rho, pv = spearmanr(x[a], x[c])
                corr.append({"auc": a, "composition": c, "spearman": rho, "p": pv, "n_splits": len(x)})
    pd.DataFrame(corr).to_csv(OUT / "split_auc_vs_composition.csv", index=False)
    # how much of the per-split AUC does composition explain? OLS on standardised composition; seed-62 prediction
    from sklearn.linear_model import LinearRegression
    from sklearn.model_selection import cross_val_predict
    preds_c = ["event_rate_naive", "event_rate_naive_pre_rt", "frac_pre_rt", "frac_later", "idh_mutant_frac",
               "mgmt_methylated_frac", "gbm_frac", "median_days_from_diagnosis", "scans_per_patient"]
    ols = []
    for a in ("prism_reselect_auc_naive", "baseline_auc_naive", "prism_reselect_auc_ipcw", "baseline_auc_ipcw"):
        x = per[[a, *preds_c, "prism_report_split"]].dropna()
        Z = (x[preds_c] - x[preds_c].mean()) / x[preds_c].std()
        lr = LinearRegression().fit(Z, x[a])
        cv = cross_val_predict(LinearRegression(), Z, x[a], cv=10)
        k = x.prism_report_split.to_numpy()
        ols.append({"auc": a, "n_splits": len(x), "r2_in_sample": lr.score(Z, x[a]),
                    "r2_cv10": 1 - ((x[a] - cv) ** 2).sum() / ((x[a] - x[a].mean()) ** 2).sum(),
                    "mean_auc": x[a].mean(), "seed62_auc": float(x[a][k].iloc[0]),
                    "seed62_predicted_from_composition": float(cv[k][0]),
                    **{f"coef_{c}": v for c, v in zip(preds_c, lr.coef_)}})
    ols = pd.DataFrame(ols)
    ols.to_csv(OUT / "split_auc_composition_ols.csv", index=False)

    # 3b. AUC within phase subsets of the test set
    shipped_p = tp.set_index("scan_id").calibrated_probability.reindex(ct.scan_id).to_numpy()
    preds = {"PRISM report model (as shipped)": shipped_p, **{OURS[m]: res[m][3] for m in OURS}}
    oofr = pd.read_csv(RESULTS / "c3" / "all_glioma" / "oof_repeats.csv.gz")
    oofr = oofr.set_index("scan_id").reindex(cohort.scan_id)
    oof_base = oofr[[f"None|none|none|none|ridge#r{r}" for r in range(5)]].to_numpy().T
    sub_rows = []
    pht = ph.iloc[te].to_numpy()
    for sub, mask in {"all": np.ones(len(ct), bool), "post_rt": np.isin(pht, ["early_post_rt", "later"]),
                      "later": pht == "later", "pre_or_during_rt": np.isin(pht, ["pre_rt", "during_rt"]),
                      "not_pre_rt": pht != "pre_rt"}.items():
        d = ct[mask].reset_index(drop=True)
        y = d.naive_label_120.to_numpy()
        for name, p in preds.items():
            row = {"subset": sub, "model": name, "n_scans": int(mask.sum()), "n_patients": d.patient_id.nunique(),
                   "n_pos_naive": int(y.sum())}
            if len(np.unique(y)) == 2:
                a, lo, hi = boot_auc(y, p[mask], d.patient_id.to_numpy(), n_boot)
                row.update(auc_naive=a, auc_naive_lo=lo, auc_naive_hi=hi)
                try:
                    row["auc_ipcw"] = point_metrics(d, p[mask], H)["auc_ipcw"]
                    b = cluster_bootstrap(d, {"m": p[mask]}, H, reference="m", n_boot=n_boot).iloc[0]
                    row.update(auc_ipcw_lo=b.auc_ipcw_lo, auc_ipcw_hi=b.auc_ipcw_hi)
                except IndexError:  # IPCW bootstrap breaks on resamples without censoring (small subsets): naive CI only
                    pass
            sub_rows.append(row)
        # reference: the same subset over the whole cohort, baseline ridge OOF (mean over 5 repeats of per-repeat AUC)
        mk = {"all": np.ones(len(cohort), bool), "post_rt": ph.isin(["early_post_rt", "later"]).to_numpy(),
              "later": ph.eq("later").to_numpy(), "pre_or_during_rt": ph.isin(["pre_rt", "during_rt"]).to_numpy(),
              "not_pre_rt": ph.ne("pre_rt").to_numpy()}[sub]
        yc = cohort.naive_label_120.to_numpy()[mk]
        sub_rows.append({"subset": sub, "model": "Baseline ridge, whole-cohort OOF (5x5 CV)", "n_scans": int(mk.sum()),
                         "n_patients": cohort.patient_id[mk].nunique(), "n_pos_naive": int(yc.sum()),
                         "auc_naive": np.mean([roc_auc_score(yc, o[mk]) for o in oof_base])})
    sub = pd.DataFrame(sub_rows)
    sub.to_csv(OUT / "subset_auc.csv", index=False)
    pd.DataFrame({"scan_id": ct.scan_id.values, "patient_id": ct.patient_id.values, "phase": pht,
                  "naive_label_120": ct.naive_label_120.values, "label_120": ct.label_120.values,
                  "days_from_diagnosis": ct.days_from_diagnosis_to_mri.values,
                  **{k: v for k, v in preds.items()}}).to_csv(OUT / "test_scans.csv", index=False)
    # per-phase mean prediction, label and group SHAP on the test scans
    pp = []
    for name, Sg, grp in (("PRISM report model (as shipped)", S, modality),
                          *((OURS[m], res[m][0], res[m][2]) for m in OURS)):
        Gp = Sg.T.groupby(grp).sum().T.groupby(pht).mean().add_prefix("mean_shap_")
        Gp["mean_total_shap"] = Sg.sum(1).groupby(pht).mean()
        Gp["mean_pred"] = pd.Series(preds[name]).groupby(pht).mean().values
        Gp["n_scans"], Gp["event_rate_naive"] = pd.Series(pht).value_counts().reindex(Gp.index).values, \
            ct.naive_label_120.groupby(pht).mean().reindex(Gp.index).values
        pp.append(Gp.assign(model=name).rename_axis("phase").reset_index())
    pp = pd.concat(pp)
    # AUC decomposition: all positives vs pre-RT negatives / vs the other negatives (pair shares)
    y = ct.naive_label_120.to_numpy()
    pos, n_pre, n_oth = y == 1, (y == 0) & (pht == "pre_rt"), (y == 0) & (pht != "pre_rt")
    dec = []
    for name, p in preds.items():
        a = lambda neg: float(((p[pos][:, None] > p[neg][None]) + 0.5 * (p[pos][:, None] == p[neg][None])).mean())
        dec.append({"model": name, "n_pos": int(pos.sum()), "n_neg_pre_rt": int(n_pre.sum()), "n_neg_other": int(n_oth.sum()),
                    "pair_share_pre_rt_neg": n_pre.sum() / (n_pre.sum() + n_oth.sum()), "auc_all": a(y == 0),
                    "auc_vs_pre_rt_neg": a(n_pre), "auc_vs_other_neg": a(n_oth)})
    pd.DataFrame(dec).to_csv(OUT / "auc_pair_decomposition.csv", index=False)
    pp.to_csv(OUT / "phase_profile.csv", index=False)

    with pd.option_context("display.width", 250, "display.max_colwidth", 60):
        print(pd.Series(check).to_string())
        print(fs.head(12)[["rank", "feature", "group", "texture_class", "mean_abs_shap", "share", "rank_train",
                           "rank_shipped_csv"]].round(3).to_string(index=False))
        print(groups_shipped.round(3).to_string(index=False))
        print(chk2.round(4).to_string(index=False))
        for m in OURS:
            print(m, F[F.model == m].head(8)[["feature", "group", "mean_abs_shap", "share"]].round(3).to_string(index=False), sep="\n")
        print(G.round(3).to_string(index=False))
        print(pd.DataFrame(pc).round(3).to_string(index=False))
        print(comp.round(3).to_string())
        print(ols.round(3).T.to_string())
        c = pd.DataFrame(corr)
        print(c[c.p < 0.05].sort_values(["auc", "p"]).round(3).to_string(index=False))
        print(sub.round(3).to_string(index=False))
        print(pp.round(3).to_string(index=False))
        print(pd.DataFrame(dec).round(3).to_string(index=False))


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="prism shap_prism_split", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n-boot", type=int, default=1000)
    run(ap.parse_args(argv).n_boot)


if __name__ == "__main__":
    main()
