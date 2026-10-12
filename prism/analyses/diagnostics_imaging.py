"""Imaging diagnostics with positive controls: are masks, measurements and label alignment sound?

Imaging-only models reach ~0.6 AUC for "progression within 120 d after this scan". If the pipeline is sound, imaging must
succeed where it obviously should. Checks:
  1 volume cross-check      our mask label counts / measurement volumes vs MU-Glioma-Post_Segmentation_Volumes.xlsx;
                            4x4 label-permutation match matrix; T1c/FLAIR intensity sanity of the label mapping
  2 concurrent detection    progression scan = first MRI (with mask) on/after the documented progression date.
                            (a) paired vs the patient's previous scan (Wilcoxon) (b) imaging-only classifier, progression
                            scans vs index-cohort scans, 5x5 patient-grouped CV (plain AUC; no censoring at a fixed scan)
  3 label/date alignment    progression date vs nearest MRI; time to progression of positives; is label_120 "the next
                            scan is the progression scan"?
  4 horizon curve           imaging-only / clinical+phase / both, ridge, IPCW AUC(H) for H in HORIZONS_DIAG
                            (labels via data.mu.horizon_label; repo folds; c3.fit_predict; metrics.evaluate_repeated)
  5 last vs earlier         among progressors' index scans: last scan before progression vs earlier ones
  6 visual QA               T1c + FLAIR overlays for 4 progression / 4 positive / 4 negative index scans

    python -m prism.analyses.diagnostics_imaging [--workers 24 --n-boot 500]
    -> $PRISM_OUTPUTS/results/analyses/diagnostics_imaging/
"""

from __future__ import annotations

import argparse
import json
import warnings
from concurrent.futures import ProcessPoolExecutor

import nibabel as nib
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedGroupKFold
from threadpoolctl import threadpool_limits

from prism.analyses.phase_ladder import SINGLE, phase
from prism.config import MEASUREMENTS, MU_ROOT, RESULTS, mu_scan_paths
from prism.data.mu import horizon_label, load_cohort, load_index, patient_dates
from prism.experiments import c3_radiomics as c3
from prism.features.tabular import clinical, measurement_groups
from prism.models.folds import load_folds
from prism.models.metrics import counted_warnings, evaluate_repeated

OUT = RESULTS / "analyses" / "diagnostics_imaging"
VOLUMES_XLSX = MU_ROOT / "MU-Glioma-Post_Segmentation_Volumes.xlsx"
SHEET_LABEL = {"Necrotic Tumor Core (Label1)": 1, "Tumor Infiltration and Edema": 2,
               "Enhancing Tumor Core (Label3)": 3, "Resection Cavity (Label4)": 4}
OURS = {1: "netc", 2: "snfh", 3: "et", 4: "rc"}  # config: LABEL_NETC, LABEL_SNFH, LABEL_ET, LABEL_RC = 1, 2, 3, 4
HORIZONS_DIAG = (30, 60, 90, 120, 180, 270)
KEY = ["et_cc", "lesion_cc", "tumor_cc", "logratio_nadir_et_cc", "logratio_nadir_lesion_cc", "logratio_et_cc",
       "logratio_lesion_cc", "rate_lesion_cc_per30d", "rate_et_cc_per30d", "vol_pd_flag"]
N_REP = 5
_num = lambda s: pd.to_numeric(s, errors="coerce")


# ---------------------------------------------------------------- shared tables
def scan_table(index: pd.DataFrame) -> pd.DataFrame:
    """Every timepoint with a known MRI day, with measurements, patient progression dates and next/previous scans."""
    meas = pd.read_csv(MEASUREMENTS).drop(columns=["patient_id", "timepoint"])
    pdates = patient_dates(index)
    s = index[["scan_id", "patient_id", "timepoint", "complete", "clinical_grade_of_primary_brain_tumor"]].copy()
    s["mri_day"] = _num(index["days_from_diagnosis_to_mri"])
    s = s[s.mri_day.notna()].merge(meas.drop(columns="mri_day"), on="scan_id", how="left")
    s["grade4"] = s.pop("clinical_grade_of_primary_brain_tumor").astype(str).str.strip().eq("4")
    for c in ("progression_day", "progressor"):
        s[c] = pdates[c].reindex(s.patient_id).to_numpy()
    s = s.sort_values(["patient_id", "mri_day"]).reset_index(drop=True)
    s["has_meas"] = s.et_cc.notna()
    s["next_scan_id"] = s.groupby("patient_id").scan_id.shift(-1)
    s["next_mri_day"] = s.groupby("patient_id").mri_day.shift(-1)
    # progression scan: first MRI with a mask/measurements on or after the documented progression date
    cand = s[s.has_meas & s.progression_day.notna() & (s.mri_day >= s.progression_day)]
    prog = cand.groupby("patient_id").scan_id.first()
    s["is_progression_scan"] = s.scan_id.isin(prog)
    s["pre_progression"] = s.progression_day.notna() & (s.mri_day < s.progression_day)
    last_pre = s[s.pre_progression & s.has_meas].groupby("patient_id").scan_id.last()
    s["last_pre_progression"] = s.scan_id.isin(last_pre)
    s["next_is_progression_scan"] = s.next_scan_id.isin(prog)
    return s


def boot_auc(y, oof, groups, n_boot=500, seed=0):
    """Mean over repeats of pooled-OOF AUC with a patient-cluster bootstrap 95% CI."""
    oof = np.atleast_2d(oof)
    point = float(np.mean([roc_auc_score(y, o) for o in oof]))
    rng = np.random.default_rng(seed)
    idx_by = {g: np.where(groups == g)[0] for g in np.unique(groups)}
    pats = np.array(list(idx_by))
    draws = []
    for _ in range(n_boot):
        idx = np.concatenate([idx_by[p] for p in rng.choice(pats, len(pats))])
        if len(np.unique(y[idx])) == 2:
            draws.append(np.mean([roc_auc_score(y[idx], o[idx]) for o in oof]))
    lo, hi = np.percentile(draws, [2.5, 97.5])
    return point, float(lo), float(hi)


def single_auc(y, x):
    ok = ~np.isnan(x)
    return float(roc_auc_score(y[ok], x[ok])) if len(np.unique(y[ok])) == 2 else np.nan


# ---------------------------------------------------------------- 1 volume cross-check
def volume_crosscheck(index: pd.DataFrame):
    x = pd.read_excel(VOLUMES_XLSX, sheet_name=None)
    v = pd.concat([d.assign(label=SHEET_LABEL[k]) for k, d in x.items()]).dropna(subset=["Patient ID"])
    ids = v["Patient ID"].astype(str)
    v["patient_id"] = ids.str.extract(r"(PatientID_\d+)")[0]
    v["tp"] = ids.str.extract(r"Post-treatment_(\d+)")[0]  # 58 patients carry the timepoint in the ID
    v["n"] = v["Number Of Voxels"].astype(float)
    ix = index[index.has_mask.astype(bool)].copy()
    meas = pd.read_csv(MEASUREMENTS).set_index("scan_id")
    by_pat = {p: g for p, g in v.groupby("patient_id")}

    # permutation matrix: fraction of xlsx rows of label j whose voxel count equals our label k count for some scan
    perm = pd.DataFrame(index=[f"xlsx_label{j}" for j in range(1, 5)], columns=[f"ours_label{k}" for k in range(1, 5)])
    for j in range(1, 5):
        vj = v[v.label == j]
        for k in range(1, 5):
            have = set(zip(ix.patient_id, ix[f"label{k}_voxels"].astype(float)))
            perm.loc[f"xlsx_label{j}", f"ours_label{k}"] = np.mean([(p, n) in have for p, n in zip(vj.patient_id, vj.n)])

    # per scan x label: closest xlsx row of that patient (and timepoint, when the ID carries one). The xlsx has no
    # timepoint for most patients and duplicate rows for some, so this is a best-match (optimistic) alignment.
    rows = []
    for r in ix.itertuples():
        g = by_pat.get(r.patient_id)
        tp = r.timepoint.split("_")[1]
        if g is not None and g.tp.notna().any():
            g = g[g.tp == tp]
        for k in range(1, 5):
            ours = float(getattr(r, f"label{k}_voxels"))
            cand = g[g.label == k].n.to_numpy() if g is not None else np.array([])
            ref = float(cand[np.argmin(np.abs(cand - ours))]) if len(cand) else 0.0  # no row = label absent
            m_cc = meas.at[r.scan_id, f"{OURS[k]}_cc"] if r.scan_id in meas.index else np.nan
            rows.append({"scan_id": r.scan_id, "patient_id": r.patient_id, "label": k, "compartment": OURS[k],
                         "ours_voxels": ours, "measurements_cc": m_cc, "xlsx_voxels": ref,
                         "xlsx_rows_for_label": len(cand)})
    d = pd.DataFrame(rows)
    d["abs_diff_cc"] = (d.ours_voxels - d.xlsx_voxels).abs() / 1000
    d["rel_diff"] = (d.ours_voxels - d.xlsx_voxels) / d[["ours_voxels", "xlsx_voxels"]].max(axis=1).replace(0, np.nan)
    d["rel_diff"] = d.rel_diff.fillna(0.0)
    d["meas_vs_mask_cc"] = d.measurements_cc - d.ours_voxels / 1000
    # >10% disagreement, ignoring tiny compartments (< 0.1 cc absolute difference)
    d["disagree_10pct"] = (d.rel_diff.abs() > 0.10) & (d.abs_diff_cc >= 0.1)
    summ = []
    for k, g in d.groupby("compartment"):
        both = g[(g.ours_voxels > 0) | (g.xlsx_voxels > 0)]
        summ.append({"compartment": k, "n_scans": len(g), "n_nonzero": len(both),
                     "pearson_r": float(np.corrcoef(g.ours_voxels, g.xlsx_voxels)[0, 1]),
                     "spearman_r": float(stats.spearmanr(g.ours_voxels, g.xlsx_voxels)[0]),
                     "exact_match_frac": float((g.ours_voxels == g.xlsx_voxels).mean()),
                     "median_rel_diff_nonzero": float(both.rel_diff.median()),
                     "median_abs_rel_diff_nonzero": float(both.rel_diff.abs().median()),
                     "n_disagree_10pct": int(g.disagree_10pct.sum()),
                     "max_abs_meas_vs_mask_cc": float(g.meas_vs_mask_cc.abs().max())})
    summ = pd.DataFrame(summ)
    # intensity sanity of the label semantics (xlsx per-label mean intensities; our relative intensities)
    vt = v.pivot_table(index=["Patient ID"], columns="label", values="Image mean (brain_t1c)", aggfunc="mean")
    sem = {"xlsx_t1c_mean_label3_gt_label1_frac": float((vt[3] > vt[1]).mean()),
           "xlsx_t1c_mean_label3_gt_label2_frac": float((vt[3] > vt[2]).mean()),
           "ours_t1c_et_rel_median": float(meas.t1c_et_rel.median()),
           "ours_t1c_et_rel_gt1_frac": float((meas.t1c_et_rel.dropna() > 1).mean()),
           "ours_t1c_et_gt_netc_frac": float((meas.t1c_et_rel > meas.t1c_netc_rel)[meas.t1c_netc_rel.notna()
                                                                                    & meas.t1c_et_rel.notna()].mean()),
           "ours_flair_snfh_rel_median": float(meas.flair_snfh_rel.median()),
           "ours_flair_snfh_rel_gt1_frac": float((meas.flair_snfh_rel.dropna() > 1).mean())}
    return d, summ, perm.astype(float), sem


# ---------------------------------------------------------------- 2 concurrent detection
def paired_progression(s: pd.DataFrame) -> pd.DataFrame:
    """Progression scan vs the same patient's immediately preceding scan (with measurements)."""
    m = s[s.has_meas].copy()
    m["prev_scan_id"] = m.groupby("patient_id").scan_id.shift()
    p = m[m.is_progression_scan & m.prev_scan_id.notna()]
    prev = m.set_index("scan_id").loc[p.prev_scan_id]
    rows = []
    for subset, keep in (("all", np.ones(len(p), bool)),
                         ("gap<=30d", (p.mri_day - p.progression_day).to_numpy() <= 30),
                         ("grade4", p.grade4.to_numpy())):
        for c in KEY[:7]:
            a, b = p[c].to_numpy(float)[keep], prev[c].to_numpy(float)[keep]
            ok = ~(np.isnan(a) | np.isnan(b))
            a, b = a[ok], b[ok]
            w = stats.wilcoxon(a, b) if len(a) and np.any(a != b) else None
            rows.append({"subset": subset, "feature": c, "n_pairs": int(len(a)), "frac_larger_at_prog": float(np.mean(a > b)),
                         "frac_equal": float(np.mean(a == b)), "median_prog": float(np.median(a)),
                         "median_prev": float(np.median(b)), "median_diff": float(np.median(a - b)),
                         "wilcoxon_p": float(w.pvalue) if w else np.nan})
    return pd.DataFrame(rows)


def img_features(df: pd.DataFrame) -> pd.DataFrame:
    g = measurement_groups(df.reset_index(drop=True))
    return pd.concat([g["volumes"], g["delta"]], axis=1)


@counted_warnings
def cv_binary(job):
    """5x5 patient-grouped stratified CV, c3 ridge (or GBM) on imaging features; returns (name, oof repeats)."""
    name, X, y, groups, learner = job
    threadpool_limits(1)
    d = pd.DataFrame({"patient_id": groups, f"label_{c3.H}": y.astype(float)})
    oof = np.zeros((N_REP, len(y)))
    for r in range(N_REP):
        for tr, te in StratifiedGroupKFold(5, shuffle=True, random_state=r).split(X, y, groups):
            oof[r, te] = c3.fit_predict(SINGLE(learner), d, X, {}, None, tr, te, seed=r)
    return name, oof


def detection_jobs(s: pd.DataFrame, cohort: pd.DataFrame):
    """Binary tasks: (name, rows frame, y). Negatives / comparison rows are index-cohort scans."""
    idx = s.set_index("scan_id")
    prog = s[s.is_progression_scan & s.has_meas & s.complete.astype(bool)]
    cohort = cohort.merge(s[["scan_id", "n_prior_scans"]], on="scan_id", how="left")
    tasks = {}
    for pop in ("all_glioma", "grade4"):
        c = cohort if pop == "all_glioma" else cohort[cohort.grade4]
        pr = prog if pop == "all_glioma" else prog[prog.grade4]
        rows = pd.concat([pr[["scan_id", "patient_id"]].assign(y=1), c[["scan_id", "patient_id"]].assign(y=0)])
        tasks[f"2b_prog_scan_vs_index_scans|{pop}"] = rows
        pr30 = pr[(pr.mri_day - pr.progression_day) <= 30]
        tasks[f"2b_prog_scan(gap<=30d)_vs_index_scans|{pop}"] = pd.concat(
            [pr30[["scan_id", "patient_id"]].assign(y=1), c[["scan_id", "patient_id"]].assign(y=0)])
        neg = c[c.label_120 == 0]  # verified: no progression within 120 d of the scan
        tasks[f"2b_prog_scan_vs_label120_neg|{pop}"] = pd.concat(
            [pr[["scan_id", "patient_id"]].assign(y=1), neg[["scan_id", "patient_id"]].assign(y=0)])
        prp = pr[pr.n_prior_scans > 0]
        cp = c[c.n_prior_scans > 0]
        tasks[f"2b_prog_scan_vs_index_scans(both_with_prior)|{pop}"] = pd.concat(
            [prp[["scan_id", "patient_id"]].assign(y=1), cp[["scan_id", "patient_id"]].assign(y=0)])
        lab = c[c.label_120.notna()]
        tasks[f"ref_label120_forward|{pop}"] = lab[["scan_id", "patient_id"]].assign(y=lab.label_120.astype(int))
        pg = c[c.event.astype(bool)]
        tasks[f"5_last_pre_prog_vs_earlier|{pop}"] = pg[["scan_id", "patient_id"]].assign(
            y=idx.loc[pg.scan_id, "last_pre_progression"].astype(int).to_numpy())
    return {k: v.reset_index(drop=True) for k, v in tasks.items()}


def single_feature_table(s, tasks):
    m = s.set_index("scan_id")
    rows = []
    for name, t in tasks.items():
        y = t.y.to_numpy()
        for c in KEY + ["mri_day"]:
            rows.append({"task": name, "feature": c, "n_pos": int(y.sum()), "n": len(y),
                         "auc": single_auc(y, m.loc[t.scan_id, c].to_numpy(float))})
    return pd.DataFrame(rows)


def continuity(s: pd.DataFrame) -> pd.DataFrame:
    """Consecutive-scan |log((v + 0.1) / (v_prev + 0.1))| by gap: a sound series changes less over shorter gaps."""
    m = s[s.has_meas].copy()
    m["gap"] = m.mri_day - m.groupby("patient_id").mri_day.shift()
    m["gap_bin"] = pd.cut(m.gap, [-1, 14, 45, 90, 180, 5000]).astype(str)
    rows = []
    for c in ("et_cc", "lesion_cc", "snfh_cc", "rc_cc"):
        m[f"abslog_{c}"] = np.abs(np.log((m[c] + 0.1) / (m.groupby("patient_id")[c].shift() + 0.1)))
    q = m[m.gap.notna()]
    for b, g in q.groupby("gap_bin"):
        rows.append({"gap_bin": b, "n_pairs": len(g), **{f"median_abslog_{c}": float(g[f"abslog_{c}"].median())
                                                          for c in ("et_cc", "lesion_cc", "snfh_cc", "rc_cc")}})
    r = stats.spearmanr(q.gap, q.abslog_lesion_cc)
    rows.append({"gap_bin": "spearman(gap, abslog_lesion)", "n_pairs": len(q), "median_abslog_lesion_cc": float(r[0]),
                 "median_abslog_et_cc": float(r[1])})  # second value = p
    return pd.DataFrame(rows)


def near_duplicates(index: pd.DataFrame, tol: float = 0.03) -> pd.DataFrame:
    """Scan pairs from DIFFERENT patients whose 4 compartment volumes agree within tol in log1p(cc)."""
    i = index[index.has_mask.astype(bool)].reset_index(drop=True)
    L = np.log1p(i[[f"label{k}_voxels" for k in range(1, 5)]].to_numpy(float) / 1000)
    rows = []
    for a in range(len(i)):
        d = np.abs(L - L[a]).max(1)
        for b in np.where(d < tol)[0]:
            if b > a and i.patient_id[a] != i.patient_id[b] and L[a].sum() > 1:
                rows.append({"scan_a": i.scan_id[a], "scan_b": i.scan_id[b], "max_dlog": d[b], "identical": d[b] == 0,
                             "day_a": i.days_from_diagnosis_to_mri[a], "day_b": i.days_from_diagnosis_to_mri[b]})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- 3 alignment
def alignment(s: pd.DataFrame, cohort: pd.DataFrame, index: pd.DataFrame):
    pdates = patient_dates(index)
    prog = pdates[pdates.progression_day.notna()]
    mri = s.groupby("patient_id").mri_day.apply(np.asarray)
    rows = []
    for p, r in prog.iterrows():
        days = mri.get(p, np.array([]))
        d = days - r.progression_day
        after = d[d >= 0]
        before = d[d < 0]
        rows.append({"patient_id": p, "progression_day": r.progression_day,
                     "nearest_mri_offset": float(d[np.argmin(np.abs(d))]) if len(d) else np.nan,
                     "first_mri_on_after_offset": float(after.min()) if len(after) else np.nan,
                     "last_mri_before_offset": float(before.max()) if len(before) else np.nan,
                     "n_mri_after": int(len(after))})
    a = pd.DataFrame(rows)
    nz = a.nearest_mri_offset.notna()
    c = cohort.merge(s[["scan_id", "next_mri_day", "next_is_progression_scan", "last_pre_progression"]], on="scan_id")
    c["t_prog"] = c.progression_day - c.days_from_diagnosis_to_mri
    c["interval_to_next"] = c.next_mri_day - c.days_from_diagnosis_to_mri
    lab = c[c.label_120.notna()]
    pos, neg = lab[lab.label_120 == 1], lab[lab.label_120 == 0]
    ct = pd.crosstab(lab.label_120, lab.next_is_progression_scan)
    kappa = _kappa(lab.label_120.to_numpy(int), lab.next_is_progression_scan.to_numpy(int))
    summ = {
        "n_progressors_with_date": int(len(a)), "n_with_any_mri": int(nz.sum()),
        "frac_prog_date_within_7d_of_mri": float((a.nearest_mri_offset[nz].abs() <= 7).mean()),
        "frac_prog_date_exactly_on_mri": float((a.nearest_mri_offset[nz] == 0).mean()),
        "frac_prog_date_within_30d_of_mri": float((a.nearest_mri_offset[nz].abs() <= 30).mean()),
        "frac_no_mri_on_after_prog_date": float(a.first_mri_on_after_offset[nz].isna().mean()),
        "median_first_mri_on_after_offset": float(a.first_mri_on_after_offset.median()),
        "positives_label120": int(len(pos)),
        "pos_t_prog_median": float(pos.t_prog.median()), "pos_t_prog_iqr": pos.t_prog.quantile([.25, .75]).tolist(),
        "pos_interval_to_next_median": float(pos.interval_to_next.median()),
        "pos_frac_last_pre_progression_scan": float(pos.last_pre_progression.mean()),
        "pos_frac_next_scan_is_progression_scan": float(pos.next_is_progression_scan.mean()),
        "neg_frac_next_scan_is_progression_scan": float(neg.next_is_progression_scan.mean()),
        "pos_frac_t_prog_le_interval_to_next": float((pos.t_prog <= pos.interval_to_next).mean()),
        "label120_vs_next_is_prog_agreement": float((lab.label_120 == lab.next_is_progression_scan).mean()),
        "label120_vs_next_is_prog_kappa": kappa,
        "crosstab_label120_x_next_is_prog": {f"{int(i)}|{bool(j)}": int(ct.loc[i, j]) for i in ct.index for j in ct.columns},
        "all_scan_interval_median": float((s.next_mri_day - s.mri_day).median()),
    }
    return a, c, summ


def _kappa(a, b):
    po = np.mean(a == b)
    pe = np.mean(a) * np.mean(b) + (1 - np.mean(a)) * (1 - np.mean(b))
    return float((po - pe) / (1 - pe))


def plot_alignment(a, c, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    pos = c[c.label_120 == 1]
    fig, ax = plt.subplots(1, 3, figsize=(14, 3.8))
    ax[0].hist(a.nearest_mri_offset.dropna().clip(-200, 200), bins=np.arange(-200, 205, 7), color="#5b8def")
    ax[0].set_title("progression date: offset of nearest MRI (d, clipped ±200)", fontsize=9)
    ax[1].hist(pos.t_prog, bins=np.arange(0, 125, 7), color="#e76f51", alpha=.8, label="progression − index scan")
    ax[1].hist(pos.interval_to_next.dropna().clip(upper=250), bins=np.arange(0, 255, 7), color="#4a4a4a", alpha=.45,
               label="next scan − index scan")
    ax[1].legend(fontsize=8)
    ax[1].set_title(f"label_120 positives (n={len(pos)}): days", fontsize=9)
    lab = c[c.label_120.notna()]
    ax[2].scatter(lab.interval_to_next.clip(upper=400), lab.t_prog.clip(upper=400), c=lab.label_120, cmap="coolwarm",
                  s=12)
    ax[2].plot([0, 400], [0, 400], color="#8c959f", lw=1, ls="--")
    ax[2].axhline(120, color="#8c959f", lw=1)
    ax[2].set_xlabel("days to next MRI")
    ax[2].set_ylabel("days to progression (clip 400)")
    ax[2].set_title("labelled index scans (red = positive)", fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


# ---------------------------------------------------------------- 4 horizon curve
_HCACHE = {}


def horizon_context(pop):
    if pop not in _HCACHE:
        cohort = load_cohort(pop).copy()
        ev, t, fu = cohort.event.to_numpy(bool), cohort.time_to_event.to_numpy(float), cohort.follow_up_days.to_numpy(float)
        for h in HORIZONS_DIAG:
            lab = horizon_label(ev, np.where(ev, t, np.nan), fu, h)
            if f"label_{h}" in cohort:
                assert np.array_equal(np.nan_to_num(lab, nan=-1), np.nan_to_num(cohort[f"label_{h}"], nan=-1)), h
            cohort[f"label_{h}"], cohort[f"naive_label_{h}"] = lab, (ev & (t <= h)).astype(int)
        img = img_features(cohort)
        img.index = cohort.index
        cp = pd.concat([clinical(cohort), phase(cohort)], axis=1)
        X = {"imaging": img, "clinical+phase": cp, "clinical+phase+imaging": pd.concat([cp, img], axis=1)}
        _HCACHE[pop] = (cohort, load_folds(), X)
    return _HCACHE[pop]


@counted_warnings
def run_horizon(job):
    pop, h, model = job
    threadpool_limits(1)
    cohort, folds, X = horizon_context(pop)
    c3.H = h
    oof = np.zeros((folds.repeat.nunique(), len(cohort)))
    for r in range(oof.shape[0]):
        f = c3._fold_ids(cohort, folds, r)
        for k in np.unique(f):
            tr, te = np.where(f != k)[0], np.where(f == k)[0]
            oof[r, te] = c3.fit_predict(SINGLE("ridge"), cohort, X[model], {}, None, tr, te, seed=r)
    return job, oof


def plot_horizon(hc, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.8), sharey=True)
    colors = {"imaging": "#2a9d8f", "clinical+phase": "#4a4a4a", "clinical+phase+imaging": "#e76f51"}
    for ax, pop in zip(axes, ("grade4", "all_glioma")):
        for m, g in hc[hc.population == pop].groupby("model"):
            ax.errorbar(g.horizon + {"imaging": -4, "clinical+phase": 0}.get(m, 4), g.auc_ipcw,
                        yerr=[g.auc_ipcw - g.auc_ipcw_lo, g.auc_ipcw_hi - g.auc_ipcw], marker="o", capsize=2,
                        color=colors[m], label=m)
        ax.axhline(0.5, color="#8c959f", ls="--", lw=1)
        ax.set_xticks(HORIZONS_DIAG)
        ax.set_xlabel("horizon H (days)")
        ax.set_title(pop, fontsize=10)
    axes[0].set_ylabel("IPCW AUC(H), ridge, 5x5 CV")
    axes[0].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


# ---------------------------------------------------------------- 6 visual QA
COLORS = {1: "#ffd166", 2: "#06d6a0", 3: "#ef476f", 4: "#118ab2"}


def overlay(scan_id, title, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    pid, tp = scan_id.rsplit("_Timepoint_", 1)
    p = mu_scan_paths(pid, f"Timepoint_{tp}")
    mask = np.rint(np.asarray(nib.load(str(p["mask"])).dataobj)).astype(int)
    t1c, flair = (np.asarray(nib.load(str(p[k])).dataobj).astype(float) for k in ("t1c", "flair"))
    lesion = np.isin(mask, (1, 2, 3)).sum(axis=(0, 1))
    z = int(np.argmax(lesion)) if lesion.any() else mask.shape[2] // 2  # axial slice with the largest lesion area
    fig, ax = plt.subplots(1, 3, figsize=(10.5, 3.8))
    for a, img, nm in ((ax[0], t1c, "T1c"), (ax[1], t1c, "T1c + mask"), (ax[2], flair, "FLAIR + mask")):
        sl = np.rot90(img[:, :, z])
        a.imshow(sl, cmap="gray", vmin=0, vmax=np.percentile(sl[sl > 0], 99.5) if (sl > 0).any() else 1)
        if nm != "T1c":
            for lab, col in COLORS.items():
                m = np.rot90(mask[:, :, z] == lab)
                if m.any():
                    a.contour(m, levels=[0.5], colors=col, linewidths=0.9)
        a.set_title(nm, fontsize=9)
        a.axis("off")
    counts = {k: int((mask == k).sum()) for k in COLORS}
    fig.suptitle(f"{title}  z={z}  NETC(1,yellow)={counts[1]} SNFH(2,green)={counts[2]} ET(3,red)={counts[3]} "
                 f"RC(4,blue)={counts[4]} vox", fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


def visual_qa(s, cohort, out, seed=0):
    rng = np.random.default_rng(seed)
    prog = s[s.is_progression_scan & s.has_meas & s.complete.astype(bool)].scan_id.to_numpy()
    picks = [("progression_scan", x) for x in rng.choice(prog, 4, replace=False)]
    picks += [("index_pos120", x) for x in rng.choice(cohort[cohort.label_120 == 1].scan_id, 4, replace=False)]
    picks += [("index_neg120", x) for x in rng.choice(cohort[cohort.label_120 == 0].scan_id, 4, replace=False)]
    out.mkdir(exist_ok=True)
    m = s.set_index("scan_id")
    rows = []
    for kind, sid in picks:
        f = out / f"{kind}__{sid}.png"
        overlay(sid, f"{kind}: {sid}", f)
        rows.append({"kind": kind, "scan_id": sid, "png": f.name, **m.loc[sid, ["et_cc", "netc_cc", "snfh_cc", "rc_cc"]]})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- main
def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="prism.analyses.diagnostics_imaging", description=__doc__)
    ap.add_argument("--workers", type=int, default=24)
    ap.add_argument("--n-boot", type=int, default=500)
    a = ap.parse_args(argv)
    OUT.mkdir(parents=True, exist_ok=True)
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    index, cohort = load_index(), load_cohort("all_glioma")
    s = scan_table(index)
    info = {}

    # 1
    vol, vsum, perm, sem = volume_crosscheck(index)
    vol.to_csv(OUT / "volume_crosscheck_scans.csv", index=False)
    vol[vol.disagree_10pct].to_csv(OUT / "volume_disagreements.csv", index=False)
    vsum.to_csv(OUT / "volume_crosscheck_summary.csv", index=False)
    perm.to_csv(OUT / "label_permutation_match.csv")
    info["1_label_semantics"] = sem
    print(vsum.round(4).to_string(index=False), "\n", perm.round(3).to_string(), "\n", sem, flush=True)

    # 2a, 3, 5 tables
    pair = paired_progression(s)
    pair.to_csv(OUT / "paired_progression_vs_previous.csv", index=False)
    print(pair.round(4).to_string(index=False), flush=True)
    s.to_csv(OUT / "scan_table.csv", index=False)
    cont = continuity(s)
    cont.to_csv(OUT / "volume_continuity_by_gap.csv", index=False)
    nd = near_duplicates(index)
    nd.to_csv(OUT / "cross_patient_near_duplicates.csv", index=False)
    print(cont.round(3).to_string(index=False), "\n", nd.to_string(index=False), flush=True)
    al, c_al, al_sum = alignment(s, cohort, index)
    al.to_csv(OUT / "progression_date_vs_mri.csv", index=False)
    c_al[["scan_id", "patient_id", "label_120", "t_prog", "interval_to_next", "next_is_progression_scan",
          "last_pre_progression"]].to_csv(OUT / "index_scan_alignment.csv", index=False)
    plot_alignment(al, c_al, OUT / "alignment.png")
    info["3_alignment"] = al_sum
    print(json.dumps(al_sum, indent=1), flush=True)

    # 2b + 5 + forward reference (imaging-only, patient-grouped CV)
    tasks = detection_jobs(s, cohort)
    sf = single_feature_table(s, tasks)
    sf.to_csv(OUT / "single_feature_auc.csv", index=False)
    ids = pd.concat(tasks.values()).scan_id.unique()
    feats = img_features(pd.DataFrame({"scan_id": ids})).set_axis(ids)
    jobs = [(f"{n}|{l}", feats.loc[t.scan_id].reset_index(drop=True), t.y.to_numpy(), t.patient_id.to_numpy(), l)
            for n, t in tasks.items() for l in ("ridge", "gbm")]
    hjobs = [(p, h, m) for p in ("grade4", "all_glioma") for h in HORIZONS_DIAG
             for m in ("imaging", "clinical+phase", "clinical+phase+imaging")]
    with ProcessPoolExecutor(a.workers) as ex:
        det = list(ex.map(cv_binary, jobs))
        hres = list(ex.map(run_horizon, hjobs))
    drows = []
    for (name, oof), job in zip(det, jobs):
        task, pop, learner = name.split("|")
        auc, lo, hi = boot_auc(job[2], oof, job[3], a.n_boot)
        drows.append({"task": task, "population": pop, "learner": learner, "n": len(job[2]), "n_pos": int(job[2].sum()),
                      "n_patients": len(np.unique(job[3])), "auc": auc, "auc_lo": lo, "auc_hi": hi})
    det_df = pd.DataFrame(drows)
    det_df.to_csv(OUT / "detection_auc.csv", index=False)
    print(det_df.round(3).to_string(index=False), flush=True)

    # 4
    hrows = []
    for pop in ("grade4", "all_glioma"):
        cohort_p, _, _ = horizon_context(pop)
        for h in HORIZONS_DIAG:
            oofs = {m: o for (p, hh, m), o in hres if p == pop and hh == h}
            ev = evaluate_repeated(cohort_p, oofs, h, reference="clinical+phase", n_boot=a.n_boot)
            lab = cohort_p[f"label_{h}"]
            for m, r in ev.iterrows():
                hrows.append({"population": pop, "horizon": h, "model": m, "events": int((lab == 1).sum()),
                              "non_events": int((lab == 0).sum()), "censored": int(lab.isna().sum()),
                              **{k: r.get(k, np.nan) for k in ("auc_ipcw", "auc_ipcw_lo", "auc_ipcw_hi", "auc_verified",
                                                               "auc_ipcw_repeat_sd", "d_auc_ipcw_vs_clinical+phase",
                                                               "d_auc_ipcw_lo", "d_auc_ipcw_hi")}})
    hc = pd.DataFrame(hrows)
    hc.to_csv(OUT / "horizon_curve.csv", index=False)
    plot_horizon(hc, OUT / "horizon_curve.png")
    print(hc.round(3).to_string(index=False), flush=True)

    # 6
    qa = visual_qa(s, cohort, OUT / "qa")
    qa.to_csv(OUT / "qa" / "qa_scans.csv", index=False)
    (OUT / "run_info.json").write_text(json.dumps(info, indent=1, default=float))
    print(f"-> {OUT}")


if __name__ == "__main__":
    main()
