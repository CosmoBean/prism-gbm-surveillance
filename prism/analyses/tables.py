"""Manuscript tables that do not depend on model results: Table 1 (cohort characteristics) and the cohort flow diagram.

Table 1 columns: MU-Glioma-Post all gliomas, MU grade 4, LUMIERE. Patient-level rows use each patient's first index scan;
scan-level rows use every index scan. Labels are the primary censoring-aware labels (label_{H}; death censors).
"Gap to next MRI" is the time from an index scan to the patient's next MRI of any kind (MU: any timepoint in the index;
LUMIERE: any rated study), among index scans that have one.

    python -m prism.analyses.tables
    # -> $PRISM_OUTPUTS/results/analyses/tables/{table1.csv, table1.md, lumiere_flow.csv, cohort_flow.csv, cohort_flow.png}
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from prism.config import HORIZONS, LUMIERE_ROOT, MU_FLOW, RESULTS
from prism.data import lumiere as lu
from prism.data.mu import MAX_POST_DEATH_RECORDS, load_cohort, load_index

OUT = RESULTS / "analyses" / "tables"
COLS = ("MU all gliomas", "MU grade 4", "LUMIERE")


def _n(x, n):
    return f"{int(x)} ({100 * x / n:.0f}%)" if n else "–"


def _med(x):
    x = pd.Series(x, dtype=float).dropna()
    return f"{x.median():.0f} [{x.quantile(.25):.0f}–{x.quantile(.75):.0f}]" if len(x) else "not available"


def _rng(x):
    x = pd.Series(x, dtype=float).dropna()
    return f"{x.median():.0f} ({x.min():.0f}–{x.max():.0f})"


def next_mri_gap(cohort: pd.DataFrame, all_days: pd.DataFrame, day_col: str) -> pd.Series:
    """Days from each index scan to the same patient's next MRI (NaN if none)."""
    days = all_days.groupby("patient_id").day.apply(lambda s: np.sort(s.dropna().unique()))
    def gap(r):
        d = days.get(r.patient_id, np.array([]))
        later = d[d > r[day_col]]
        return later[0] - r[day_col] if len(later) else np.nan
    return cohort.apply(gap, axis=1)


def mu_frames():
    idx = load_index()
    c = load_cohort("all_glioma").merge(
        idx[["scan_id", "clinical_grade_of_primary_brain_tumor", "clinical_primary_diagnosis", "clinical_radiation_therapy",
             "clinical_initial_chemo_therapy", "clinical_name_of_initial_chemo_therapy",
             "clinical_number_of_days_from_diagnosis_to_radiation_therapy_end_date"]], on="scan_id", how="left")
    c["grade"] = c.clinical_grade_of_primary_brain_tumor.astype(str).str.strip()
    c["rt"] = c.clinical_radiation_therapy.astype(str).str.strip().isin(["Yes", "Proton Therapy"])
    c["chemo"] = c.clinical_initial_chemo_therapy.astype(str).str.strip().eq("Yes")
    c["tmz"] = c.clinical_name_of_initial_chemo_therapy.astype(str).str.strip().eq("Temozolomide")
    rt_end = pd.to_numeric(c.clinical_number_of_days_from_diagnosis_to_radiation_therapy_end_date, errors="coerce")
    c["rt_done_at_scan"] = c.rt & (rt_end <= c.days_from_diagnosis_to_mri)
    c["scan_day"] = c.days_from_diagnosis_to_mri
    c["gap_next"] = next_mri_gap(c, idx.rename(columns={"days_from_diagnosis_to_mri": "day"}), "scan_day")
    c["field_strength"] = np.nan
    return c


def lumiere_frames():
    c = lu.load_cohort()
    r = pd.read_csv(LUMIERE_ROOT / "LUMIERE-ExpertRating-v202211.csv")
    r = r.iloc[:, :2].set_axis(["patient_id", "date"], axis=1)
    r["day"] = r.date.map(lu._week) * 7
    c["scan_day"] = c.days_since_surgery
    c["gap_next"] = next_mri_gap(c, r, "scan_day")
    mr = pd.read_csv(LUMIERE_ROOT / "LUMIERE-MRinfo.csv")
    mr = mr[mr.Sequence.eq("CT1")].assign(scan_id=lambda d: d.Patient + "_" + d.Timepoint)
    c["field_strength"] = c.scan_id.map(mr.drop_duplicates("scan_id").set_index("scan_id")["Field strength"])
    c["grade"] = "4"
    for k in ("rt", "chemo", "tmz", "rt_done_at_scan"):
        c[k] = np.nan
    return c


def table1(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = {}
    for name, c in frames.items():
        p = c.sort_values(["patient_id", "scan_day"]).groupby("patient_id").first()
        nP, nS = len(p), len(c)
        lum = name == "LUMIERE"
        t = {("Size", "Patients"): str(nP), ("Size", "Index scans"): str(nS),
             ("Size", "Index scans per patient, median (range)"): _rng(c.groupby("patient_id").size())}
        t[("Patient", "Age, years, median [IQR]")] = _med(p.age)
        t[("Patient", "Male sex")] = _n(p.male.sum(), nP)
        for lvl in ("wildtype", "mutant", "unknown"):
            t[("Patient", f"IDH {lvl}")] = _n(p.idh.eq(lvl).sum(), nP)
        for lvl in ("methylated", "unmethylated", "unknown"):
            t[("Patient", f"MGMT {lvl}")] = _n(p.mgmt.eq(lvl).sum(), nP)
        for g in ("1", "2", "3", "3 vs 4", "4"):
            t[("Patient", f"WHO grade {g}")] = _n(p.grade.eq(g).sum(), nP) if g in set(p.grade) or g == "4" else "0"
        t[("Patient", "Radiotherapy (any, documented)")] = "not recorded" if lum else _n(p.rt.sum(), nP)
        t[("Patient", "Initial chemotherapy (documented)")] = "not recorded" if lum else _n(p.chemo.sum(), nP)
        t[("Patient", "  of which temozolomide")] = "not recorded" if lum else _n(p.tmz.sum(), nP)
        t[("Scan", "Days from origin to scan, median [IQR]")] = _med(c.scan_day)
        t[("Scan", "RT completed by scan day")] = "not recorded" if lum else _n(c.rt_done_at_scan.sum(), nS)
        t[("Scan", "Early post-RT window")] = _n((c.early_post_rt == 1).sum(), nS) + (
            "" if c.early_post_rt.notna().all() else f"; unknown {int(c.early_post_rt.isna().sum())}")
        t[("Scan", "Gap to next MRI, days, median [IQR]")] = _med(c.gap_next)
        t[("Scan", "Last documented follow-up after scan, days, median [IQR]")] = _med(c.follow_up_days)
        t[("Scan", "Time to progression or censoring, days, median [IQR]")] = _med(c.time_to_event)
        t[("Scan", "Progression documented after scan (any time)")] = _n(c.event.sum(), nS)
        t[("Scan", "Death without documented progression")] = _n(c.death_without_progression.sum(), nS)
        fs = c.field_strength
        t[("Scan", "Field strength (T1c) 1.5 T / 3 T / other or missing")] = "not distributed" if fs.isna().all() else \
            f"{_n(fs.eq(1.5).sum(), nS)} / {_n(fs.eq(3).sum(), nS)} / {int((~fs.isin([1.5, 3])).sum())}"
        for h in HORIZONS:
            y = c[f"label_{h}"]
            t[("Outcome", f"{h} d: progression / no progression / censored")] = \
                f"{int((y == 1).sum())} / {int((y == 0).sum())} / {int(y.isna().sum())}"
        rows[name] = t
    df = pd.DataFrame(rows)
    df.index = pd.MultiIndex.from_tuples(df.index, names=["level", "characteristic"])
    return df


def lumiere_flow() -> pd.DataFrame:
    """Same steps as prism.data.lumiere.build_cohort, counted."""
    r = pd.read_csv(LUMIERE_ROOT / "LUMIERE-ExpertRating-v202211.csv")
    r = r.iloc[:, [0, 1, 4]].set_axis(["patient_id", "date", "rating"], axis=1)
    r["rating"], r["day"] = r.rating.astype(str).str.strip(), r.date.map(lu._week) * 7
    first_pd = r[r.rating.str.contains("PD")].groupby("patient_id").day.min()
    death = lu.demographics().set_index("patient_id").death_day
    n_after = r.assign(d=r.patient_id.map(death)).query("day > d").groupby("patient_id").size()
    death = death.where(~death.index.isin(n_after[n_after > MAX_POST_DEATH_RECORDS].index))
    steps = [("all rated studies", np.ones(len(r), bool)),
             ("post-operative (week >= 2)", r.day >= 14),
             ("rated SD / PR / CR / Post-Op (not PD, not pre-op, not unrated)", r.rating.isin(lu.NON_PD)),
             ("before first progression (PD)", ~(r.day >= r.patient_id.map(first_pd))),
             ("not after recorded death (index scans)", ~(r.day > r.patient_id.map(death)))]
    keep, rows, prev = np.ones(len(r), bool), [], len(r)
    for name, m in steps:
        keep &= np.asarray(m)
        rows.append({"step": name, "scans": int(keep.sum()), "patients": r[keep].patient_id.nunique(),
                     "excluded": prev - int(keep.sum())})
        prev = int(keep.sum())
    out = pd.DataFrame(rows)
    c = lu.load_cohort()
    assert (out.scans.iloc[-1], out.patients.iloc[-1]) == (len(c), c.patient_id.nunique()), out
    return out


def plot_flow(mu: pd.DataFrame, lum: pd.DataFrame, g4: tuple[int, int], path):
    import textwrap
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch
    n, w = max(len(mu), len(lum)), 4.8
    fig, ax = plt.subplots(figsize=(12, 1.05 * n + 1.8))
    ax.set_xlim(0, 12.6), ax.set_ylim(-1.8, n + 0.4), ax.axis("off")
    box = dict(boxstyle="round,pad=0.02,rounding_size=0.08", lw=1.1)
    arrow = dict(arrowstyle="-|>", color="#555555", lw=1)
    def column(df, x0, title, final):
        xc = x0 + w / 2
        ax.text(xc, n + 0.1, title, ha="center", fontsize=11.5, weight="bold")
        for i, r in enumerate(df.itertuples()):
            y, last = n - 1 - i, i == len(df) - 1
            ax.add_patch(FancyBboxPatch((x0, y - 0.34), w, 0.68, fc="#e8f0fb" if last else "#f4f4f2",
                                        ec="#2a78d6" if last else "#8a8a85", **box))
            ax.text(xc, y + 0.1, textwrap.fill(r.step, 52), ha="center", va="center", fontsize=8.2, linespacing=1.1)
            ax.text(xc, y - 0.19, f"{r.scans} scans / {r.patients} patients", ha="center", va="center",
                    fontsize=8.8, weight="bold")
            if i:
                ax.annotate("", (xc, y + 0.34), (xc, y + 0.66), arrowprops=arrow)
                ax.text(xc + 0.12, y + 0.5, f"excluded {r.excluded} scans", fontsize=7.5, color="#8a3b12", va="center")
        if final:
            y = n - len(df) - 1
            ax.add_patch(FancyBboxPatch((x0 + 0.3, y - 0.3), w - 0.6, 0.6, fc="#e8f0fb", ec="#2a78d6", **box))
            ax.text(xc, y, final, ha="center", va="center", fontsize=8.6, weight="bold")
            ax.annotate("", (xc, y + 0.3), (xc, y + 0.66), arrowprops=arrow)
    column(mu, 0.3, "MU-Glioma-Post (development)", f"grade 4 subset: {g4[0]} scans / {g4[1]} patients")
    column(lum, 7.5, "LUMIERE (external test)", "")
    fig.savefig(path, dpi=200, bbox_inches="tight")


def markdown(t1: pd.DataFrame) -> str:
    lines = ["| | " + " | ".join(t1.columns) + " |", "|---|" + "---|" * len(t1.columns)]
    level = None
    for (lv, ch), r in t1.iterrows():
        if lv != level:
            lines.append(f"| **{ {'Size': 'Cohort', 'Patient': 'Patient level (first index scan)', 'Scan': 'Scan level (all index scans)', 'Outcome': 'Primary label, scans'}[lv] }** |" + " |" * len(t1.columns))
            level = lv
        lines.append(f"| {ch} | " + " | ".join(r.astype(str)) + " |")
    return "\n".join(lines) + "\n"


def main(argv=None) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    mu = mu_frames()
    frames = {COLS[0]: mu, COLS[1]: mu[mu.grade4].reset_index(drop=True), COLS[2]: lumiere_frames()}
    t1 = table1(frames)
    t1 = t1[~t1.apply(lambda r: r.astype(str).str.fullmatch(r"0( \(0%\))?").all(), axis=1)]  # drop all-zero rows
    t1.to_csv(OUT / "table1.csv")
    (OUT / "table1.md").write_text(markdown(t1))
    flow_mu, flow_lu = pd.read_csv(MU_FLOW), lumiere_flow()
    flow_lu.to_csv(OUT / "lumiere_flow.csv", index=False)
    pd.concat([flow_mu.assign(cohort="MU-Glioma-Post"), flow_lu.assign(cohort="LUMIERE")]).to_csv(
        OUT / "cohort_flow.csv", index=False)
    g4 = frames[COLS[1]]
    plot_flow(flow_mu, flow_lu, (len(g4), g4.patient_id.nunique()), OUT / "cohort_flow.png")
    print(markdown(t1))
    print(flow_lu.to_string(index=False))


if __name__ == "__main__":
    main()
