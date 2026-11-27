"""PRISM and the published radiomics model on the held-out split of Christodoulou et al. 2026 (exploratory).

Their split (code commit 643c888, bin_class/rank_and_split__4.py): np.random.default_rng(42).choice of 30 of the
203 patients of their dataset__2.xlsx (all MU diagnoses); their test set is 96 scans, 53 positive. Here: PRISM's three
ridge models and their LightGBM pipeline (prism.analyses._christodoulou_vendor, 400 Optuna trials) are fitted on our
grade 4 training rows of the patients outside those 30, and scored on our intended-use evaluation scans of the
grade 4 patients among the 30. Our label (scan-level detection), not theirs (patient-level). CI: 2,000 bootstrap
samples of patients.

  PRISM_MASKS=brats24_22 PRISM_MEASUREMENTS=... PYTHONPATH=. .venv/bin/python scripts/prism_christodoulou_split.py <their_test.json>
"""
import json, sys, warnings
import numpy as np, pandas as pd
from sklearn.metrics import roc_auc_score
warnings.filterwarnings("ignore")
sys.path.insert(0, "scripts")
from prism_single_splits import designs
from prism.experiments import c3_radiomics as c3
from prism.config import MASK_SUFFIX, RESULTS

OUT = RESULTS / "analyses" / "single_splits"
SEED = 20261127


def radiomics(tr, te):
    from prism.analyses import _christodoulou_vendor as V, christodoulou_faithful as F
    import contextlib, io, optuna
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    V.LGBM_N_JOBS, V.OPTUNA_N_JOBS = 1, 1   # one thread, as in christodoulou_faithful (oversubscription otherwise)
    F.configure("released")
    d, y, R = F.frame()
    tr = tr[~np.isnan(y[tr])]
    dtr = R.iloc[tr].copy()
    dtr[V.PROG_COL] = np.where(y[tr] == 1, 1.0, np.nan)
    with contextlib.redirect_stdout(io.StringIO()):
        imp, _ = V.compute_importance_traincv(dtr)
    top = V.top_k_features(imp, R.columns, F.K_FEATURES)
    art = V.train_lgbm(R.iloc[tr][top], y[tr].astype(int), d.patient_id.to_numpy()[tr], n_trials=400)
    return V.predict(art, R.iloc[te][top])[1]


if __name__ == "__main__":
    test = set(json.load(open(sys.argv[1])))
    assert len(test) == 30
    d, y, X = designs()
    g = d.patient_id.to_numpy()
    tr = np.where(~np.isin(g, list(test)))[0]
    te = np.where(np.isin(g, list(test)) & ~np.isnan(y) & d.intended_use.to_numpy())[0]
    yy = y[te].astype(int)
    P = {k: c3.fit_predict(c3.BASELINES[0], d, Xa, {}, None, tr, te, seed=0) for k, Xa in X.items()}
    P["published radiomics (supplied masks)"] = radiomics(tr, te)
    rng = np.random.default_rng(SEED)
    pats = np.unique(g[te])
    rows = {q: np.where(g[te] == q)[0] for q in pats}
    boots = [np.concatenate([rows[q] for q in rng.choice(pats, len(pats))]) for _ in range(2000)]
    boots = [b for b in boots if 0 < yy[b].sum() < len(b)]
    res = {"their_test_patients": 30, "grade4_test_patients_here": int(len(pats)), "n_scans": int(len(te)),
           "n_pos": int(yy.sum()), "n_train_patients": int(len(np.unique(g[tr]))), "masks": MASK_SUFFIX or "supplied"}
    for k, p in P.items():
        bs = [roc_auc_score(yy[b], p[b]) for b in boots]
        res[k] = {"auc": round(roc_auc_score(yy, p), 3), "ci": [round(float(np.quantile(bs, q)), 3) for q in (.025, .975)]}
    print(json.dumps(res, indent=1))
    (OUT / f"christodoulou_split{MASK_SUFFIX or '_released'}.json").write_text(json.dumps(res, indent=1))
