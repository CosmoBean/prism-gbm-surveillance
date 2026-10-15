"""Feature card (unit, source, as-of rule), per-scan as-of days, file hashes, git state, package versions."""

from __future__ import annotations

import hashlib
import platform
import subprocess
import sys
import tomllib
from pathlib import Path

import numpy as np
import pandas as pd

from prism.config import EARLY_POST_RT_DAYS, REPO

W = "MU clinical workbook column "
RT_START = "clinical_number_of_days_from_diagnosis_to_radiation_therapy_start_date"
RT_END = "clinical_number_of_days_from_diagnosis_to_radiation_therapy_end_date"
CHEMO_START = "clinical_number_of_days_from_diagnosis_to_initial_chemo_therapy_start_date"
SURGERY = "clinical_number_of_days_from_diagnosis_to_first_surgery_or_procedure"

# feature -> (unit, source, as-of event: 'demographic' (known at any scan; age at diagnosis differs from age at a
# pre-diagnosis scan by <= 29 d) | 'diagnosis' (molecular pathology, day 0) | 'scan' | index column holding the day the
# fact becomes known)
FEATURES = {
    "age": ("years", W + "clinical_age_at_diagnosis", "demographic"),
    "male": ("0/1", W + "clinical_sex_at_birth", "demographic"),
    "idh_mutant": ("0/1 (ref. wildtype)", W + "clinical_idh1_mutation, clinical_idh2_mutation", "diagnosis"),
    "idh_unknown": ("0/1", W + "clinical_idh1_mutation, clinical_idh2_mutation (neither 0 nor 1)", "diagnosis"),
    "mgmt_methylated": ("0/1 (ref. unmethylated)", W + "clinical_mgmt_methylation", "diagnosis"),
    "mgmt_unknown": ("0/1", W + "clinical_mgmt_methylation (unknown code)", "diagnosis"),
    "days_from_diagnosis": ("days", "days_from_diagnosis_to_mri (MRI timepoint day)", "scan"),
    "days_since_rt_end": ("days (NaN until RT has ended)", W + RT_END + " vs scan day", RT_END),
    "rt_date_unknown": ("0/1 (no completed RT with known end day at scan)", W + RT_END, "scan"),
    "early_post_rt": (f"0/1 (0-{EARLY_POST_RT_DAYS} d after RT end; RANO 2.0 12-week window)", W + RT_END, RT_END),
    "early_post_rt_x_mgmt_methylated": ("0/1", W + RT_END + " x clinical_mgmt_methylation", RT_END),
    "visit_index": ("count (1 = first MRI)", "rank of days_from_diagnosis_to_mri among the patient's MRIs", "scan"),
    "rt_started": ("0/1", W + "clinical_radiation_therapy + " + RT_START, RT_START),
    "rt_completed": ("0/1", W + RT_END, RT_END),
    "rt_dose_gy": ("Gy (NaN until RT started)", W + "clinical_dose", RT_START),
    "rt_fractions": ("fractions (NaN until RT started)", W + "clinical_number_of_fractions", RT_START),
    "rt_hypofractionated": ("0/1 (<= 15 fractions)", W + "clinical_number_of_fractions", RT_START),
    "rt_start_day": ("days from diagnosis", W + RT_START, RT_START),
    "rt_duration_days": ("days (NaN until RT ended)", W + RT_END + " - " + RT_START, RT_END),
    "chemo_started": ("0/1", W + "clinical_initial_chemo_therapy + " + CHEMO_START, CHEMO_START),
    "surgery_day": ("days from diagnosis", W + SURGERY, SURGERY),
    "biopsy_before_resection": ("0/1", W + "clinical_stereotactic_biopsy_before_surgical_resection", SURGERY),
    "previous_brain_tumor": ("0/1", W + "clinical_previous_brain_tumor", "demographic"),
}


def _day(v) -> float:
    s = pd.Series([v]).astype(str).str.extract(r"([-\d.]+)")[0]
    return float(pd.to_numeric(s, errors="coerce").iloc[0])


def as_of(feature: str, value, scan_day: float, index_row: pd.Series) -> dict:
    """When the input became known, and whether that is on or before the scan day."""
    unit, source, event = FEATURES[feature]
    if event == "demographic":
        day, note = min(0.0, scan_day), "demographic / history, known at any scan"
    elif event == "diagnosis":
        day, note = 0.0, "molecular pathology at diagnosis (day 0; report date not recorded)"
    elif event == "scan":
        day, note = scan_day, "computed from the scan day and earlier dates"
    else:
        d = _day(index_row.get(event))
        empty = value is None or pd.isna(value) or value == 0
        if not np.isnan(d) and d <= scan_day:
            day, note = d, f"source event documented on day {d:g} (<= scan day)"
        elif not np.isnan(d):
            # the event happens after the scan: the input may only say "not yet" (0 / missing)
            day = scan_day if empty else d
            note = f"source event on day {d:g} is after the scan; input shows 'not yet' (0 / missing, imputed)" \
                if empty else f"LEAK: uses event on day {d:g} after the scan"
        elif empty:
            day, note = scan_day, "no source date documented; input 0 / missing (imputed)"
        else:
            day, note = scan_day, "therapy documented without a date; assumed started before the scan (rule)"
    return {"feature": feature, "value": None if pd.isna(value) else float(value), "unit": unit, "source": source,
            "as_of_day": day, "scan_day": scan_day, "known_by_scan": bool(day <= scan_day), "note": note}


# ---------------------------------------------------------------- hashes, git, packages
def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git_state() -> dict:
    run = lambda *a: subprocess.run(["git", *a], cwd=REPO, capture_output=True, text=True).stdout.strip()
    return {"commit": run("rev-parse", "HEAD"), "branch": run("rev-parse", "--abbrev-ref", "HEAD"),
            "dirty_files": [l[3:] for l in run("status", "--porcelain").splitlines()]}


def package_versions(names=("numpy", "pandas", "scikit-learn", "scikit-survival", "scipy", "joblib")) -> dict:
    lock = tomllib.loads((REPO / "uv.lock").read_text())
    locked = {p["name"]: p.get("version") for p in lock.get("package", [])}
    from importlib.metadata import version
    out = {"python": sys.version.split()[0], "platform": platform.platform()}
    for n in names:
        try:
            inst = version(n)
        except Exception:
            inst = None
        out[n] = {"uv.lock": locked.get(n), "installed": inst}
    out["uv.lock_sha256"] = sha256(REPO / "uv.lock")
    return out
