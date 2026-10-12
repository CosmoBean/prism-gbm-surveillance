"""Does ONE consistent segmenter make the MU longitudinal volumes less noisy and the imaging positive controls pass?

Segmenters  mu       shipped MU-Glioma-Post masks (outputs/features/measurements.csv)
            brats21  MONAI BraTS21 SwinUNETR re-segmentation (prism.features.reseg; primary)
            bsf      BrainSegFounder BraTS-finetune re-segmentation (second segmenter)
For brats21/bsf the measurement table is rebuilt with measurements.py logic on the new ET/NETC/SNFH labels; the
resection cavity (RC, which BraTS models do not segment) is kept from the MU mask wherever the new mask is background.
Compartments: ET; TC = ET|NETC (`tumor_cc`); WT = ET|NETC|SNFH (`lesion_cc`).

  2 agreement     Dice ET/TC/WT vs MU, volume correlation (log1p cc)
  3 consistency   consecutive-scan |log((v+0.1)/(v0+0.1))| for gaps <= 14 / <= 30 d, with and without pairs that
                  straddle a likely surgery (MU cavity grows >= 1 cc and >= 1.5x, or brachytherapy insertion between);
                  Spearman(|log change|, gap). Paired patient-cluster bootstrap of the median difference vs mu.
  4 controls      diagnostics_imaging logic re-run per segmenter: (a) progression scan vs previous scan, overall and
                  by MU progression type (1 imaging / 2 clinical / 3 both); (b) imaging-only (volumes + delta)
                  detection AUC, 5x5 patient-grouped CV, paired patient-cluster bootstrap of the AUC difference vs mu;
                  (c) forward label_120 imaging-only plain AUC and IPCW AUC(120) (repo folds, evaluate_repeated).
  5 QA            T1c/FLAIR overlays, MU vs new contours, 8 scans

    python -m prism.analyses.reseg_eval [--workers 48 --n-boot 1000]
    -> $PRISM_OUTPUTS/results/analyses/reseg/
"""

from __future__ import annotations

import argparse
import json
import time
import warnings
from concurrent.futures import ProcessPoolExecutor

import nibabel as nib
import numpy as np
import pandas as pd
from scipy import ndimage, stats
from sklearn.metrics import roc_auc_score

import prism.analyses.diagnostics_imaging as di
import prism.features.measurements as meas_mod
from prism.config import LABEL_ET, LABEL_NETC, LABEL_RC, LABEL_SNFH, MEASUREMENTS, RESULTS, mu_scan_paths
from prism.data.mu import load_cohort, load_index
from prism.features.measurements import NAWM_MARGIN_MM, NEAR_CAVITY_MM, add_deltas, reference_mask
from prism.features.reseg import SEG, seg_path, volumes_path

OUT = RESULTS / "analyses" / "reseg"
SEGMENTERS = ("mu", "brats21", "bsf")
COMP = {"et": "et_cc", "tc": "tumor_cc", "wt": "lesion_cc"}
PAIRED = ["et_cc", "tumor_cc", "lesion_cc", "logratio_nadir_et_cc", "logratio_nadir_tumor_cc", "logratio_nadir_lesion_cc"]
TASKS = ("2b_prog_scan_vs_index_scans", "2b_prog_scan_vs_label120_neg", "2b_prog_scan_vs_index_scans(both_with_prior)",
         "ref_label120_forward")
PROG_TYPE = {1: "imaging", 2: "clinical", 3: "both"}
_num = lambda s: pd.to_numeric(s, errors="coerce")


def table_path(seg: str):
    return MEASUREMENTS if seg == "mu" else OUT / f"measurements_{seg}.csv"


def use_table(seg: str) -> None:
    """Point measurements.load_measurements and diagnostics_imaging.scan_table at this segmenter's table."""
    di.MEASUREMENTS = meas_mod.MEASUREMENTS = table_path(seg)
    di._HCACHE.clear()


# ---------------------------------------------------------------- measurement tables from the new masks
def scan_concepts_seg(args) -> dict:
    """measurements.scan_concepts on a re-segmented label map (RC from the MU mask where the new map is 0)."""
    sid, model = args
    pid, tp = sid.split("_Timepoint_")
    paths = mu_scan_paths(pid, f"Timepoint_{tp}")
    row = {"scan_id": sid, "patient_id": pid, "timepoint": f"Timepoint_{tp}"}
    try:
        mask = np.asarray(nib.load(str(seg_path(sid, model))).dataobj).astype(np.uint8)
        img = nib.load(str(paths["mask"]))
        spacing = tuple(float(z) for z in img.header.get_zooms()[:3])
        mu = np.rint(np.asarray(img.dataobj)).astype(np.uint8)
        t1c = np.asarray(nib.load(str(paths["t1c"])).dataobj).astype(np.float32)
        flair = np.asarray(nib.load(str(paths["flair"])).dataobj).astype(np.float32)
    except FileNotFoundError:
        return row
    mask[(mask == 0) & (mu == LABEL_RC)] = LABEL_RC
    et, netc, snfh, rc = (mask == LABEL_ET), (mask == LABEL_NETC), (mask == LABEL_SNFH), (mask == LABEL_RC)
    tumor, lesion = et | netc, et | netc | snfh
    cc = lambda m: float(m.sum()) / 1000.0
    row.update(et_cc=cc(et), netc_cc=cc(netc), snfh_cc=cc(snfh), rc_cc=cc(rc), tumor_cc=cc(tumor), lesion_cc=cc(lesion))
    row["et_fraction_of_tumor"] = row["et_cc"] / row["tumor_cc"] if row["tumor_cc"] > 0 else np.nan
    row["snfh_to_tumor_ratio"] = row["snfh_cc"] / row["tumor_cc"] if row["tumor_cc"] > 0 else np.nan
    row["has_cavity"] = float(rc.any())
    labels, n = ndimage.label(et, structure=np.ones((3, 3, 3)))
    sizes = np.bincount(labels.ravel())[1:] if n else np.array([])
    row["et_n_components"] = float((sizes >= 10).sum())
    row["et_largest_component_fraction"] = float(sizes.max() / sizes.sum()) if n else np.nan
    row["et_max_axial_mm2"] = float(et.sum(axis=(0, 1)).max()) if et.any() else 0.0
    if rc.any() and et.any():
        dist_to_rc = ndimage.distance_transform_edt(~rc)
        row["et_near_cavity_fraction"] = float((dist_to_rc[et] <= NEAR_CAVITY_MM).mean())
        row["et_cavity_distance_mm_p50"] = float(np.median(dist_to_rc[et]))
    else:
        row["et_near_cavity_fraction"] = row["et_cavity_distance_mm_p50"] = np.nan
    brain = (t1c > 0) & (flair > 0)
    nab = reference_mask(brain, lesion | rc, NAWM_MARGIN_MM, spacing)
    ref_t1c = np.median(t1c[nab]) if nab.sum() > 1000 else np.nan
    ref_flair = np.median(flair[nab]) if nab.sum() > 1000 else np.nan
    rel = lambda im, m, ref: float(np.median(im[m]) / ref) if m.sum() >= 10 and ref and np.isfinite(ref) else np.nan
    row.update(t1c_et_rel=rel(t1c, et, ref_t1c), t1c_netc_rel=rel(t1c, netc, ref_t1c),
               flair_snfh_rel=rel(flair, snfh, ref_flair), flair_netc_rel=rel(flair, netc, ref_flair),
               t1c_et_p90_rel=float(np.percentile(t1c[et], 90) / ref_t1c) if et.sum() >= 10 and np.isfinite(ref_t1c) else np.nan)
    return row


def build_table(model: str, workers: int) -> pd.DataFrame:
    old = pd.read_csv(MEASUREMENTS)[["scan_id", "mri_day"]]
    with ProcessPoolExecutor(workers) as ex:
        c = pd.DataFrame(list(ex.map(scan_concepts_seg, [(s, model) for s in old.scan_id], chunksize=4)))
    c = c.merge(old, on="scan_id")
    c = c[c.et_cc.notna()]
    m = c.merge(add_deltas(c), on="scan_id", how="left")
    m.to_csv(table_path(model), index=False)
    return m


# ---------------------------------------------------------------- 2 agreement
def agreement(tables: dict) -> pd.DataFrame:
    rows = []
    for seg in SEGMENTERS[1:]:
        v = pd.read_csv(volumes_path(seg))
        for c, col in COMP.items():
            d = v[f"dice_{c}"]
            both = (v[f"mu_{c}_voxels"] > 0) & (v[f"new_{c}_voxels"] > 0)
            a, b = np.log1p(v[f"mu_{c}_voxels"] / 1000), np.log1p(v[f"new_{c}_voxels"] / 1000)
            rows.append({"segmenter": seg, "compartment": c, "n_scans": len(v), "dice_median": d.median(),
                         "dice_q25": d.quantile(.25), "dice_q75": d.quantile(.75), "dice_mean": d.mean(),
                         "frac_dice_lt_0.5": float((d < 0.5).mean()), "n_both_nonzero": int(both.sum()),
                         "pearson_log1p_cc": float(np.corrcoef(a, b)[0, 1]), "spearman_cc": float(stats.spearmanr(a, b)[0]),
                         "median_ratio_new_over_mu": float((v[f"new_{c}_voxels"] / v[f"mu_{c}_voxels"])[both].median()),
                         "frac_mu_zero_new_nonzero": float(((v[f"mu_{c}_voxels"] == 0) & (v[f"new_{c}_voxels"] > 0)).mean()),
                         "frac_mu_nonzero_new_zero": float(((v[f"mu_{c}_voxels"] > 0) & (v[f"new_{c}_voxels"] == 0)).mean())})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- 3 longitudinal consistency
def consecutive_pairs(tables: dict, index: pd.DataFrame) -> pd.DataFrame:
    """One row per consecutive scan pair (same scans for every segmenter) with |log change| per segmenter."""
    mu = tables["mu"].sort_values(["patient_id", "mri_day"])
    g = mu.groupby("patient_id")
    p = pd.DataFrame({"patient_id": mu.patient_id, "scan_id": mu.scan_id, "prev_scan_id": g.scan_id.shift(),
                      "gap": mu.mri_day - g.mri_day.shift(), "mri_day": mu.mri_day, "prev_day": g.mri_day.shift(),
                      "rc": mu.rc_cc, "rc_prev": g.rc_cc.shift()}).dropna(subset=["prev_scan_id"])
    brachy = _num(index.drop_duplicates("patient_id").set_index("patient_id")[
        "clinical_number_of_days_from_diagnosis_to_the_day_of_insertion_of_brachytherapy"])
    b = brachy.reindex(p.patient_id).to_numpy()
    p["cavity_jump"] = ((p.rc - p.rc_prev) >= 1) & ((p.rc + 0.1) >= 1.5 * (p.rc_prev + 0.1))
    p["brachy_between"] = (b > p.prev_day.to_numpy()) & (b <= p.mri_day.to_numpy())
    p["surgery_between"] = p.cavity_jump | p.brachy_between
    for seg, t in tables.items():
        t = t.set_index("scan_id")
        for c, col in COMP.items():
            cur, old = t.loc[p.scan_id, col].to_numpy(), t.loc[p.prev_scan_id, col].to_numpy()
            p[f"abslog_{c}|{seg}"] = np.abs(np.log((cur + 0.1) / (old + 0.1)))
    return p.reset_index(drop=True)


def _cluster_boot(df, fn, n_boot, seed=0):
    rng = np.random.default_rng(seed)
    by = {g: np.where(df.patient_id.to_numpy() == g)[0] for g in df.patient_id.unique()}
    pats = np.array(list(by))
    out = []
    for _ in range(n_boot):
        out.append(fn(df.iloc[np.concatenate([by[q] for q in rng.choice(pats, len(pats))])]))
    return np.nanpercentile(out, [2.5, 97.5])


def consistency(p: pd.DataFrame, n_boot: int) -> pd.DataFrame:
    rows = []
    for excl in (False, True):
        q0 = p[~p.surgery_between] if excl else p
        for win, q in (("gap<=14d", q0[q0.gap <= 14]), ("gap<=30d", q0[q0.gap <= 30]), ("gap>90d", q0[q0.gap > 90]),
                       ("all", q0)):
            for c in COMP:
                for seg in SEGMENTERS:
                    col = f"abslog_{c}|{seg}"
                    r = {"exclude_surgery": excl, "window": win, "compartment": c, "segmenter": seg, "n_pairs": len(q),
                         "n_patients": q.patient_id.nunique(), "median_abslog": q[col].median(),
                         "median_fold_change": float(np.exp(q[col].median())),
                         "frac_fold_ge_1.5": float((q[col] >= np.log(1.5)).mean()),
                         "spearman_abslog_vs_gap": float(stats.spearmanr(q.gap, q[col])[0]) if len(q) > 10 else np.nan,
                         "spearman_p": float(stats.spearmanr(q.gap, q[col])[1]) if len(q) > 10 else np.nan}
                    if seg != "mu" and len(q) > 5:
                        ref = f"abslog_{c}|mu"
                        r["d_median_abslog_vs_mu"] = q[col].median() - q[ref].median()
                        r["d_lo"], r["d_hi"] = _cluster_boot(q, lambda d: d[col].median() - d[ref].median(), n_boot)
                        r["frac_pairs_less_noisy_than_mu"] = float((q[col] < q[ref]).mean())
                    rows.append(r)
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- 4a paired progression vs previous
def paired_pairs(s: pd.DataFrame) -> pd.DataFrame:
    m = s[s.has_meas].copy()
    m["prev_scan_id"] = m.groupby("patient_id").scan_id.shift()
    return m[m.is_progression_scan & m.prev_scan_id.notna()][["scan_id", "prev_scan_id", "patient_id", "grade4"]]


def paired_table(pairs: pd.DataFrame, tables: dict, ptype: pd.Series, n_boot: int) -> pd.DataFrame:
    pairs = pairs.assign(ptype=ptype.reindex(pairs.patient_id).to_numpy())
    subsets = {"all": np.ones(len(pairs), bool), "grade4": pairs.grade4.to_numpy(bool),
               **{f"type{k}_{v}": (pairs.ptype == k).to_numpy() for k, v in PROG_TYPE.items()}}
    rng = np.random.default_rng(0)
    rows = []
    for sub, keep in subsets.items():
        for f in PAIRED:
            larger, base = {}, None
            for seg in SEGMENTERS:
                t = tables[seg].set_index("scan_id")
                a, b = t.loc[pairs.scan_id, f].to_numpy(float)[keep], t.loc[pairs.prev_scan_id, f].to_numpy(float)[keep]
                ok = ~(np.isnan(a) | np.isnan(b))
                base = ok if base is None else base & ok
                larger[seg] = (a, b)
            for seg in SEGMENTERS:
                a, b = (x[base] for x in larger[seg])
                w = stats.wilcoxon(a, b) if len(a) and np.any(a != b) else None
                r = {"subset": sub, "feature": f, "segmenter": seg, "n_pairs": int(len(a)),
                     "frac_larger_at_prog": float(np.mean(a > b)) if len(a) else np.nan,
                     "median_diff": float(np.median(a - b)) if len(a) else np.nan,
                     "wilcoxon_p": float(w.pvalue) if w else np.nan}
                if seg != "mu" and len(a) > 3:  # one pair per patient: bootstrap over pairs
                    am, bm = (x[base] for x in larger["mu"])
                    dn, dm = (a > b).astype(float), (am > bm).astype(float)
                    r["d_frac_vs_mu"] = dn.mean() - dm.mean()
                    bs = [(dn[i] - dm[i]).mean() for i in (rng.integers(0, len(a), len(a)) for _ in range(n_boot))]
                    r["d_lo"], r["d_hi"] = np.percentile(bs, [2.5, 97.5])
                rows.append(r)
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- 4b/c detection + forward
def boot_pair(y, oa, ob, groups, n_boot=1000, seed=0):
    """Paired patient-cluster bootstrap of mean-over-repeats AUC(b) - AUC(a)."""
    auc = lambda o, i: np.mean([roc_auc_score(y[i], r[i]) for r in o])
    rng = np.random.default_rng(seed)
    by = {g: np.where(groups == g)[0] for g in np.unique(groups)}
    pats = np.array(list(by))
    d = []
    for _ in range(n_boot):
        i = np.concatenate([by[p] for p in rng.choice(pats, len(pats))])
        if len(np.unique(y[i])) == 2:
            d.append(auc(ob, i) - auc(oa, i))
    full = np.arange(len(y))
    return float(auc(ob, full) - auc(oa, full)), *np.percentile(d, [2.5, 97.5])


def detection(tables, index, cohort, workers, n_boot):
    use_table("mu")
    tasks = {k: v for k, v in di.detection_jobs(di.scan_table(index), cohort).items() if k.split("|")[0] in TASKS}
    ids = pd.concat(tasks.values()).scan_id.unique()
    oofs = {}
    for seg in SEGMENTERS:
        use_table(seg)
        feats = di.img_features(pd.DataFrame({"scan_id": ids})).set_axis(ids)
        jobs = [(f"{n}|{l}|{seg}", feats.loc[t.scan_id].reset_index(drop=True), t.y.to_numpy(), t.patient_id.to_numpy(), l)
                for n, t in tasks.items() for l in ("ridge", "gbm")]
        with ProcessPoolExecutor(workers) as ex:
            oofs.update(dict(ex.map(di.cv_binary, jobs)))
    use_table("mu")
    rows = []
    for n, t in tasks.items():
        task, pop = n.split("|")
        y, g = t.y.to_numpy(), t.patient_id.to_numpy()
        for l in ("ridge", "gbm"):
            for seg in SEGMENTERS:
                o = oofs[f"{n}|{l}|{seg}"]
                auc, lo, hi = di.boot_auc(y, o, g, n_boot)
                r = {"task": task, "population": pop, "learner": l, "segmenter": seg, "n": len(y), "n_pos": int(y.sum()),
                     "auc": auc, "auc_lo": lo, "auc_hi": hi}
                if seg != "mu":
                    r["d_auc_vs_mu"], r["d_lo"], r["d_hi"] = boot_pair(y, oofs[f"{n}|{l}|mu"], o, g, n_boot)
                rows.append(r)
    return pd.DataFrame(rows)


def forward_ipcw(n_boot):
    rows = []
    for pop in ("all_glioma", "grade4"):
        oofs = {}
        for seg in SEGMENTERS:
            use_table(seg)
            for model in ("imaging", "clinical+phase+imaging"):
                _, o = di.run_horizon((pop, 120, model))
                oofs[f"{model}|{seg}"] = o
        cohort_p, _, _ = di.horizon_context(pop)
        for model in ("imaging", "clinical+phase+imaging"):
            sub = {k: v for k, v in oofs.items() if k.startswith(model + "|")}
            ev = di.evaluate_repeated(cohort_p, sub, 120, reference=f"{model}|mu", n_boot=n_boot)
            for k, r in ev.iterrows():
                rows.append({"population": pop, "model": model, "segmenter": k.split("|")[1],
                             **{c: r.get(c, np.nan) for c in ("auc_ipcw", "auc_ipcw_lo", "auc_ipcw_hi")},
                             "d_auc_ipcw_vs_mu": r.get(f"d_auc_ipcw_vs_{model}|mu", np.nan),
                             "d_lo": r.get("d_auc_ipcw_lo", np.nan), "d_hi": r.get("d_auc_ipcw_hi", np.nan)})
    use_table("mu")
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- 5 QA
def overlay(sid, title, path, model="brats21"):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    pid, tp = sid.split("_Timepoint_")
    p = mu_scan_paths(pid, f"Timepoint_{tp}")
    mu = np.rint(np.asarray(nib.load(str(p["mask"])).dataobj)).astype(int)
    new = np.asarray(nib.load(str(seg_path(sid, model))).dataobj).astype(int)
    t1c, flair = (np.asarray(nib.load(str(p[k])).dataobj).astype(float) for k in ("t1c", "flair"))
    area = (np.isin(mu, (1, 2, 3)) | (new > 0)).sum(axis=(0, 1))
    z = int(np.argmax(area)) if area.any() else mu.shape[2] // 2
    fig, ax = plt.subplots(1, 3, figsize=(10.5, 3.8))
    for a, img, m, nm in ((ax[0], t1c, mu, "T1c + MU mask"), (ax[1], t1c, new, f"T1c + {model}"),
                          (ax[2], flair, None, "FLAIR: WT MU (green) / new (magenta)")):
        sl = np.rot90(img[:, :, z])
        a.imshow(sl, cmap="gray", vmin=0, vmax=np.percentile(sl[sl > 0], 99.5) if (sl > 0).any() else 1)
        if m is not None:
            for lab, col in di.COLORS.items():
                mm = np.rot90(m[:, :, z] == lab)
                if mm.any():
                    a.contour(mm, levels=[0.5], colors=col, linewidths=0.9)
        else:
            for mm, col in ((np.isin(mu, (1, 2, 3)), "#06d6a0"), (new > 0, "#ff00ff")):
                if mm[:, :, z].any():
                    a.contour(np.rot90(mm[:, :, z]), levels=[0.5], colors=col, linewidths=0.9)
        a.set_title(nm, fontsize=9)
        a.axis("off")
    cnt = lambda m, k: int((m == k).sum())
    fig.suptitle(f"{title} z={z} | ET(red) MU {cnt(mu, 3)} new {cnt(new, 3)} | NETC(yellow) MU {cnt(mu, 1)} new "
                 f"{cnt(new, 1)} | SNFH(green) MU {cnt(mu, 2)} new {cnt(new, 2)} | RC(blue) MU only", fontsize=7)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


def visual_qa(p: pd.DataFrame, cohort: pd.DataFrame, out, seed=0):
    out.mkdir(exist_ok=True)
    short = p[(p.gap <= 14) & ~p.surgery_between].sort_values("abslog_et|mu", ascending=False).head(2)
    picks = [(f"shortgap_mu_et_jump_prev", r.prev_scan_id) for r in short.itertuples()]
    picks += [(f"shortgap_mu_et_jump_cur", r.scan_id) for r in short.itertuples()]
    rng = np.random.default_rng(seed)
    picks += [("random_index", x) for x in rng.choice(cohort.scan_id, 4, replace=False)]
    rows = []
    for kind, sid in picks:
        f = out / f"{kind}__{sid}.png"
        overlay(sid, f"{kind}: {sid}", f)
        rows.append({"kind": kind, "scan_id": sid, "png": f.name})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- main
def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="prism.analyses.reseg_eval", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workers", type=int, default=48)
    ap.add_argument("--n-boot", type=int, default=1000)
    ap.add_argument("--reuse-tables", action="store_true", help="reuse measurements_<seg>.csv if present")
    a = ap.parse_args(argv)
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    index, cohort = load_index(), load_cohort("all_glioma")
    tables = {"mu": pd.read_csv(MEASUREMENTS)}
    for seg in SEGMENTERS[1:]:
        tables[seg] = (pd.read_csv(table_path(seg)) if a.reuse_tables and table_path(seg).exists()
                       else build_table(seg, a.workers))
    n = {k: len(v) for k, v in tables.items()}
    assert len(set(n.values())) == 1, n
    print(f"tables {n} {time.time() - t0:.0f}s", flush=True)

    ag = agreement(tables)
    ag.to_csv(OUT / "agreement.csv", index=False)
    print(ag.round(3).to_string(index=False), flush=True)

    pairs = consecutive_pairs(tables, index)
    pairs.to_csv(OUT / "consecutive_pairs.csv", index=False)
    cons = consistency(pairs, a.n_boot)
    cons.to_csv(OUT / "consistency.csv", index=False)
    print(cons[cons.window.isin(["gap<=14d", "gap<=30d"])].round(3).to_string(index=False), flush=True)

    use_table("mu")
    s = di.scan_table(index)
    ptype = _num(index.drop_duplicates("patient_id").set_index("patient_id")["clinical_type_of_1st_progression"])
    pp = paired_pairs(s)
    pt = paired_table(pp, tables, ptype, a.n_boot)
    pt.to_csv(OUT / "paired_progression_vs_previous.csv", index=False)
    print(pt.round(3).to_string(index=False), flush=True)

    det = detection(tables, index, cohort, a.workers, a.n_boot)
    det.to_csv(OUT / "detection_auc.csv", index=False)
    print(det.round(3).to_string(index=False), flush=True)
    fw = forward_ipcw(a.n_boot)
    fw.to_csv(OUT / "forward_ipcw120.csv", index=False)
    print(fw.round(3).to_string(index=False), flush=True)

    qa = visual_qa(pairs, cohort, OUT / "qa")
    qa.to_csv(OUT / "qa" / "qa_scans.csv", index=False)
    info = {"n_scans": n, "n_consecutive_pairs": len(pairs), "n_pairs_surgery_flag": int(pairs.surgery_between.sum()),
            "n_progression_pairs": len(pp), "runtime_s": time.time() - t0, "segmentation_dir": str(SEG)}
    (OUT / "run_info.json").write_text(json.dumps(info, indent=1, default=float))
    print(info, f"-> {OUT}")


if __name__ == "__main__":
    main()
