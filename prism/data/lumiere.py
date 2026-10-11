"""LUMIERE external cohort (Suter et al., Sci Data 2022; CC0) harmonised to the MU-Glioma-Post endpoint.

Index scans: rated follow-up MRIs (SD / PR / CR / Post-Op at week >= 2) before the first RANO PD and not after the
recorded death. Label at horizon H: 1 = first PD within H days; 0 = a later rated scan >= H days after the index with no
PD before index + H; NaN = censored (no rating far enough ahead). Death without PD censors at death (same rule as MU):
follow-up = min(last rating, death). label_{H}_composite: event = PD or death. Time is weeks since the first surgery
(x 7 days); the survival time (weeks) is taken on the same origin. A death date contradicted by more than one later
rating is ignored (death_date_conflict); a single rated scan after death is dropped as an index scan.
early_post_rt is the rater's "LessThan3Months" flag (< ~90 d after RT), not MU's 0-84 d window from the RT end date.
label_{H}_altdate / _imgfu equal label_{H} (one progression source, imaging-only follow-up already).

Volumes are the DeepBraTumIA segmentations shipped with LUMIERE (read straight from the imaging archive).

    python -m prism lumiere   # -> outputs/data/lumiere_cohort.csv
"""

from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

from prism.config import HORIZONS, LUMIERE_COHORT, LUMIERE_ROOT as ROOT
from prism.data.mu import MAX_POST_DEATH_RECORDS, composite_label, horizon_label

NON_PD = {"SD", "PR", "CR", "Post-Op"}


def _week(s: str) -> float:
    return float(re.match(r"week-(\d+)", s).group(1))


def demographics() -> pd.DataFrame:
    d = pd.read_csv(ROOT / "LUMIERE-Demographics_Pathology.csv")
    d.columns = ["patient_id", "survival_weeks", "sex", "age", "idh_raw", "idh_method", "mgmt_raw", "mgmt_quant"]
    d["death_day"] = pd.to_numeric(d.survival_weeks, errors="coerce") * 7
    return d


def build_cohort() -> pd.DataFrame:
    r = pd.read_csv(ROOT / "LUMIERE-ExpertRating-v202211.csv")
    r.columns = ["patient_id", "date", "lt3m", "nonmeas", "rating", "rationale"]
    r["rating"] = r.rating.astype(str).str.strip()
    r["day"] = r.date.map(_week) * 7
    d = demographics()
    death_of = d.set_index("patient_id").death_day
    rows, n_after_death = [], 0
    for pid, g in r.sort_values(["patient_id", "day", "date"]).groupby("patient_id"):
        pd_days = g.loc[g.rating.str.contains("PD"), "day"]
        first_pd = pd_days.min() if len(pd_days) else np.nan
        death = death_of.get(pid, np.nan)
        conflict = bool((g.day > death).sum() > MAX_POST_DEATH_RECORDS)
        if conflict:
            death = np.nan
        for t in g.itertuples():
            if t.rating not in NON_PD or t.day < 14 or (not np.isnan(first_pd) and t.day >= first_pd):
                continue
            if t.day > death:
                n_after_death += 1
                continue
            later = g[g.day > t.day]
            row = {"scan_id": f"{pid}_{t.date}", "patient_id": pid, "date": t.date, "days_since_surgery": t.day,
                   "early_post_rt": float(t.lt3m == "x"), "rating": t.rating, "progression_day": first_pd,
                   "death_day": death, "death_date_conflict": conflict}
            last_seen = np.fmin(later.day.max() if len(later) else t.day, death)
            follow_up, t_pd, t_death = last_seen - t.day, first_pd - t.day, death - t.day
            ev = not np.isnan(first_pd)
            row.update({"event": ev, "time_to_event": t_pd if ev else max(follow_up, 0.5),
                        "status_known_indefinitely": False, "follow_up_days": follow_up,
                        "follow_up_imaging_days": follow_up, "death_without_progression": not ev and death == death,
                        "death_before_progression": ev and death < first_pd})
            t_comp = np.fmin(t_pd, t_death) if ev else (t_death if death == death else follow_up)
            row["event_composite"] = ev or death == death
            row["time_to_event_composite"] = t_comp if row["event_composite"] else max(follow_up, 0.5)
            for h in HORIZONS:
                lab = float(horizon_label(ev, t_pd, follow_up, h))
                row[f"label_{h}"] = lab
                row[f"naive_label_{h}"] = int(ev and t_pd <= h)
                row[f"label_{h}_composite"] = float(composite_label(ev, t_pd, t_death, follow_up, h))
                row[f"label_{h}_altdate"] = row[f"label_{h}_imgfu"] = lab
            rows.append(row)
    print(f"index scans dropped as rated after the recorded death: {n_after_death}")
    c = pd.DataFrame(rows)

    idh = d.idh_raw.astype(str).str.strip().str.lower()
    d["idh"] = np.select([idh.eq("wt"), idh.str.contains("mut")], ["wildtype", "mutant"], "unknown")
    mg = d.mgmt_raw.astype(str).str.strip().str.lower()
    d["mgmt"] = np.select([mg.eq("methylated"), mg.eq("not methylated")], ["methylated", "unmethylated"], "unknown")
    d["male"] = d.sex.astype(str).str.lower().eq("male").astype(int)
    c = c.merge(d[["patient_id", "age", "male", "idh", "mgmt"]], on="patient_id", how="left")
    c["grade4"] = True
    return c


def deepbratumia_volumes(zip_path: Path = ROOT / "Imaging-v202211.zip") -> pd.DataFrame:
    """Per-study DeepBraTumIA volumes (cc) read straight from the archive."""
    rows = []
    with zipfile.ZipFile(zip_path) as z:
        for name in z.namelist():
            if name.endswith("measured_volumes_in_mm3.json") and "DeepBraTumIA" in name:
                parts = Path(name).parts
                pid = next(p for p in parts if p.startswith("Patient-"))
                date = next(p for p in parts if p.startswith("week-"))
                vols = json.loads(z.read(name))
                rows.append({"scan_id": f"{pid}_{date}", **{f"raw_{k}": v for k, v in vols.items()}})
    return pd.DataFrame(rows)


def load_cohort() -> pd.DataFrame:
    return pd.read_csv(LUMIERE_COHORT)


def main(argv=None) -> None:
    c = build_cohort()
    zp = ROOT / "Imaging-v202211.zip"
    if zp.exists() and zipfile.is_zipfile(zp):
        c = c.merge(deepbratumia_volumes(zp), on="scan_id", how="left")
    else:
        print(f"WARNING: {zp} not found - cohort written without volumes")
    LUMIERE_COHORT.parent.mkdir(parents=True, exist_ok=True)
    c.to_csv(LUMIERE_COHORT, index=False)
    print(f"{len(c)} index scans / {c.patient_id.nunique()} patients")
    print(f"death date ignored (conflict): {sorted(c.loc[c.death_date_conflict, 'patient_id'].unique())}; "
          f"death without PD {int(c.death_without_progression.sum())} scans")
    for h in HORIZONS:
        for s in ("", "_composite"):
            l = c[f"label_{h}{s}"]
            print(f"H={h}{s}: pos {int((l == 1).sum())}, verified neg {int((l == 0).sum())}, "
                  f"censored {int(l.isna().sum())}")

