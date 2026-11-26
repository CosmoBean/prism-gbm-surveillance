"""PRISM's ridge models on the 100 single splits of the radiomics re-implementation (seeds 0-99, 20% of patients).

Run from outputs/results/analyses/single_splits/:
  PYTHONPATH=../../../.. python ../../../../scripts/prism_single_splits.py 16
  (segmenter: PRISM_MASKS=brats24_22 PRISM_MEASUREMENTS=.../mu_table_brats24_padded.csv)
"""
import sys, warnings, numpy as np, pandas as pd
from concurrent.futures import ProcessPoolExecutor
from sklearn.metrics import roc_auc_score
warnings.filterwarnings("ignore")
from prism.analyses import christodoulou_replication as CR
from prism.analyses import detection as D
from prism.experiments import c3_radiomics as c3
from prism.config import MASK_SUFFIX

def designs():
    d, y, _, ridge = CR.data("grade4")
    if MASK_SUFFIX:
        from prism.features.seg_measurements import CAVITY_INPUTS
        ridge = {**ridge, "I_pure": ridge["I_pure"].drop(columns=list(CAVITY_INPUTS))}
        assert ridge["I_pure"].shape[1] == 22, ridge["I_pure"].shape
    return d, y, {"history": ridge["B1"], "imaging": ridge["I_pure"],
                  "combined": pd.concat([ridge["B1"], ridge["I_pure"]], axis=1)}

def job(j):
    from threadpoolctl import threadpool_limits; threadpool_limits(1); warnings.filterwarnings("ignore")
    kind, a, b = j
    d, y, X = designs(); g = d.patient_id.to_numpy()
    if kind == "cv":
        f = D.fold_ids(d, a); tr, te = np.where(f != b)[0], np.where(f == b)[0]
    else:
        pats = np.unique(g[~np.isnan(y)])
        tp = np.random.default_rng(a).choice(pats, int(round(CR.TEST_FRAC * len(pats))), replace=False)
        tr, te = np.where(~np.isin(g, tp))[0], np.where(np.isin(g, tp) & ~np.isnan(y))[0]
    return j, te, {k: c3.fit_predict(c3.BASELINES[0], d, Xa, {}, None, tr, te, seed=a) for k, Xa in X.items()}

if __name__ == "__main__":
    d, y, X = designs(); iu = d.intended_use.to_numpy()
    jobs = [("cv", r, k) for r in range(5) for k in range(5)] + [("split", s, 0) for s in range(100)]
    with ProcessPoolExecutor(int(sys.argv[1]) if len(sys.argv) > 1 else 16) as ex:
        res = list(ex.map(job, jobs, chunksize=1))
    ev = D.eval_sets(d, "primary")["intended_use"]
    oof = {k: np.full((5, len(d)), np.nan) for k in X}
    for (kind, r, k), te, p in res:
        if kind == "cv":
            for m in X: oof[m][r, te] = p[m]
    yl = d.label_det.to_numpy()[ev]
    print("mask suffix:", repr(MASK_SUFFIX), "| 5x5 CV, intended use, mean over repeats:",
          {m: round(np.mean([roc_auc_score(yl, oof[m][r][ev]) for r in range(5)]), 3) for m in X})
    rows = []
    for (kind, s, _), te, p in res:
        if kind != "split": continue
        m = iu[te]; yy = y[te].astype(int)[m]
        rows.append({"seed": s, "n_test_patients": d.patient_id.iloc[te].nunique(), "n_scans_iu": int(m.sum()),
                     "n_pos_iu": int(yy.sum()),
                     **{f"auc_{k}": roc_auc_score(yy, p[k][m]) if 0 < yy.sum() < len(yy) else np.nan for k in X}})
    sp = pd.DataFrame(rows)
    sp.to_csv(f"splits_prism{MASK_SUFFIX or '_released'}.csv", index=False)
    for k in X:
        x = sp[f"auc_{k}"].dropna()
        print(f"{k:9s} n={len(x)} mean {x.mean():.3f} sd {x.std():.3f} p2.5 {x.quantile(.025):.3f} "
              f"p97.5 {x.quantile(.975):.3f} min {x.min():.3f} (seed {sp.seed[x.idxmin()]}) max {x.max():.3f} "
              f"(seed {sp.seed[x.idxmax()]}) share>=0.80 {(x>=.8).mean():.2f} >=0.90 {(x>=.9).mean():.2f}")
    print("test patients per split:", sp.n_test_patients.min(), "-", sp.n_test_patients.max())
