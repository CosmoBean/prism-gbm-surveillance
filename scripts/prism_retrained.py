"""PRISM at LUMIERE and UCSF-ALPTDG three ways (PI 2026-11-27: 'show values with retraining or fine-tuning'):

  external     fitted once on MU, applied unchanged (the paper's external result)
  trained      fitted within the centre: 5 repeats of patient-grouped, label-stratified 5-fold CV on its own scans
  fine-tuned   fitted on all MU scans plus the centre's training folds, scored on the held-out fold (same folds)

Same ridge pipeline (BASE_PRE + verified ridge), same designs and segmenter inputs as prism.analyses.system.
Evaluation: AUC over the centre's labelled scans, mean over the 5 repeats; 95% CI and paired differences from
2,000 bootstrap samples of patients.

  PRISM_MASKS=brats24_22 PRISM_MEASUREMENTS=$PWD/outputs/results/analyses/segmenter_brats24/mu_table_brats24_padded.csv \
  PYTHONPATH=. .venv/bin/python scripts/prism_retrained.py [lumiere] [ucsf]   -> outputs/results/analyses/retrained_brats24_22/
"""
import json, warnings
import numpy as np, pandas as pd
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedGroupKFold
warnings.filterwarnings("ignore")
from prism.analyses import system as SYS, detection as D
from prism.analyses import ucsf_external as UX
from prism.config import MASK_SUFFIX, RESULTS

OUT = RESULTS / "analyses" / f"retrained{MASK_SUFFIX}"
SEED, N_REP, N_FOLD, N_BOOT = 20261127, 5, 5, 2000
PW = ("timeline", "images", "combined")


def lumiere():
    SS, (d, A4, T, cv) = SYS._seg_designs()
    L, LX, _ = D.lumiere_detection()
    Xmu = {"timeline": T[D.T_BASE], "images": cv["images"], "combined": cv["combined"]}
    ls = SS.lumiere_seg(L, LX, list(cv["images"].columns), "brats24")
    Xe = {"timeline": LX[D.T_BASE], "images": ls["images"], "combined": ls["combined"]}
    return d, Xmu, Xe, L.label_det.to_numpy(float), L.patient_id.to_numpy()


def ucsf():
    SS, (d4, A4, T, cv) = SYS._seg_designs()
    u = UX.ucsf_frame()
    A = UX.ucsf_designs(u, A4)
    keep = (u.timepoint.eq(2) & u.grade4).to_numpy()
    Xmu = {"timeline": A4["A-Tbase"], "images": cv["images"], "combined": cv["combined"]}
    us = SS.ucsf_seg(u, A, keep, list(cv["images"].columns), "brats24")
    Xe = {"timeline": A["A-Tbase"][keep].reset_index(drop=True), "images": us["images"], "combined": us["combined"]}
    uk = u[keep].reset_index(drop=True)
    pm30, neg = uk.pos_s2_pm30.eq(1).to_numpy(), uk.primary_neg.to_numpy()
    return d4, Xmu, Xe, np.where(pm30, 1.0, np.where(neg, 0.0, np.nan)), uk.subject_id.to_numpy()


def frame(pid, y):
    return pd.DataFrame({"patient_id": pid, "label_120": y})


def run(name, d, Xmu, Xe, y, pid):
    lab = ~np.isnan(y)
    Xe = {p: X[lab].reset_index(drop=True)[list(Xmu[p].columns)] for p, X in Xe.items()}
    y, pid = y[lab].astype(int), pid[lab]
    n = len(y)
    dmu = frame(d.patient_id.to_numpy(), d.label_120.to_numpy())
    P = {(a, p): np.full((N_REP, n), np.nan) for a in ("external", "trained", "fine-tuned") for p in PW}
    for p in PW:
        f = SYS._fit(Xmu[p], dmu, np.arange(len(dmu)))
        P[("external", p)][:] = f(Xe[p])
    for r in range(N_REP):
        cvs = StratifiedGroupKFold(N_FOLD, shuffle=True, random_state=SEED + r)
        for tr, te in cvs.split(np.zeros(n), y, pid):
            de = frame(pid[tr], y[tr].astype(float))
            for p in PW:
                f = SYS._fit(Xe[p].iloc[tr].reset_index(drop=True), de, np.arange(len(tr)))
                P[("trained", p)][r, te] = f(Xe[p].iloc[te])
                Xc = pd.concat([Xmu[p], Xe[p].iloc[tr]], ignore_index=True)
                dc = pd.concat([dmu, de], ignore_index=True)
                f = SYS._fit(Xc, dc, np.arange(len(dc)))
                P[("fine-tuned", p)][r, te] = f(Xe[p].iloc[te])
    auc = lambda k, idx: np.mean([roc_auc_score(y[idx], P[k][r, idx]) for r in range(N_REP)])
    rng = np.random.default_rng(SEED)
    pats = np.unique(pid)
    rows_of = {q: np.where(pid == q)[0] for q in pats}
    boots = []
    for _ in range(N_BOOT):
        idx = np.concatenate([rows_of[q] for q in rng.choice(pats, len(pats))])
        if 0 < y[idx].sum() < len(idx):
            boots.append(idx)
    res = []
    for p in PW:
        for a in ("external", "trained", "fine-tuned"):
            k = (a, p)
            full = auc(k, np.arange(n))
            bs = np.array([auc(k, i) for i in boots])
            dif = np.array([auc(k, i) - auc(("external", p), i) for i in boots]) if a != "external" else None
            res.append({"centre": name, "model": p, "fit": a, "n_scans": n, "n_pos": int(y.sum()),
                        "n_patients": len(pats), "auc": round(full, 4),
                        "ci": [round(float(np.quantile(bs, q)), 3) for q in (.025, .975)],
                        "diff_vs_external": None if dif is None else round(full - auc(("external", p), np.arange(n)), 3),
                        "diff_ci": None if dif is None else [round(float(np.quantile(dif, q)), 3) for q in (.025, .975)]})
            print(res[-1])
    return res


if __name__ == "__main__":
    assert MASK_SUFFIX == "_brats24_22", "run with PRISM_MASKS=brats24_22 (the paper's primary pipeline)"
    OUT.mkdir(parents=True, exist_ok=True)
    import sys
    for name in sys.argv[1:] or ["lumiere", "ucsf"]:
        res = run({"lumiere": "LUMIERE", "ucsf": "UCSF-ALPTDG"}[name], *{"lumiere": lumiere, "ucsf": ucsf}[name]())
        pd.DataFrame(res).to_csv(OUT / f"retrained_{name}.csv", index=False)
        json.dump(res, open(OUT / f"retrained_{name}.json", "w"), indent=1)
