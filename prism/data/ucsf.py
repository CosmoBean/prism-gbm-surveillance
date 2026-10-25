"""UCSF-ALPTDG external cohort: clinical table and label candidates for detection of progression at the scan.

UCSF ships one consecutive post-treatment scan pair per patient (time1, time2) and a workbook whose day columns use
mixed sign conventions. Every event is re-expressed here as **days from scan 1 to the event (positive = after
scan 1)**. The conventions were settled by internal consistency checks (docs/results/UCSF_DATA.md):

    column (workbook)                          stored as                       event day from scan 1
    Days from 1st surgery/DX to 1st scan       scan 1 - surgery                -value
    Days from 1st scan to 2nd scan             scan 2 - scan 1                 +value
    Days from death to 1st scan                scan 1 - death                  -value
    Days from 1st scan to next progression     progression - scan 1            +value
    Days from 1st scan to 1st RT start         RT start - scan 1 ("neg = RT first")  +value
    Days from 1st chemo start to 1st scan      scan 1 - chemo start            -value
    Days from 1st scan to 2nd / 3rd SX         scan 1 - surgery                -value
    Number of surgeries                        total listed (NOT only before scan 1, despite the dictionary)

Values with |days| > MAX_ABS_DAYS (~41,000-43,600, i.e. an Excel date serial minus an empty date; one 328,372) are
date-entry artefacts: the event is kept, its day is unknown (NaN) and the patient is listed in flags.csv.
Progression dated in [-7, 0) days is progression at scan 1 (time-of-day offsets); earlier dates are a progression
before scan 1, after which the next progression is unknown.

No outcome model is fitted here; counts only.

    PYTHONPATH=. .venv/bin/python -m prism.data.ucsf   # -> outputs/data/ucsf/{scans,flags}.csv
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd

from prism.config import OUTPUTS

UCSF_ROOT = Path(os.environ.get("PRISM_UCSF_ROOT", "/project/community/sbandred/ucsf"))
UCSF_XLSX = UCSF_ROOT / "UCSF_PostopGlioma_Table S1 R1 V5.0_UNBLINDED_FINAL.xlsx"
OUT = OUTPUTS / "data" / "ucsf"
SCANS, FLAGS = OUT / "scans.csv", OUT / "flags.csv"

MAX_ABS_DAYS = 20_000          # larger |days| are date artefacts
AT_SCAN_TOL = 7                # progression dated <= 7 d before scan 1 = progression at scan 1
RT_COURSE_DAYS = 42            # standard 6-week course (only RT start is known)
EARLY_POST_RT_DAYS = 84        # MU / RANO: 12 weeks after RT end
NEG_HORIZON = 120              # primary negative: no progression for >= 120 d after the scan

CLINICAL = ["subject_id", "dx_to_s1", "s1_to_s2", "eor", "who2021", "presumed_dx", "grade", "mgmt_raw", "mgmt_index",
            "idh_raw", "codel_1p19q", "atrx", "death_raw", "prog_raw", "rt_raw", "chemo_type", "chemo_raw",
            "on_tx_1", "on_tx_2", "n_surgeries_total", "sx2_raw", "sx3_raw"]
# event -> (raw column, sign that turns it into "days from scan 1, positive = after")
EVENTS = {"surgery1": ("dx_to_s1", -1), "death": ("death_raw", -1), "progression": ("prog_raw", 1),
          "rt_start": ("rt_raw", 1), "chemo_start": ("chemo_raw", -1), "surgery2": ("sx2_raw", -1),
          "surgery3": ("sx3_raw", -1)}
# UCSF-LPTDG sheet by position: the ET overall-change column repeats the SNFH header.
VOLUME_SHEET = {0: "subject_id", 1: "timepoint", 6: "sex", 7: "age", 15: "snfh_change", 16: "snfh_inc_mm3",
                17: "snfh_dec_mm3", 18: "snfh_overall_mm3", 20: "et_change", 21: "et_inc_mm3", 22: "et_dec_mm3",
                23: "et_overall_mm3"}


def read_workbook(path: Path = UCSF_XLSX) -> dict[str, pd.DataFrame]:
    """The four data sheets with short column names (positional, so the duplicated ET header is harmless)."""
    clin = pd.read_excel(path, sheet_name="Clinical Info")
    assert clin.shape[1] == len(CLINICAL), clin.columns
    clin.columns = CLINICAL
    vol = pd.read_excel(path, sheet_name="UCSF-LPTDG", header=None, skiprows=1)
    assert vol.shape[1] == 24, vol.shape
    vol = vol[list(VOLUME_SHEET)].set_axis(list(VOLUME_SHEET.values()), axis=1)
    split = pd.read_excel(path, sheet_name="TrainTestSplit").set_axis(["subject_id", "split"], axis=1)
    pdgm = pd.read_excel(path, sheet_name="UCSF-PDGM Mapping").set_axis(["subject_id", "pdgm_id"], axis=1)
    for d in (clin, vol, split, pdgm):
        d["subject_id"] = d.subject_id.astype(int).astype(str)
    return {"clinical": clin, "volumes": vol, "split": split, "pdgm": pdgm}


def event_days(clin: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Per patient: <event>_day (from scan 1, positive = after), <event>_listed, and the artefact flags."""
    out, flags = pd.DataFrame({"subject_id": clin.subject_id}), []
    for ev, (col, sign) in EVENTS.items():
        raw = pd.to_numeric(clin[col], errors="coerce")
        bad = raw.abs() > MAX_ABS_DAYS
        out[f"{ev}_day"] = (sign * raw).where(~bad)
        out[f"{ev.split('_')[0]}_listed"] = raw.notna()
        flags.append(pd.DataFrame({"subject_id": clin.subject_id[bad], "flag": f"{ev}_date_artefact",
                                   "action": f"{ev} day set to NaN"}))
    out["scan2_day"] = pd.to_numeric(clin.s1_to_s2, errors="coerce")
    # A death 'date' that is an artefact contradicts nothing else: no death date is listed.
    out.loc[out.death_day.isna(), "death_listed"] = False
    # Chemo type given but no day: chemo given, start unknown.
    out["chemo_listed"] = out.chemo_listed | clin.chemo_type.notna()
    out["rt_listed"] = out.rt_listed | clin.on_tx_1.eq("rt") | clin.on_tx_2.eq("rt")
    s1 = out.surgery1_day
    checks = {"first_surgery_after_scan1": (s1 > 0, "diagnosis day set to NaN"),
              "rt_before_first_surgery": (out.rt_start_day < s1 - 3, "kept; diagnosis day suspect"),
              "progression_before_scan1": (out.progression_day < -AT_SCAN_TOL,
                                           "next progression unknown; both scans excluded from labels")}
    for name, (mask, action) in checks.items():
        flags.append(pd.DataFrame({"subject_id": clin.subject_id[mask], "flag": name, "action": action}))
    out.loc[s1 > 0, "surgery1_day"] = np.nan
    return out, pd.concat(flags, ignore_index=True)


def surgeries_before_scan1(clin: pd.DataFrame, ev: pd.DataFrame) -> pd.Series:
    """'Number of surgeries' counts all listed surgeries; subtract the 2nd / 3rd ones dated after scan 1. 4th+
    surgeries are undated and taken as before scan 1 only when the 3rd one was."""
    n = clin.n_surgeries_total.astype(float)
    after = (ev.surgery2_day > 0).astype(int) + (ev.surgery3_day > 0).astype(int)
    later_after = (ev.surgery3_day > 0) | ((ev.surgery2_day > 0) & ev.surgery3_day.isna())
    return (n - after - np.where(later_after, (n - 3).clip(lower=0), 0)).clip(lower=0)


def _status(s: pd.Series, mapping: dict) -> pd.Series:
    return s.astype(str).str.strip().str.lower().map(mapping).fillna("unknown")


def build_scans(wb: dict[str, pd.DataFrame] | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """One row per scan (patient x timepoint) with the timeline re-expressed relative to each scan."""
    wb = read_workbook() if wb is None else wb
    clin, vol = wb["clinical"], wb["volumes"]
    ev, flags = event_days(clin)
    pt = pd.DataFrame({
        "subject_id": clin.subject_id, "who2021": clin.who2021, "presumed_dx": clin.presumed_dx,
        "grade": pd.to_numeric(clin.grade, errors="coerce"),
        "idh": _status(clin.idh_raw, {"mut": "mutant", "wt": "wildtype"}),
        "mgmt": _status(clin.mgmt_raw, {"positive": "methylated", "unmethylated": "unmethylated"}),
        "mgmt_index": pd.to_numeric(clin.mgmt_index, errors="coerce"), "codel_1p19q": clin.codel_1p19q,
        "atrx": clin.atrx, "eor_first_surgery": clin.eor, "chemo_type": clin.chemo_type.astype(str).str.strip()
        .replace("nan", np.nan), "n_surgeries_total": clin.n_surgeries_total,
        "n_surgeries_before_scan1": surgeries_before_scan1(clin, ev)})
    pt["grade4"] = pt.grade.eq(4)
    pt["gbm_who"] = pt.who2021.eq("Glioblastoma")
    pt["gbm_or_gliosarcoma"] = pt.who2021.isin(["Glioblastoma", "Gliosarcoma"])
    pt = pt.merge(ev, on="subject_id").merge(wb["split"], on="subject_id", how="left")
    pt["in_pdgm"] = pt.subject_id.isin(wb["pdgm"].subject_id)
    pt["last_known_day"] = pt[["scan2_day", "progression_day", "death_day", "surgery2_day", "surgery3_day",
                               "rt_start_day", "chemo_start_day"]].max(axis=1)

    s = vol.merge(pt, on="subject_id", how="left", validate="many_to_one")
    s.insert(0, "scan_id", s.subject_id + "_time" + s.timepoint.astype(str))
    s["scan_day"] = np.where(s.timepoint.eq(1), 0.0, s.scan2_day)  # days from scan 1
    s["male"] = s.sex.astype(str).str.lower().eq("male").astype(int)
    rel = lambda c: s[c] - s.scan_day                                 # event day relative to this scan
    s["days_from_diagnosis_to_mri"] = -rel("surgery1_day")
    s["days_from_rt_start_to_mri"] = -rel("rt_start_day")
    s["days_from_chemo_start_to_mri"] = -rel("chemo_start_day")
    s["days_to_progression"] = rel("progression_day")
    s["days_to_death"] = rel("death_day")
    s["days_to_next_surgery"] = np.fmin(rel("surgery2_day").where(rel("surgery2_day") > 0),
                                        rel("surgery3_day").where(rel("surgery3_day") > 0))
    s["inferred_follow_up_days"] = rel("last_known_day").clip(lower=0)
    s["days_from_prev"] = np.where(s.timepoint.eq(2), s.scan2_day, np.nan)
    s["has_prev"] = s.timepoint.eq(2).astype(int)
    s["rt_started"] = np.select([~s.rt_listed, s.days_from_rt_start_to_mri >= 0, s.days_from_rt_start_to_mri < 0],
                                [0.0, 1.0, 0.0], np.nan)
    s["chemo_started"] = np.select([~s.chemo_listed, s.days_from_chemo_start_to_mri >= 0,
                                    s.days_from_chemo_start_to_mri < 0], [0.0, 1.0, 0.0], np.nan)
    tx = np.where(s.timepoint.eq(1), clin.set_index("subject_id").on_tx_1.reindex(s.subject_id),
                  clin.set_index("subject_id").on_tx_2.reindex(s.subject_id))
    s["on_tx"] = pd.Series(tx).fillna("unknown").to_numpy()
    s["on_chemo"], s["on_rt"] = (s.on_tx == "c").astype(int), (s.on_tx == "rt").astype(int)
    s["rt_phase"] = rt_phase(s.days_from_rt_start_to_mri, s.rt_listed)
    return add_label_candidates(s), flags.sort_values(["flag", "subject_id"]).reset_index(drop=True)


def rt_phase(days_from_rt_start: pd.Series, rt_listed: pd.Series) -> pd.Series:
    """Plausible phase from RT start alone, assuming a 6-week course: no RT, pre-RT, during RT (0-41 d), early
    post-RT (42-125 d = within 12 weeks of an assumed RT end), later post-RT (>= 126 d), or RT date unknown."""
    d = days_from_rt_start
    return pd.Series(np.select(
        [~rt_listed, d.isna(), d < 0, d < RT_COURSE_DAYS, d < RT_COURSE_DAYS + EARLY_POST_RT_DAYS],
        ["no_rt", "rt_date_unknown", "pre_rt", "during_rt", "early_post_rt"], "later_post_rt"), index=d.index)


def add_label_candidates(s: pd.DataFrame) -> pd.DataFrame:
    """Candidate detection labels (1 / 0 / NaN = not usable). Progression is the first progression after scan 1."""
    p, s2 = s.progression_day, s.scan2_day
    t2 = s.timepoint.eq(2)
    at_s1 = p.between(-AT_SCAN_TOL, 0, inclusive="left")
    prior = p < -AT_SCAN_TOL                                      # progression before scan 1: next one unknown
    nearer_s2 = p > s2 / 2
    pos = {"pos_s2_pm30": t2 & nearer_s2 & ((p - s2).abs() <= 30),
           "pos_s2_pm60": t2 & nearer_s2 & ((p - s2).abs() <= 60),
           "pos_s2_between": t2 & (p > 0) & (p <= s2 + 30),
           "pos_s1_at": s.timepoint.eq(1) & at_s1,
           "pos_s1_le30": s.timepoint.eq(1) & (at_s1 | ((p >= 0) & (p <= 30) & ~nearer_s2))}
    d_prog = s.days_to_progression
    post_prog = (d_prog <= 0) | prior | (t2 & at_s1)              # scan on/after the first progression
    neg_verified = ~post_prog & (d_prog >= NEG_HORIZON)
    no_prog = ~s.progression_listed & ~prior
    neg_followed = no_prog & (s.inferred_follow_up_days >= NEG_HORIZON)
    neg_unverified = no_prog & (s.inferred_follow_up_days < NEG_HORIZON)
    s["neg_class"] = np.select([neg_verified, neg_followed, neg_unverified],
                               ["verified_by_later_progression", "no_progression_followed_120",
                                "no_progression_follow_up_unknown"], "not_negative")
    for name, m in pos.items():
        s[name] = np.where(m, 1.0, np.where(s.neg_class.ne("not_negative"), 0.0, np.nan))
    # Imaging-defined (circular for an image model): ET Increased at scan 2 vs Unchanged / Decreased.
    s["et_increased"] = np.where(t2 & s.et_change.notna(), s.et_change.eq("Increased").astype(float), np.nan)
    s["label_excluded_prior_progression"] = prior
    return s


COLUMNS = ["scan_id", "subject_id", "timepoint", "scan_day", "days_from_prev", "has_prev", "split", "in_pdgm",
           "who2021", "presumed_dx", "grade", "grade4", "gbm_who", "gbm_or_gliosarcoma", "idh", "mgmt", "mgmt_index",
           "codel_1p19q", "atrx", "age", "male", "eor_first_surgery", "n_surgeries_total", "n_surgeries_before_scan1",
           "days_from_diagnosis_to_mri", "rt_listed", "days_from_rt_start_to_mri", "rt_started", "rt_phase",
           "chemo_listed", "chemo_type", "days_from_chemo_start_to_mri", "chemo_started", "on_tx", "on_chemo", "on_rt",
           "progression_listed", "days_to_progression", "death_listed", "days_to_death", "days_to_next_surgery",
           "inferred_follow_up_days", "snfh_change", "snfh_inc_mm3", "snfh_dec_mm3", "snfh_overall_mm3", "et_change",
           "et_inc_mm3", "et_dec_mm3", "et_overall_mm3", "neg_class", "pos_s2_pm30", "pos_s2_pm60", "pos_s2_between",
           "pos_s1_at", "pos_s1_le30", "et_increased", "label_excluded_prior_progression"]


def load_scans() -> pd.DataFrame:
    return pd.read_csv(SCANS, dtype={"subject_id": str})


def main(argv=None) -> None:
    s, flags = build_scans()
    OUT.mkdir(parents=True, exist_ok=True)
    s[COLUMNS].to_csv(SCANS, index=False)
    flags.to_csv(FLAGS, index=False)
    print(f"{len(s)} scans / {s.subject_id.nunique()} patients -> {SCANS}")
    print(flags.groupby("flag").subject_id.nunique().to_string())


if __name__ == "__main__":
    main()
