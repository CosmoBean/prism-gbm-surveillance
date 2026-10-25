# EXPLORATORY (post hoc, 2026-10-25): images + clinical (age, sex, IDH, MGMT), no timeline. The model a dataset with
# images and clinical data but no treatment dates could build.
# Run: PYTHONPATH=. .venv/bin/python scripts/exploratory_images_clinical_detection.py  (about 5 min; prints results)
import warnings, numpy as np, pandas as pd
warnings.filterwarnings("ignore")
from prism.analyses import detection as D
from prism.analyses.triage_feasibility import _features_one
from prism.experiments import c3_radiomics as c3
from prism.features.tabular import measurement_groups

index, d0, _, meas = D._base()
d, X, rad, er, F = D.context("grade4", "primary")
mg = measurement_groups(d)
by_pat = {p: g.sort_values("mri_day") for p, g in meas.groupby("patient_id")}
nad = []
for sid, pid, day in zip(d.scan_id, d.patient_id, d.mri_day):
    g = by_pat[pid]; h = g[g.mri_day <= day]
    f = _features_one(h, day, -np.inf)
    nad.append({"nadir_all_et": f["traj_logratio_nadir_et"], "nadir_all_lesion": f["traj_logratio_nadir_lesion"]})
nad = pd.DataFrame(nad, index=d.index)
prevr = F[[c for c in F.columns if c.startswith("logratio_prev_")]]
ipure = pd.concat([mg["volumes"], mg["morphology"], prevr, nad], axis=1)
iscan = pd.concat([mg["volumes"], mg["morphology"]], axis=1)
arms = {
  "B0": X["B0"], "B1": X["B1"], "I_scan": iscan, "I_pure": ipure,
  "B0+I_scan": pd.concat([X["B0"], iscan], axis=1),
  "B0+I_pure": pd.concat([X["B0"], ipure], axis=1),
  "B1+I_pure": pd.concat([X["B1"], ipure], axis=1),
}
lab = d.label_120.to_numpy()
oof = {a: np.full((5, len(d)), np.nan) for a in arms}
for a, Xa in arms.items():
    for r in range(5):
        f = D.fold_ids(d, r)
        for k in range(5):
            tr, te = np.where(f != k)[0], np.where(f == k)[0]
            oof[a][r, te] = c3.fit_predict(c3.BASELINES[0], d, Xa, {}, None, tr, te, seed=r)
sets = D.eval_sets(d, "primary")
con = [("B0+I_pure","I_pure"),("B0+I_scan","I_scan"),("B0+I_pure","B0"),("B0+I_pure","B1"),("B1+I_pure","B0+I_pure")]
out=[]
for name in ("intended_use","all_scans"):
    rows = np.where(sets[name])[0]
    res, c, wp = D.evaluate_set(name, d, rows, oof, 1000, contrasts=con)
    for x in res: print(name, x["arm"], round(x["auc"],3), round(x["auc_lo"],3), round(x["auc_hi"],3))
    for x in c: print(name, x["subset"], x["contrast"], round(x["diff"],3), round(x["diff_lo"],3), round(x["diff_hi"],3))
    for x in wp:
        if x["phase"] in ("later_post_rt","phase_stratified"): print(name, "WP", x["phase"], x["arm"], round(x["auc"],3), x["auc_lo"], x["auc_hi"])
