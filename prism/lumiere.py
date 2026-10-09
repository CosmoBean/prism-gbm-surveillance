"""LUMIERE external cohort (Suter et al., Sci Data 2022; CC0) harmonised to the MU-Glioma-Post endpoint.

Index scans: rated follow-up MRIs (SD / PR / CR / Post-Op at week >= 2) before the first RANO PD.
Label at horizon H: 1 = first PD within H days; 0 = a later rated scan >= H days after the index with no PD before
index + H; NaN = censored (no rating far enough ahead). Time is weeks since the first surgery (x 7 days).

    uv run python -m prism.lumiere   # -> outputs/lumiere/cohort.csv
"""

from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

from prism.config import HORIZONS, OUTPUTS

ROOT = Path("/project/community/sbandred/lumiere")
NON_PD = {"SD", "PR", "CR", "Post-Op"}


def _week(s: str) -> float:
    return float(re.match(r"week-(\d+)", s).group(1))


def build_cohort() -> pd.DataFrame:
    r = pd.read_csv(ROOT / "LUMIERE-ExpertRating-v202211.csv")
    r.columns = ["patient_id", "date", "lt3m", "nonmeas", "rating", "rationale"]
    r["rating"] = r.rating.astype(str).str.strip()
    r["day"] = r.date.map(_week) * 7
    rows = []
    for pid, g in r.sort_values(["patient_id", "day", "date"]).groupby("patient_id"):
        pd_days = g.loc[g.rating.str.contains("PD"), "day"]
        first_pd = pd_days.min() if len(pd_days) else np.nan
        for t in g.itertuples():
            if t.rating not in NON_PD or t.day < 14 or (not np.isnan(first_pd) and t.day >= first_pd):
                continue
            later = g[g.day > t.day]
            row = {"scan_id": f"{pid}_{t.date}", "patient_id": pid, "date": t.date, "days_since_surgery": t.day,
                   "early_post_rt": t.lt3m == "x", "rating": t.rating, "progression_day": first_pd}
            last_seen = later.day.max() if len(later) else t.day
            row["event"] = not np.isnan(first_pd)
            row["time_to_event"] = (first_pd - t.day) if row["event"] else max(last_seen - t.day, 0.5)
            row["status_known_indefinitely"] = False
            for h in HORIZONS:
                pos = row["event"] and first_pd - t.day <= h
                neg = (not pos) and (last_seen - t.day >= h)
                row[f"label_{h}"] = 1.0 if pos else (0.0 if neg else np.nan)
                row[f"naive_label_{h}"] = int(pos)
            rows.append(row)
    c = pd.DataFrame(rows)

    d = pd.read_csv(ROOT / "LUMIERE-Demographics_Pathology.csv")
    d.columns = ["patient_id", "survival_weeks", "sex", "age", "idh_raw", "idh_method", "mgmt_raw", "mgmt_quant"]
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


def main() -> None:
    c = build_cohort()
    out = OUTPUTS / "lumiere"
    out.mkdir(parents=True, exist_ok=True)
    zp = ROOT / "Imaging-v202211.zip"
    if zp.exists() and zipfile.is_zipfile(zp):
        v = deepbratumia_volumes(zp)
        v.to_csv(out / "deepbratumia_volumes.csv", index=False)
        c = c.merge(v, on="scan_id", how="left")
    c.to_csv(out / "cohort.csv", index=False)
    print(f"{len(c)} index scans / {c.patient_id.nunique()} patients")
    for h in HORIZONS:
        l = c[f"label_{h}"]
        print(f"H={h}: pos {int((l == 1).sum())}, verified neg {int((l == 0).sum())}, censored {int(l.isna().sum())}")


if __name__ == "__main__":
    main()
