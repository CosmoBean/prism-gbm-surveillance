"""Fig 5A candidates: the PRISM architecture diagram and a one-page example report (matplotlib, no LLM)."""

from __future__ import annotations

import textwrap

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

FLAG_NAMES = {"early_post_rt_window": "early post-RT window", "out_of_distribution": "out of distribution",
              "uncertain": "uncertain"}
INK, MUTED, LINE = "#1f2933", "#52606d", "#9aa5b1"
FILL = {"in": "#eef2f7", "core": "#dcebf7", "img": "#f4f4f4", "risk": "#e3f1e6", "audit": "#fdf3dc", "rep": "#f6e3e3"}


def _box(ax, x, y, w, h, title, body, kind, dashed=False, fs=8.2):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.008,rounding_size=0.012", fc=FILL[kind],
                                ec=LINE if dashed else INK, lw=0.9, ls="--" if dashed else "-"))
    ax.text(x + 0.012, y + h - 0.018, title, fontsize=fs + 0.8, weight="bold", color=INK, va="top")
    ax.text(x + 0.012, y + h - 0.07, body, fontsize=fs, color=MUTED if dashed else INK, va="top", linespacing=1.3)


def _arrow(ax, a, b, dashed=False):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=10, lw=1.0, color=LINE if dashed else INK,
                                 ls="--" if dashed else "-", shrinkA=2, shrinkB=2))


def architecture(path_stem):
    fig = plt.figure(figsize=(12, 4.3))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1), ax.set_ylim(0, 1), ax.axis("off")
    top, th = 0.50, 0.46
    _box(ax, 0.012, top, 0.175, th, "Inputs (as of scan day)",
         "Clinical: age, sex, IDH, MGMT,\nprevious tumour\nTiming: days from diagnosis,\ndays since RT end, scan no.\n"
         "Treatment: RT / chemo started,\ncompleted, dose, fractions,\nsurgery day", "in")
    _box(ax, 0.012, 0.05, 0.175, 0.36, "Post-treatment MRI",
         "T1c, FLAIR, T1, T2\n+ tumour masks\n(ET / NETC / SNFH / cavity)", "in")
    _box(ax, 0.232, top, 0.19, th, "Core model (deployed)",
         "Clinical + treatment-phase\nridge logistic regression\n(one coefficient per term)\n\n"
         "5x5 CV IPCW AUC(120 d)\n0.70 grade 4 / 0.72 all gliomas", "core")
    _box(ax, 0.232, 0.05, 0.19, 0.36, "Optional imaging branches",
         "Volumes, change vs prior / nadir\nCompartment radiomics\nDeep encoder (SwinUNETR)\n"
         "Nested CV: no measurable\nadded value; not deployed", "img", dashed=True)
    _box(ax, 0.467, top, 0.165, th, "Risk estimate",
         "P(documented progression\nwithin 120 d)\n95% patient-bootstrap\ninterval\n"
         "Tier: tertile of training\npredictions\nCalibration checked in CV", "risk")
    _box(ax, 0.677, 0.05, 0.15, 0.91, "Audit record",
         "One JSON per scan\n\nInputs with source\ncolumn and as-of day\n\nExact additive\ncontributions by group\n\n"
         "80% conformal set\n\nReferral flags:\nearly post-RT window,\nout of distribution,\nuncertain\n\n"
         "Indicative volumes\n(not RANO)", "audit")
    _box(ax, 0.852, 0.05, 0.138, 0.91, "Grounded report",
         "Deterministic sections\nrendered from the\nrecord\n\nLocal LLM summary:\nevery sentence cites\nrecord fields\n\n"
         "Deterministic checker:\nnumbers, flags, tier,\nforbidden content", "rep")
    _arrow(ax, (0.189, top + th / 2), (0.230, top + th / 2))
    _arrow(ax, (0.189, 0.23), (0.230, 0.23), dashed=True)
    _arrow(ax, (0.424, top + th / 2), (0.465, top + th / 2))
    _arrow(ax, (0.424, 0.23), (0.675, 0.23), dashed=True)
    ax.text(0.55, 0.25, "volumes, labelled indicative", fontsize=7.5, color=MUTED, ha="center")
    _arrow(ax, (0.634, top + th / 2), (0.675, top + th / 2))
    _arrow(ax, (0.829, 0.5), (0.850, 0.5))
    for ext in ("pdf", "png"):
        fig.savefig(f"{path_stem}.{ext}", dpi=220, facecolor="white")
    plt.close(fig)


def example_report(rec, F, summary, path_stem, check=None):
    """One page: header, context, risk, contributions, flags, volumes, summary, limitations."""
    from prism.report.facts import term_name
    from prism.report.sections import limitations
    fig = plt.figure(figsize=(8.27, 11.69))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1), ax.set_ylim(0, 1), ax.axis("off")
    y = [0.965]

    def line(t, fs=9, w="normal", c=INK, x=0.06, wrap=100, gap=0.0055):
        for s in textwrap.wrap(t, wrap) or [""]:
            ax.text(x, y[0], s, fontsize=fs, weight=w, color=c, va="top")
            y[0] -= fs / 72 / 11.69 * 1.45
        y[0] -= gap

    def head(t):
        y[0] -= 0.006
        ax.plot([0.06, 0.94], [y[0] + 0.004, y[0] + 0.004], color=LINE, lw=0.6)
        line(t, 10.5, "bold", gap=0.004)

    line("PRISM surveillance report", 16, "bold")
    line(f"{rec['scan_id']}  |  scan day {F['scan.day_from_diagnosis']} from diagnosis  |  {F['scan.phase_of_care']}",
         9, c=MUTED)
    head("Risk of documented progression within 120 days")
    line(f"{F['risk.value']:.2f}   (95% interval {F['risk.interval_low']:.2f}-{F['risk.interval_high']:.2f})", 15, "bold")
    line(f"Tier: {F['risk.tier']} of development-cohort predictions (cut points {F['risk.tier_cut_lower']:.2f} / "
         f"{F['risk.tier_cut_upper']:.2f}).  80% conformal set: {F['risk.conformal_set']}.")
    head("Referral flags")
    act = [k.split(".")[1] for k in F if k.endswith(".active") and F[k] is True]
    for n in act:
        line(f"[!] {FLAG_NAMES[n]}: {F[f'flags.{n}.reason']}", 9.2, "bold", c="#9b2c2c")
    if not act:
        line("none raised")
    line(f"Action: {F['flags.action']}", 9, c=MUTED)
    head("Contributions (exact additive log-odds; positive = towards higher risk)")
    ex = rec["explanation"]
    line(f"Intercept {ex['intercept']:+.2f}   clinical {F['contrib.clinical_logodds']:+.2f}   timing "
         f"{F['contrib.timing_logodds']:+.2f}   treatment {F['contrib.treatment_logodds']:+.2f}   = logit "
         f"{ex['sum_check']['logit']:+.2f}.  Imaging: not part of this model.")
    ins = {i["feature"]: i for i in rec["inputs"]}
    for t in ex["terms"][:5]:
        line(f"{t['contribution_logodds']:+.2f}   {term_name(t['column'], ins)}  ({t['group']})", 8.8, x=0.08,
             gap=0.001)
    head("Inputs as of the scan day (source: MU clinical workbook)")
    line(f"Age {F['inputs.age_years']}, {F['inputs.sex']}; IDH {F['inputs.idh']}; MGMT {F['inputs.mgmt']}; RT started "
         f"{F['inputs.rt_started']}, completed {F['inputs.rt_completed']}; days since RT end {F['scan.days_since_rt_end']}; "
         f"chemotherapy started {F['inputs.chemo_started']}. All {len(rec['inputs'])} inputs known by the scan day: "
         f"{F['inputs.all_known_by_scan_day']} (each with source column and as-of day in the record).")
    head("Volumetric change (indicative, not RANO)")
    if F["volume.available"]:
        line(f"Enhancing {F['volume.enhancing_cc']:.1f} cc; FLAIR hyperintensity {F['volume.flair_hyperintensity_cc']:.1f} cc.")
        if F["volume.prior_available"]:
            from prism.report.sections import _pc
            line(f"vs prior ({F['volume.days_since_prior']} d earlier): {F['volume.enhancing_change_since_prior_cc']:+.1f} cc "
                 f"({_pc(F['volume.enhancing_change_since_prior_percent'])}); vs nadir {F['volume.enhancing_nadir_cc']:.1f} cc: "
                 f"{F['volume.enhancing_change_since_nadir_cc']:+.1f} cc "
                 f"({_pc(F['volume.enhancing_change_since_nadir_percent'])}). Indicative flag: {F['volume.indicative_flag']}.")
        else:
            line("First scan: no prior or nadir.")
    head("Summary (local LLM; every sentence cites record fields; checked deterministically)")
    for s in summary:
        line(s, 9.4, wrap=96, gap=0.003)
    if check is not None:
        line(f"Faithfulness check: {check['n_claims'] - check['n_unsupported']}/{check['n_claims']} claims supported; "
             f"active flags mentioned: {'all' if check['all_flags_mentioned'] else 'NO'}; forbidden content: "
             f"{'none' if not check['any_forbidden'] else 'PRESENT'}.", 8.5, c=MUTED)
    head("Limitations")
    line((lambda s: s[:1].upper() + s[1:])(limitations(F).removeprefix("Limitations: ")), 8.6, c=MUTED, wrap=110)
    for ext in ("pdf", "png"):
        fig.savefig(f"{path_stem}.{ext}", dpi=200, facecolor="white")
    plt.close(fig)
