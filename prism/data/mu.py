"""Stage `mu`: MU-Glioma-Post scan index, surveillance cohort with censoring-aware labels, and CV folds.

Index   one row per timepoint folder: file completeness, mask label voxel counts, MRI day, clinical workbook.
Cohort  one row per eligible surveillance scan (index date). For each horizon H the scan gets
          label_{H}       1 = progression within H days, 0 = verified no progression within H days,
                          NaN = censored before H (status unknown)
          naive_label_{H} the legacy definition: censored scans counted as 0
        and a time-to-event pair (time_to_event, event) for survival formulations.
Folds   repeated patient-grouped stratified folds; every model reads the same folds.

    python -m prism mu   # -> outputs/data/{mu_index, mu_cohort, mu_flow, folds}.csv
"""

from __future__ import annotations

import re
from concurrent.futures import ProcessPoolExecutor

import nibabel as nib
import numpy as np
import pandas as pd

from prism.config import (EARLY_POST_RT_DAYS, FOLDS, HORIZONS, MU_CLINICAL, MU_COHORT, MU_FLOW, MU_IMAGES, MU_INDEX,
                          WORKERS, mu_scan_paths)
from prism.models.folds import make_folds

LATE_TREATMENT_COLUMNS = (
    "clinical_number_of_days_from_diagnosis_to_starting_2nd_additional_therapy",
    "clinical_number_of_days_from_diagnosis_to_start_immunotherapy",
    "clinical_days_from_diagnosis_to_new_treatment",
)


def _num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce")


def _snake(value: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "_", value.strip().lower())
    return re.sub(r"_+", "_", value).strip("_")


# ---------------------------------------------------------------- index
def _scan_files(args: tuple[str, str]) -> dict:
    pid, tp = args
    paths = mu_scan_paths(pid, tp)
    row = {"patient_id": pid, "timepoint": tp, "has_mask": paths["mask"].exists(),
           "complete": all(p.exists() for p in paths.values())}
    if row["has_mask"]:
        values, counts = np.unique(np.asarray(nib.load(str(paths["mask"])).dataobj), return_counts=True)
        n = dict(zip(values.astype(int).tolist(), counts.tolist()))
        row.update({f"label{k}_voxels": n.get(k, 0) for k in (1, 2, 3, 4)})
    return row


def load_clinical() -> tuple[pd.DataFrame, dict[int, str]]:
    """Clinical workbook with snake_case `clinical_*` columns, plus the MRI-day column for each timepoint number."""
    clin = pd.read_excel(MU_CLINICAL, sheet_name="MU Glioma Post")
    names = {c: "patient_id" if str(c) == "Patient_ID" else f"clinical_{_snake(str(c))}" for c in clin.columns}
    tp_cols = {int(m.group(1)): names[c] for c in clin.columns if (m := re.search(r"Timepoint_(\d+)", str(c)))}
    return clin.rename(columns=names), tp_cols


def build_index(workers: int = WORKERS) -> pd.DataFrame:
    jobs = sorted((p.parent.name, p.name) for p in MU_IMAGES.glob("PatientID_*/Timepoint_*") if p.is_dir())
    with ProcessPoolExecutor(min(workers, 32)) as ex:
        files = pd.DataFrame(list(ex.map(_scan_files, jobs, chunksize=8)))
    clin, tp_cols = load_clinical()
    index = files.merge(clin, on="patient_id", how="left")
    index["timepoint_number"] = index["timepoint"].str.extract(r"Timepoint_(\d+)")[0].astype(int)
    index["days_from_diagnosis_to_mri"] = [
        index.at[i, tp_cols[n]] if n in tp_cols else np.nan for i, n in enumerate(index["timepoint_number"])]
    index["scan_id"] = index["patient_id"] + "_" + index["timepoint"]
    return index.sort_values(["patient_id", "timepoint_number"]).reset_index(drop=True)


def load_index() -> pd.DataFrame:
    return pd.read_csv(MU_INDEX, low_memory=False)


# ---------------------------------------------------------------- codebook
def idh_status(idh1: pd.Series, idh2: pd.Series) -> pd.Series:
    """Data dictionary: IDH1/IDH2 0 = no mutation, 1 = mutation. Other codes are undocumented -> unknown."""
    idh1, idh2 = _num(idh1), _num(idh2)
    out = pd.Series("unknown", index=idh1.index)
    out[(idh1 == 0) & (idh2 == 0)] = "wildtype"
    out[(idh1 == 1) | (idh2 == 1)] = "mutant"
    return out


def mgmt_status(mgmt: pd.Series) -> pd.Series:
    """0 = unmethylated, 1 = methylated; 2 indeterminate, 3 unable to assess, others undocumented -> unknown."""
    m = _num(mgmt)
    return pd.Series(np.select([m == 1, m == 0], ["methylated", "unmethylated"], "unknown"), index=m.index)


def atrx_status(atrx: pd.Series) -> pd.Series:
    a = _num(atrx)
    return pd.Series(np.select([a == 0, a == 1, a == 2], ["wildtype", "mutant", "mosaic"], "unknown"), index=a.index)


def codeletion_1p19q(x: pd.Series) -> pd.Series:
    """Dictionary documents only 0 (no co-deletion) and 6 (1p deletion); the rest are undocumented."""
    v = _num(x)
    return pd.Series(np.select([v == 0, v == 6], ["no_codeletion", "1p_deletion"], "unknown"), index=v.index)


# ---------------------------------------------------------------- cohort
def eligible_scans(index: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Apply the surveillance-cohort rules in order, logging the count after each."""
    df = index.copy()
    df["tumor_voxels"] = df[["label1_voxels", "label2_voxels", "label3_voxels"]].fillna(0).sum(axis=1)
    df["progression_day"] = _num(df["clinical_number_of_days_from_diagnosis_to_date_of_first_progression"]).fillna(
        _num(df["clinical_time_to_first_progression_days"]))
    late = df[[c for c in LATE_TREATMENT_COLUMNS if c in df]].apply(_num)
    df["late_treatment_day"] = late.where(late >= 0).min(axis=1)
    mri = _num(df["days_from_diagnosis_to_mri"])
    progressor = df["clinical_progression"].eq(1)

    rules = [
        ("all timepoints", pd.Series(True, index=df.index)),
        ("all four sequences and mask present", df["complete"].astype(bool)),
        ("tumour (labels 1-3) present", df["tumor_voxels"] > 0),
        ("MRI day known", mri.notna()),
        ("progression date known for progressors", ~progressor | df["progression_day"].notna()),
        ("before late treatment (2nd-line, immunotherapy, new treatment)",
         df["late_treatment_day"].isna() | (mri < df["late_treatment_day"])),
        ("before first progression (index scans only)", ~progressor | (mri < df["progression_day"])),
    ]
    keep = pd.Series(True, index=df.index)
    flow = []
    for name, rule in rules:
        before = int(keep.sum())
        keep &= rule.fillna(False)
        flow.append({"step": name, "scans": int(keep.sum()), "patients": int(df.loc[keep, "patient_id"].nunique()),
                     "excluded": before - int(keep.sum())})
    return df[keep].copy(), pd.DataFrame(flow)


def last_known_day(index: pd.DataFrame) -> pd.Series:
    """Latest documented day per patient: any MRI, any dated clinical event (therapy, progression, death)."""
    day_cols = [c for c in index.columns if c.startswith("clinical_") and "days" in c and "cycle" not in c]
    days = index[day_cols].apply(_num)
    per_row = pd.concat([days.max(axis=1), _num(index["days_from_diagnosis_to_mri"])], axis=1).max(axis=1)
    return per_row.groupby(index["patient_id"]).max()


def add_outcomes(scans: pd.DataFrame, last_day: pd.Series, horizons=HORIZONS) -> pd.DataFrame:
    """Time-to-event from each scan; death without progression is a verified non-event (competing risk)."""
    out = scans.copy()
    mri = _num(out["days_from_diagnosis_to_mri"])
    progressor = out["clinical_progression"].eq(1)
    died = out["clinical_overall_survival_death"].eq(1)
    follow_up = last_day.reindex(out["patient_id"]).to_numpy() - mri.to_numpy()
    t_prog = (out["progression_day"] - mri).to_numpy()

    out["event"] = progressor.to_numpy()
    out["time_to_event"] = np.where(progressor, t_prog, np.maximum(follow_up, 0.5))
    # A patient who died without documented progression cannot progress later: status known for any horizon.
    out["status_known_indefinitely"] = (~progressor & died).to_numpy()
    for h in horizons:
        pos = progressor.to_numpy() & (t_prog <= h)
        known_neg = ~pos & ((progressor.to_numpy() & (t_prog > h)) | (out["status_known_indefinitely"].to_numpy())
                            | (~progressor.to_numpy() & (follow_up >= h)))
        out[f"label_{h}"] = np.where(pos, 1.0, np.where(known_neg, 0.0, np.nan))
        out[f"naive_label_{h}"] = pos.astype(int)
    return out


def build_cohort(index: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    scans, flow = eligible_scans(index)
    scans = add_outcomes(scans, last_known_day(index))
    mri = _num(scans["days_from_diagnosis_to_mri"])
    rt_end = _num(scans["clinical_number_of_days_from_diagnosis_to_radiation_therapy_end_date"])
    scans["days_since_rt_end"] = (mri - rt_end).where(rt_end.notna())
    scans["early_post_rt"] = scans["days_since_rt_end"].between(0, EARLY_POST_RT_DAYS)
    scans["visit_index"] = scans.groupby("patient_id")["days_from_diagnosis_to_mri"].rank(method="first").astype(int)
    grade = scans["clinical_grade_of_primary_brain_tumor"].astype(str).str.strip()
    scans["grade4"] = grade.eq("4")
    scans["gbm"] = scans["clinical_primary_diagnosis"].astype(str).str.contains("GBM")
    scans["idh"] = idh_status(scans["clinical_idh1_mutation"], scans["clinical_idh2_mutation"])
    scans["mgmt"] = mgmt_status(scans["clinical_mgmt_methylation"])
    scans["atrx"] = atrx_status(scans["clinical_atrx_mutation"])
    scans["codel_1p19q"] = codeletion_1p19q(scans["clinical_1p_19q"])
    scans["age"] = _num(scans["clinical_age_at_diagnosis"])
    scans["male"] = scans["clinical_sex_at_birth"].eq("Male").astype(int)
    keep = ["scan_id", "patient_id", "timepoint", "visit_index", "days_from_diagnosis_to_mri", "days_since_rt_end",
            "early_post_rt", "grade4", "gbm", "age", "male", "idh", "mgmt", "atrx", "codel_1p19q",
            "label1_voxels", "label2_voxels", "label3_voxels", "label4_voxels",
            "clinical_progression", "progression_day", "event", "time_to_event", "status_known_indefinitely",
            *[f"label_{h}" for h in HORIZONS], *[f"naive_label_{h}" for h in HORIZONS]]
    return scans[keep].sort_values(["patient_id", "visit_index"]).reset_index(drop=True), flow


def load_cohort(population: str = "all_glioma") -> pd.DataFrame:
    """Cohort for `grade4` (WHO grade 4, ~GBM) or `all_glioma`."""
    cohort = pd.read_csv(MU_COHORT)
    return cohort[cohort.grade4].reset_index(drop=True) if population == "grade4" else cohort


def main(argv=None) -> None:
    MU_INDEX.parent.mkdir(parents=True, exist_ok=True)
    index = build_index()
    index.to_csv(MU_INDEX, index=False)
    cohort, flow = build_cohort(index)
    cohort.to_csv(MU_COHORT, index=False)
    flow.to_csv(MU_FLOW, index=False)
    make_folds(cohort).to_csv(FOLDS, index=False)
    print(f"index: {len(index)} timepoints / {index.patient_id.nunique()} patients")
    print(flow.to_string(index=False))
    for h in HORIZONS:
        lab = cohort[f"label_{h}"]
        print(f"H={h:3d}: positives {int((lab == 1).sum())}, verified negatives {int((lab == 0).sum())}, "
              f"censored {int(lab.isna().sum())}")
    print(f"grade 4: {int(cohort.grade4.sum())} scans / {cohort[cohort.grade4].patient_id.nunique()} patients; "
          f"early post-RT: {int(cohort.early_post_rt.sum())}")
