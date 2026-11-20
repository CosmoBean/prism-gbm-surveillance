"""Timestamp-only check (EXPLORATORY, 2026-11-20): how well the timing of a scan alone ranks it, on the paper's folds and
evaluation sets. MU: unfitted single timestamps and a ridge on all timestamps (5 x 5 CV, intended use), with the AUC
split by time window; LUMIERE and UCSF: unfitted single timestamps. Results: docs/results/TIMING_ONLY.md.

    PRISM_SKIP_UCSF=0 PYTHONPATH=. .venv/bin/python -m prism.analyses.timing_only
"""
import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
from sklearn.metrics import roc_auc_score
from prism.analyses import system as S, detection as D, ucsf_external as UX
from prism.analyses.methods import m1_stats, boot, ci
from prism.experiments import c3_radiomics as c3
d,X=S.mu_designs('grade4'); H=X['timeline']
sets={'days since RT end':['days_since_rt_end','rt_date_unknown'],
      'all timestamps':['days_since_rt_end','rt_date_unknown','days_from_diagnosis','visit_index','early_post_rt'],
      'clinical-history model':list(H.columns)}
ev=(d.label_120.notna() & d.intended_use).to_numpy(); y=d.label_120.to_numpy()[ev]; pid=d.patient_id.to_numpy()[ev]; ctx=d.phase.astype(str).to_numpy()[ev]
P={}
for k,cols in sets.items():
    M=np.full((5,len(d)),np.nan)
    for r in range(5):
        f=D.fold_ids(d,r)
        for kk in range(5):
            tr,te=np.where(f!=kk)[0],np.where(f==kk)[0]
            M[r,te]=c3.fit_predict(c3.BASELINES[0],d,H[cols],{},None,tr,te,seed=r)
    P[k]=M[:,ev]
est=m1_stats(y,P,ctx); B=boot(y,P,ctx,pid,1000,seed=1)
print('MU (CV, intended use, 62 vs 84):')
for k in P:
    lo,hi=ci([b[k][0] for b in B]); wlo,whi=ci([b[k][2] for b in B])
    print(f'  {k:24s} AUC {est[k][0]:.3f} ({lo:.2f}-{hi:.2f})  within-window {est[k][2]:.3f} ({wlo:.2f}-{whi:.2f})  across {est[k][3]:.3f}')
def uv(yy,v):
    ok=~np.isnan(v); return (round(roc_auc_score(yy[ok],v[ok]),3), int(ok.sum()))
print('  univariate, no fitting (AUC, n):', {c: uv(y, d[c].to_numpy(float)[ev]) for c in ['days_since_rt_end','visit_index','days_from_diagnosis_to_mri']})
L,LX,_=D.lumiere_detection(); yl=L.label_det.to_numpy(float); m=~np.isnan(yl)
print('LUMIERE univariate (AUC, n):', {c: uv(yl[m], L[c].to_numpy(float)[m]) for c in ['day','early_post_rt']})
u=UX.ucsf_frame(); keep=(u.timepoint.eq(2)&u.grade4).to_numpy(); uk=u[keep]
yu=np.where(uk.pos_s2_pm30.eq(1),1.0,np.where(uk.primary_neg,0.0,np.nan)); e=~np.isnan(yu)
out={}
for c in ['days_from_diagnosis_to_mri','days_from_rt_start_to_mri','days_from_prev']:
    v=uk[c].to_numpy(float)[e]; ok=~np.isnan(v); out[c]=(round(roc_auc_score(yu[e][ok],v[ok]),3), int(ok.sum()))
print('UCSF scan 2 univariate (AUC, n):', out)
