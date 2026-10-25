"""PRISM reliability card: at every scan, a LOOKUP of results already measured, by situation (no learned confidence).

EXPLORATORY (post hoc). The situations, the lookup table and the agreement rule were defined after the detection,
LUMIERE and UCSF results had been seen (docs/results/RELIABILITY_CARD.md; author's decision, OUTLINE.md decisions
log items 8-10). Nothing here is fitted: the card only reads counts and AUCs computed from existing out-of-fold or
locked-test scores.

The card states, at one scan:
  1. situation   phase of care x enhancement state (below)
  2. evidence    per cohort, how many scans of that exact situation the pathways were tested on, and, if enough,
                 their AUC with a patient-cluster bootstrap CI (timeline, images, both)
  3. agreement   whether the timeline and image pathways point the same way at this scan
  4. range       whether the scan's inputs lie inside the training 1st-99th percentile (prism.audit.model.ood_flags)

Situations (one cell = phase x enhancement; only the exact cell is looked up, cohorts are never pooled; council
decision, recorded in RELIABILITY_CARD.md):
  phase        before_rt_end  pre-RT or during RT (merged: both are tiny and both precede post-RT change)
               early_post_rt  <= 84 d (12 weeks) after RT end
               later_post_rt  > 84 d after RT end
               unknown        RT dates missing (LUMIERE always; MU patients with no RT date; UCSF no / undated RT)
  enhancement  et_absent         enhancing tumour < PD_MIN_NADIR_CC (0.1 cc) at the scan
               no_previous       ET present, no earlier scan to compare with
               et_not_increased  ET present, not increased since the previous scan
               et_increased      ET present and increased since the previous scan by the volumetric rule of
                                 prism.features.measurements.volumetric_pd (>= 1 cc and >= 40% from a measurable
                                 previous volume, or >= 1 cc of new enhancement from ~0 cc)
               unknown           no usable segmentation

TIER RULE (per cohort x cell; the counts are the same for every pathway of that cohort):
  tested      >= 10 progression AND >= 10 non-progression scans: AUC and 95% CI are shown
  few cases   at least one scan but fewer than 10 of either class: counts only, never an AUC
  not tested  no scan of this situation in that cohort
AUC: mean over CV repeats of the pooled AUC (one "repeat" for locked tests); 95% CI: 2.5-97.5 percentiles over
N_BOOT = 1000 patient-cluster bootstrap draws (seed SEED), resampling patients with all their scans.

Agreement: each pathway's score is "above" or "below" the median of that pathway's scores over the cohort's
evaluation set (median of scores, no labels). The pathways agree when both are on the same side.
"""

from __future__ import annotations

import numpy as np

from prism.features.measurements import PD_MIN_NADIR_CC, volumetric_pd

MIN_POS = MIN_NEG = 10
N_BOOT = 1000
SEED = 20261021
STATUS = "EXPLORATORY: post hoc lookup of results already measured; not a learned confidence"
TIERS = ("tested", "few cases", "not tested")
PATHWAYS = ("timeline", "images", "both")
PHASES = ("before_rt_end", "early_post_rt", "later_post_rt", "unknown")
ENHANCEMENT = ("et_absent", "no_previous", "et_not_increased", "et_increased", "unknown")
PHASE_TEXT = {"before_rt_end": "before the end of RT (pre-RT or during RT)",
              "early_post_rt": "early post-RT (within 12 weeks of RT end)",
              "later_post_rt": "later post-RT (more than 12 weeks after RT end)",
              "unknown": "phase of care unknown (RT dates missing)"}
ENH_TEXT = {"et_absent": "no enhancing tumour", "no_previous": "enhancing tumour present, no previous scan to compare",
            "et_not_increased": "enhancing tumour present, not increased since the previous scan",
            "et_increased": "enhancing tumour increased since the previous scan",
            "unknown": "enhancement state unknown (no usable segmentation)"}
COHORTS = {"mu": "MU-Glioma-Post, development (cross-validated, out-of-fold)",
           "lumiere": "LUMIERE, locked external test",
           "ucsf_locked": "UCSF-ALPTDG scan 2, locked external test",
           "ucsf_internal": "UCSF-ALPTDG scan 2, models trained on UCSF (cross-validated)"}


# ---------------------------------------------------------------- situations
def phase_cell(phase: str) -> str:
    """Map a phase label (MU phase_label, UCSF rt_phase) to a card phase."""
    return {"pre_rt": "before_rt_end", "during_rt": "before_rt_end", "early_post_rt": "early_post_rt",
            "later_post_rt": "later_post_rt"}.get(phase, "unknown")


def enhancement_state(et_cc: float, prev_et_cc: float | None) -> str:
    """ET at the scan (cc) and at the previous scan (cc; None / NaN when there is no previous scan)."""
    if et_cc is None or not np.isfinite(et_cc):
        return "unknown"
    if et_cc < PD_MIN_NADIR_CC:
        return "et_absent"
    if prev_et_cc is None or not np.isfinite(prev_et_cc):
        return "no_previous"
    f = volumetric_pd(float(et_cc), float(prev_et_cc))
    return "et_increased" if f["vol_pd_flag"] or f["et_new_from_zero_nadir"] else "et_not_increased"


def cell(phase: str, enhancement: str) -> str:
    assert phase in PHASES and enhancement in ENHANCEMENT, (phase, enhancement)
    return f"{phase}|{enhancement}"


def situation_text(c: str) -> str:
    p, e = c.split("|")
    return f"{PHASE_TEXT[p]}; {ENH_TEXT[e]}"


def tier(n_pos: int, n_neg: int) -> str:
    if n_pos + n_neg == 0:
        return "not tested"
    return "tested" if n_pos >= MIN_POS and n_neg >= MIN_NEG else "few cases"


# ---------------------------------------------------------------- AUC with a patient-cluster bootstrap
def auc(y: np.ndarray, s: np.ndarray) -> float:
    """Plain AUC (ties 1/2)."""
    pos, neg = s[y == 1], np.sort(s[y == 0])
    if not len(pos) or not len(neg):
        return np.nan
    lo = np.searchsorted(neg, pos - 1e-12, side="left")
    hi = np.searchsorted(neg, pos + 1e-12, side="right")
    return float((lo + 0.5 * (hi - lo)).sum() / (len(pos) * len(neg)))


def mean_auc(y, S, mask) -> float:
    """S: (repeats, n) scores; mask: (n,) or (repeats, n). Mean over repeats of the AUC on the masked rows."""
    S = np.atleast_2d(S)
    M = np.broadcast_to(mask, S.shape)
    v = [auc(y[m], s[m]) for s, m in zip(S, M)]
    return float(np.nanmean(v)) if np.isfinite(v).any() else np.nan


def bootstrap_auc(y, scores: dict, groups, masks: dict, n_boot=N_BOOT, seed=SEED) -> dict:
    """Paired patient-cluster bootstrap. scores {pathway: (R, n)}, masks {name: (n,) or (R, n) bool}.
    Returns {(pathway, mask name): (point, lo, hi)}; CI only from finite draws."""
    by = {g: np.where(groups == g)[0] for g in np.unique(groups)}
    pats = np.array(list(by))
    rng = np.random.default_rng(seed)
    point = {(a, m): mean_auc(y, S, M) for a, S in scores.items() for m, M in masks.items()}
    draws = {k: [] for k in point}
    for _ in range(n_boot):
        idx = np.concatenate([by[p] for p in rng.choice(pats, len(pats))])
        for (a, m) in point:
            M = masks[m]
            draws[(a, m)].append(mean_auc(y[idx], np.atleast_2d(scores[a])[:, idx],
                                          M[..., idx] if np.ndim(M) == 2 else M[idx]))
    out = {}
    for k, v in point.items():
        x = np.array(draws[k], float)
        x = x[np.isfinite(x)]
        out[k] = (v, float(np.percentile(x, 2.5)) if len(x) else np.nan,
                  float(np.percentile(x, 97.5)) if len(x) else np.nan)
    return out


# ---------------------------------------------------------------- agreement
def side(score: float, median: float) -> str:
    return "above" if score > median else "below"


def agreement(timeline_score: float, image_score: float, medians: dict) -> dict:
    t, i = side(timeline_score, medians["timeline"]), side(image_score, medians["images"])
    if t == i:
        txt = f"agree: both pathways score {t} their cohort median"
    else:
        txt = f"disagree: timeline {t} its cohort median, images {i} theirs"
    return {"timeline_side": t, "images_side": i, "agree": t == i, "text": txt}


# ---------------------------------------------------------------- the card
def lookup(table: list[dict], cohort: str, c: str) -> dict:
    """The table row for (cohort, cell); a 'not tested' row when the cohort never saw this situation."""
    for r in table:
        if r["cohort"] == cohort and r["cell"] == c:
            return r
    return {"cohort": cohort, "cell": c, "n_scans": 0, "n_pos": 0, "n_neg": 0, "n_patients": 0, "tier": "not tested",
            **{f"{p}_{k}": None for p in PATHWAYS for k in ("auc", "auc_lo", "auc_hi")}}


def evidence(row: dict) -> dict:
    """What the card may show for one cohort: counts always; AUC and CI only when the tier is 'tested'."""
    e = {"cohort": row["cohort"], "cohort_text": COHORTS[row["cohort"]], "tier": row["tier"],
         "n_scans": int(row["n_scans"]), "n_progression": int(row["n_pos"]), "n_no_progression": int(row["n_neg"])}
    if row["tier"] == "tested":
        for p in PATHWAYS:
            if row.get(f"{p}_auc") is not None and np.isfinite(row[f"{p}_auc"]):
                e[p] = {"auc": float(row[f"{p}_auc"]), "auc_lo": float(row[f"{p}_auc_lo"]),
                        "auc_hi": float(row[f"{p}_auc_hi"])}
    return e


def build_card(phase: str, enhancement: str, table: list[dict], own_cohort: str, scores: dict | None = None,
               medians: dict | None = None, ood_reasons: list[str] | None = None,
               agreement_table: list[dict] | None = None) -> dict:
    """The card for one scan. scores = {'timeline': x, 'images': y} of this scan; medians = own cohort's medians."""
    c = cell(phase, enhancement)
    ev = {k: evidence(lookup(table, k, c)) for k in COHORTS}
    card = {"status": STATUS, "situation": {"phase": phase, "enhancement": enhancement, "cell": c,
                                            "text": situation_text(c)},
            "own_cohort": own_cohort, "tier": ev[own_cohort]["tier"], "evidence": ev,
            "tier_rule": f"tested = >= {MIN_POS} progression and >= {MIN_NEG} non-progression scans in this exact "
                         "situation (AUC and 95% patient-bootstrap CI shown); few cases = fewer (counts only); "
                         "not tested = none"}
    if scores is not None and medians is not None:
        a = agreement(scores["timeline"], scores["images"], medians)
        a.update({"timeline_score": float(scores["timeline"]), "images_score": float(scores["images"]),
                  "medians": {k: float(v) for k, v in medians.items()}})
        if agreement_table is not None:
            col = {("above", "above"): "pct_progression_both_above", ("below", "below"): "pct_progression_both_below",
                   ("above", "below"): "pct_progression_timeline_above_images_below",
                   ("below", "above"): "pct_progression_images_above_timeline_below"}[(a["timeline_side"],
                                                                                       a["images_side"])]
            for r in agreement_table:
                if r["cohort"] == own_cohort and r["subset"] == ("agree" if a["agree"] else "disagree"):
                    a["measured"] = evidence({**r, "cell": r["subset"]})
                    if r.get(col) is not None:  # share of progression scans among scans with this direction
                        a["progression_rate_same_direction"] = float(r[col])
        card["agreement"] = a
    if ood_reasons is not None:
        card["inputs_in_range"] = {"in_range": not ood_reasons, "reasons": list(ood_reasons)}
    return card


def _fmt_ev(e: dict) -> str:
    s = f"{e['tier']}: {e['n_progression']} progression / {e['n_no_progression']} non-progression scans"
    if e["tier"] == "tested":
        s += "; AUC " + ", ".join(f"{p} {e[p]['auc']:.2f} ({e[p]['auc_lo']:.2f}-{e[p]['auc_hi']:.2f})"
                                  for p in PATHWAYS if p in e)
    return s


def render_text(card: dict) -> str:
    """Plain-text rendering of a card (no identifiers)."""
    own = card["evidence"][card["own_cohort"]]
    lines = ["RELIABILITY CARD (" + card["status"] + ")",
             f"Situation: {card['situation']['text']}",
             f"This situation in {COHORTS[card['own_cohort']]}: {_fmt_ev(own)}"]
    for k, e in card["evidence"].items():
        if k != card["own_cohort"]:
            lines.append(f"  elsewhere, {COHORTS[k]}: {_fmt_ev(e)}")
    if "agreement" in card:
        a = card["agreement"]
        lines.append(f"Pathways: {a['text']}" + (f" (measured where they {('agree' if a['agree'] else 'disagree')}: "
                                                   f"{_fmt_ev(a['measured'])})" if "measured" in a else ""))
        if "progression_rate_same_direction" in a:
            lines.append(f"  scans with this direction in the cohort's evaluation set: "
                         f"{100 * a['progression_rate_same_direction']:.0f}% were progression scans")
    if "inputs_in_range" in card:
        r = card["inputs_in_range"]
        lines.append("Inputs: inside the training range" if r["in_range"] else
                     "Inputs: OUTSIDE the training range: " + "; ".join(r["reasons"]))
    lines.append(f"Tier rule: {card['tier_rule']}.")
    return "\n".join(lines)
