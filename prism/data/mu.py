"""Stage `mu`: MU-Glioma-Post scan index, surveillance cohort with censoring-aware labels, and CV folds.

Index   one row per timepoint folder: file completeness, mask label voxel counts, MRI day, clinical workbook.
Cohort  one row per eligible surveillance scan (index date). For each horizon H the scan gets
          label_{H}       1 = progression within H days, 0 = verified no progression within H days,
                          NaN = censored before H (status unknown). Death without progression censors at death.
          naive_label_{H} the legacy definition: censored scans counted as 0
          label_{H}_composite / _altdate / _imgfu   sensitivity labels (see add_outcomes)
        and a time-to-event pair (time_to_event, event) for survival formulations.
        Rules and data conflicts: docs/results/FIX_LABELS.md.
Folds   repeated patient-grouped stratified folds; every model reads the same folds.

    python -m prism mu [--reuse-index]   # -> outputs/data/{mu_index, mu_cohort, mu_flow, folds}.csv
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
MAX_POST_DEATH_RECORDS = 1   # more dated records after the recorded death -> the death date is the error


def patient_dates(index: pd.DataFrame) -> pd.DataFrame:
    """Per-patient progression / death dates after the consistency rules (see docs/results/FIX_LABELS.md).

    progression_day      first-progression date, fallback time_to_first_progression; any date makes a progressor
    progression_day_alt  the reverse source order (sensitivity)
    death_day            recorded death day; set to NaN when > MAX_POST_DEATH_RECORDS MRIs / progression dates
                         post-date it (death_date_conflict) - an MRI or progression assessment needs a living patient
    """
    p = index.drop_duplicates("patient_id").set_index("patient_id")
    prim = _num(p["clinical_number_of_days_from_diagnosis_to_date_of_first_progression"])
    alt = _num(p["clinical_time_to_first_progression_days"])
    out = pd.DataFrame({"progression_day": prim.fillna(alt), "progression_day_alt": alt.fillna(prim)})
    out["progression_flag_conflict"] = p["clinical_progression"].ne(1) & out["progression_day"].notna()
    out["progressor"] = p["clinical_progression"].eq(1) | out["progression_day"].notna()
    died = p["clinical_overall_survival_death"].eq(1)
    death = _num(p["clinical_number_of_days_from_diagnosis_to_death_days"]).where(died)
    mri = _num(index["days_from_diagnosis_to_mri"])
    post = (mri > death.reindex(index["patient_id"]).to_numpy()).groupby(index["patient_id"]).sum()
    post = post.reindex(out.index).fillna(0) + (out["progression_day"] > death).astype(int)
    out["death_date_conflict"] = post > MAX_POST_DEATH_RECORDS
    out["death_day"] = death.where(~out["death_date_conflict"])
    out["death_date_missing"] = died & death.isna()
    return out


def eligible_scans(index: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Apply the surveillance-cohort rules in order, logging the count after each."""
    df = index.copy()
    df["tumor_voxels"] = df[["label1_voxels", "label2_voxels", "label3_voxels"]].fillna(0).sum(axis=1)
    pdates = patient_dates(index)
    for c in pdates:
        df[c] = pdates[c].reindex(df["patient_id"]).to_numpy()
    late = df[[c for c in LATE_TREATMENT_COLUMNS if c in df]].apply(_num)
    df["late_treatment_day"] = late.where(late >= 0).min(axis=1)
    mri = _num(df["days_from_diagnosis_to_mri"])
    earlier = mri.groupby(df["patient_id"]).transform(lambda s: s.cummax().shift())  # index is in timepoint order
    df["after_recorded_death"] = mri > df["death_day"]
    progressor = df["progressor"].astype(bool)

    rules = [
        ("all timepoints", pd.Series(True, index=df.index)),
        ("all four sequences and mask present", df["complete"].astype(bool)),
        ("tumour (labels 1-3) present", df["tumor_voxels"] > 0),
        ("MRI day known", mri.notna()),
        ("MRI day plausible (>= -365 d, not before an earlier timepoint)",
         (mri >= -365) & (earlier.isna() | (mri >= earlier))),
        ("progression date known for progressors", ~progressor | df["progression_day"].notna()),
        ("MRI not after recorded death", ~df["after_recorded_death"]),
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
    """Latest documented day per patient: any MRI, any dated clinical event (therapy, progression). The death day is
    excluded here and handled separately (censoring at death)."""
    day_cols = [c for c in index.columns
                if c.startswith("clinical_") and "days" in c and "cycle" not in c and "death" not in c]
    days = index[day_cols].apply(_num)
    per_row = pd.concat([days.max(axis=1), _num(index["days_from_diagnosis_to_mri"])], axis=1).max(axis=1)
    return per_row.groupby(index["patient_id"]).max()


def horizon_label(event, t, follow_up, h) -> np.ndarray:
    """1 = event within h; 0 = event after h or event-free follow-up >= h; NaN = censored before h."""
    event = np.asarray(event, bool)
    pos = event & (t <= h)
    neg = ~pos & ((event & (t > h)) | (~event & (follow_up >= h)))
    return np.where(pos, 1.0, np.where(neg, 0.0, np.nan))


def composite_label(progressor, t_prog, t_death, follow_up, h) -> np.ndarray:
    """Event = progression or death. 0 needs progression after h, or progression-free follow-up >= h (a death after h
    alone does not verify that no progression occurred before h)."""
    progressor = np.asarray(progressor, bool)
    pos = (progressor & (t_prog <= h)) | (t_death <= h)
    neg = ~pos & ((progressor & (t_prog > h)) | (~progressor & (follow_up >= h)))
    return np.where(pos, 1.0, np.where(neg, 0.0, np.nan))


def add_outcomes(scans: pd.DataFrame, last_day: pd.Series, horizons=HORIZONS,
                 last_mri: pd.Series | None = None) -> pd.DataFrame:
    """Time-to-event from each scan. Primary: progression is the event, death without progression censors at death.

    Sensitivity labels (same cohort): label_{H}_composite (event = progression or death), label_{H}_altdate (the other
    progression-date field; NaN if that date is on/before the scan), label_{H}_imgfu (follow-up from imaging only).
    """
    out = scans.copy()
    nan = pd.Series(np.nan, index=out.index)
    mri = _num(out["days_from_diagnosis_to_mri"]).to_numpy(float)
    prog_day = _num(out["progression_day"]).to_numpy(float)
    progressor = (out["clinical_progression"].eq(1) | out["progression_day"].notna()).to_numpy()
    death = _num(out.get("death_day", nan)).to_numpy(float)
    last = last_day.reindex(out["patient_id"]).to_numpy(float)
    follow_up = np.where(np.isnan(death), last, death) - mri
    last_img = last if last_mri is None else last_mri.reindex(out["patient_id"]).to_numpy(float)
    follow_up_img = np.fmin(last_img, death) - mri
    t_prog, t_death = prog_day - mri, death - mri

    out["event"] = progressor
    out["time_to_event"] = np.where(progressor, t_prog, np.maximum(follow_up, 0.5))
    out["status_known_indefinitely"] = False  # kept for downstream code; death no longer makes status known
    out["follow_up_days"] = follow_up
    out["follow_up_imaging_days"] = follow_up_img
    out["death_without_progression"] = ~progressor & ~np.isnan(death)
    out["death_before_progression"] = progressor & (death < prog_day)
    out["event_composite"] = progressor | ~np.isnan(death)
    t_comp = np.where(progressor, np.fmin(t_prog, t_death), np.where(np.isnan(death), follow_up, t_death))
    out["time_to_event_composite"] = np.where(out["event_composite"], t_comp, np.maximum(follow_up, 0.5))
    alt = _num(out.get("progression_day_alt", out["progression_day"])).to_numpy(float) - mri
    for h in horizons:
        out[f"label_{h}"] = horizon_label(progressor, t_prog, follow_up, h)
        out[f"naive_label_{h}"] = (progressor & (t_prog <= h)).astype(int)
        out[f"label_{h}_composite"] = composite_label(progressor, t_prog, t_death, follow_up, h)
        out[f"label_{h}_altdate"] = np.where(progressor & ~(alt > 0), np.nan,
                                             horizon_label(progressor, alt, follow_up, h))
        out[f"label_{h}_imgfu"] = horizon_label(progressor, t_prog, follow_up_img, h)
    return out


def consistency_report(index: pd.DataFrame, cohort: pd.DataFrame) -> list[str]:
    """Counts of the data conflicts handled by the rules (printed by `prism mu`)."""
    p = patient_dates(index)
    mri = _num(index["days_from_diagnosis_to_mri"])
    lines = [
        f"progression flag 0 but a progression date (now progressors): {int(p.progression_flag_conflict.sum())} patients",
        f"progression date fields disagree: {int((p.progression_day.ne(p.progression_day_alt) & p.progression_day.notna()).sum())} patients",
        f"death date contradicted by > {MAX_POST_DEATH_RECORDS} later records (death date ignored): "
        f"{list(p.index[p.death_date_conflict])}",
        f"died, no death day: {int(p.death_date_missing.sum())} patients",
        f"MRI day < -365 d: {list(index.loc[mri < -365, 'scan_id'])}",
        f"cohort: death without progression {int(cohort.death_without_progression.sum())} scans, "
        f"death before progression {int(cohort.death_before_progression.sum())} scans, "
        f"early_post_rt unknown (RT end unknown) {int(cohort.early_post_rt.isna().sum())} scans",
    ]
    assert not cohort["after_recorded_death"].any() and (cohort["time_to_event"] > 0).all()
    return lines


def build_cohort(index: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    scans, flow = eligible_scans(index)
    last_mri = _num(index["days_from_diagnosis_to_mri"]).groupby(index["patient_id"]).max()
    scans = add_outcomes(scans, last_known_day(index), last_mri=last_mri)
    mri = _num(scans["days_from_diagnosis_to_mri"])
    rt_end = _num(scans["clinical_number_of_days_from_diagnosis_to_radiation_therapy_end_date"])
    scans["days_since_rt_end"] = (mri - rt_end).where(rt_end.notna())
    # RT end unknown (no RT documented or no end date) -> early_post_rt unknown (NaN), not 0.
    scans["early_post_rt"] = scans["days_since_rt_end"].between(0, EARLY_POST_RT_DAYS).astype(float).where(rt_end.notna())
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
            *[f"label_{h}" for h in HORIZONS], *[f"naive_label_{h}" for h in HORIZONS],
            "progression_day_alt", "progression_flag_conflict", "death_day", "death_date_conflict",
            "death_date_missing", "after_recorded_death", "death_without_progression", "death_before_progression",
            "follow_up_days", "follow_up_imaging_days", "event_composite", "time_to_event_composite",
            *[f"label_{h}_{s}" for s in ("composite", "altdate", "imgfu") for h in HORIZONS]]
    return scans[keep].sort_values(["patient_id", "visit_index"]).reset_index(drop=True), flow


def load_cohort(population: str = "all_glioma") -> pd.DataFrame:
    """Cohort for `grade4` (WHO grade 4, ~GBM) or `all_glioma`."""
    cohort = pd.read_csv(MU_COHORT)
    return cohort[cohort.grade4].reset_index(drop=True) if population == "grade4" else cohort


def main(argv=None) -> None:
    MU_INDEX.parent.mkdir(parents=True, exist_ok=True)
    index = load_index() if argv and "--reuse-index" in argv and MU_INDEX.exists() else build_index()
    index.to_csv(MU_INDEX, index=False)
    cohort, flow = build_cohort(index)
    cohort.to_csv(MU_COHORT, index=False)
    flow.to_csv(MU_FLOW, index=False)
    make_folds(cohort).to_csv(FOLDS, index=False)
    print(f"index: {len(index)} timepoints / {index.patient_id.nunique()} patients")
    print(flow.to_string(index=False))
    print("\n".join(consistency_report(index, cohort)))
    for h in HORIZONS:
        for s in ("", "_composite", "_altdate", "_imgfu"):
            lab = cohort[f"label_{h}{s}"]
            print(f"H={h:3d}{s:11s}: positives {int((lab == 1).sum())}, verified negatives {int((lab == 0).sum())}, "
                  f"censored {int(lab.isna().sum())}")
    print(f"grade 4: {int(cohort.grade4.sum())} scans / {cohort[cohort.grade4].patient_id.nunique()} patients; "
          f"early post-RT: {int((cohort.early_post_rt == 1).sum())} (unknown {int(cohort.early_post_rt.isna().sum())})")
