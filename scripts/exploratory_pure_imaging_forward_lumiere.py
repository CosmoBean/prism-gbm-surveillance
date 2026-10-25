# EXPLORATORY (post hoc, 2026-10-24): data for choosing the paper's end goal.
# (1) 120-day risk (IPCW AUC) with image-only models, timing proxies removed, grade 4: full cohort, intended use,
#     within phase; against the corrected core model C2. (2) LUMIERE detection with image-only inputs.
# Run: PYTHONPATH=. .venv/bin/python scripts/exploratory_pure_imaging_forward_lumiere.py
import warnings, numpy as np, pandas as pd
warnings.filterwarnings("ignore")
from sklearn.base import clone
from prism.analyses import detection as D, phase_censoring as pc
from prism.analyses.intended_use import IN_SCOPE
from prism.analyses.triage_feasibility import _features_one
from prism.experiments import c3_radiomics as c3
from prism.features.tabular import measurement_groups

index, _, _, meas = D._base()
cohort, folds, _, p4, p5 = pc.load("grade4")
cohort = cohort.reset_index(drop=True)
d = cohort.copy(); d["mri_day"] = pd.to_numeric(d.days_from_diagnosis_to_mri)
F = D.change_nadir(d, index, meas)
mg = measurement_groups(cohort)
by_pat = {p: g.sort_values("mri_day") for p, g in meas.groupby("patient_id")}
nad = pd.DataFrame([{k: (f := _features_one(by_pat[pid][by_pat[pid].mri_day <= day], day, -np.inf))[f"traj_logratio_nadir_{k}"]
                     for k in ("et", "lesion")} for pid, day in zip(d.patient_id, d.mri_day)], index=d.index)
nad.columns = ["nadir_all_et", "nadir_all_lesion"]
prevr = F[[c for c in F.columns if c.startswith("logratio_prev_")]]
img_scan = pd.concat([mg["volumes"], mg["morphology"]], axis=1)
img_pure = pd.concat([img_scan, prevr, nad], axis=1)
img_full = pd.concat([img_scan, F.drop(columns="prev_scan_id_used")], axis=1)
c2X, _ = pc.arm_design("C2", cohort, index)
arms = {"I_scan": img_scan, "I_pure": img_pure, "I": img_full, "C2+I_pure": pd.concat([c2X, img_pure], axis=1)}
oof = {a: np.full((5, len(cohort)), np.nan) for a in arms}
for a, X in arms.items():
    X = X.reset_index(drop=True)
    for r in range(5):
        f = c3._fold_ids(cohort, folds, r)
        for k in range(5):
            tr, te = np.where(f != k)[0], np.where(f == k)[0]
            oof[a][r, te] = c3.fit_predict(c3.BASELINES[0], cohort, X, {}, None, tr, te, seed=r)
full = pd.read_csv(pc.OUT / "oof_grade4_full.csv.gz")
assert (full.scan_id.to_numpy() == cohort.scan_id.to_numpy()).all()
oof["C2"] = np.array([full[f"C2#r{r}"].to_numpy(float) for r in range(5)])
iu = np.isin(p4, IN_SCOPE)
for name, m in (("full", np.ones(len(cohort), bool)), ("intended_use", iu)):
    dd, oo, q4, q5 = cohort[m].reset_index(drop=True), {k: v[:, m] for k, v in oof.items()}, p4[m], p5[m]
    subs = {f"phase={lv}": q4 == lv for lv in sorted(set(q4))}
    pt, dr = pc.bootstrap(dd, oo, q4, q5, 1000, 32, schemes=("marginal_km",), subsets=subs, pair_strata=q4)
    print("==", name, "n", len(dd))
    for a in oo:
        for sn in ("all", "phase_stratified") + tuple(subs):
            k = ("marginal_km", a, sn)
            if k in pt:
                lo, hi = pc.ci(dr[k]); print(name, a, sn, round(pt[k], 3), round(lo, 3), round(hi, 3))
    for a, b in (("I_pure", "C2"), ("C2+I_pure", "C2"), ("I", "I_pure"), ("I_pure", "I_scan")):
        for sn in ("all", "phase_stratified"):
            c = pc.contrast(pt, dr, ("marginal_km", a, sn), ("marginal_km", b, sn))
            print(name, f"{a} - {b}", sn, {k: round(v, 3) for k, v in c.items()})
# LUMIERE detection, image-only
L, LX, info = D.lumiere_detection()
dm, X, *_ = D.context("grade4", "primary")
cols = [c for c in X["T"].columns if c not in D.T_BASE + ["has_prev", "log_days_from_prev"]]
print("LUMIERE image cols", cols)
tr = np.where(dm.label_120.notna())[0]
preds = {}
for arm, cc in (("T", list(X["T"].columns)), ("Tbase", D.T_BASE), ("T_img", cols)):
    bp = clone(c3.BASE_PRE).fit(X["T"][cc].iloc[tr])
    mdl = c3._ridge(bp.transform(X["T"][cc].iloc[tr]), dm, tr, 0)
    preds[arm] = mdl.predict_proba(bp.transform(LX[cc]))[:, 1][None, :]
y, g = L.label_det.to_numpy(), L.patient_id.to_numpy()
pt, dr = D.bootstrap(y, preds, g, 1000, 20261021)
for a in preds:
    lo, hi = D.ci(dr[(a, "all")]); print("LUMIERE", a, round(pt[(a, "all")], 3), round(lo, 3), round(hi, 3))
x = dr[("T_img", "all")] - dr[("Tbase", "all")]; print("LUMIERE T_img - Tbase", round(pt[("T_img","all")] - pt[("Tbase","all")], 3), D.ci(x))
