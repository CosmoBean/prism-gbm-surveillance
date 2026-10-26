"""EXPLORATORY (not pre-specified): clinical-only model on LUMIERE detection, for Figure 2's "clinical alone".

Model: age, sex, IDH, MGMT with the C2 rules (no unknown indicators, markers masked before diagnosis) = the first four
columns of Tbase, fitted once on the MU grade-4 detection training rows exactly as Tbase (positives + primary
negatives, all phases; ridge via c3._ridge on c3.BASE_PRE) and applied once to the LUMIERE detection set.
Plain AUC, patient-cluster bootstrap, 1,000 draws, seed 20261021 (as the other locked LUMIERE results).
Also: MU internal OOF of the same model (= B0) on grade 4, intended use (the Tbase internal population).
Existing module behaviour is unchanged; everything is imported from prism.analyses.detection.
"""
import json
import warnings

import numpy as np
import pandas as pd
from sklearn.base import clone

from prism.analyses import detection as D
from prism.experiments import c3_radiomics as c3

warnings.filterwarnings("ignore")
N_BOOT, SEED = 1000, 20261021
CLIN = ["age", "male", "idh_mutant", "mgmt_methylated"]
OUT = D.OUT / "lumiere_clinical_alone.json"

# --- LUMIERE external: fit once on MU grade-4 training rows, apply once
L, LX, info = D.lumiere_detection()
d, X, *_ = D.context("grade4", "primary")
assert list(X["B0"].columns) == CLIN and list(X["Tbase"].columns[:4]) == CLIN
tr = np.where(d.label_120.notna())[0]
bp = clone(c3.BASE_PRE).fit(X["B0"].iloc[tr])
m = c3._ridge(bp.transform(X["B0"].iloc[tr]), d, tr, 0)
p = m.predict_proba(bp.transform(LX[CLIN]))[:, 1][None, :]
y, g = L.label_det.to_numpy(), L.patient_id.to_numpy()
pt, dr = D.bootstrap(y, {"clin": p}, g, N_BOOT, SEED)
lo, hi = D.ci(dr[("clin", "all")])
ext = {"auc": pt[("clin", "all")], "lo": lo, "hi": hi, "n_pos": int(y.sum()), "n_neg": int((y == 0).sum()),
       "n_patients": int(len(np.unique(g))), "n_train_rows": int(len(tr)),
       "n_lumiere_missing_clinical": int(LX[CLIN].isna().any(axis=1).sum())}

# --- MU internal OOF (grade 4, primary negatives, shared 5x5 folds), evaluated in the intended use
oof = np.full((5, len(d)), np.nan)
for r in range(5):
    for k in range(5):
        _, te, pr, _c = D.cv_job(("grade4", "primary", "B0", r, k))
        oof[r, te] = pr
sets = D.eval_sets(d, "primary")
rows = sets["intended_use"]
yy, gg = d.label_det.to_numpy()[rows], d.patient_id.to_numpy()[rows]
ph = d.phase.to_numpy()[rows]
pt2, dr2 = D.bootstrap(yy, {"clin": oof[:, rows]}, gg, N_BOOT, SEED)
lo2, hi2 = D.ci(dr2[("clin", "all")])
internal = {"auc": pt2[("clin", "all")], "lo": lo2, "hi": hi2, "n_pos": int(yy.sum()), "n_neg": int((yy == 0).sum()),
            "n_patients": int(len(np.unique(gg)))}
stored = pd.read_csv(D.OUT / "auc.csv")
s = stored[(stored.set == "grade4|train_primary|intended_use") & (stored.arm == "B0")].iloc[0]
internal["stored_B0_auc"] = float(s.auc)
res = {"lumiere_external": ext, "mu_internal_grade4_intended_use": internal}
OUT.write_text(json.dumps(res, indent=1))
print(json.dumps(res, indent=1))
