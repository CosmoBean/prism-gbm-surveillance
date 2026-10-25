"""Report facts v3: a flat, pre-rounded {key: value} view of ONE system record (detection at the scan;
docs/results/SYSTEM_PLAN.md section 1). The LLM's only input and the checker's only reference.

Rounding: scores and medians 2 dp; volumes 1 dp (changes signed); percentages and days 0 dp; card AUCs 2 dp.
Percent changes only from a baseline of at least 1 cc. Wherever the wording can be fixed in advance it is written
here, deterministically, as a "*statement" field (the card tier in plain words, each conformal set, pathway
agreement, each flag's reason), so the LLM copies rather than composes.

Key families
  system.*       version, task, cohort
  scan.*         timing context
  meas.*         segmentation measurements (indicative, not RANO) and their change
  pathway.<p>.*  p in timeline / images / combined: what it is based on, score, cohort median, side, statement
  pathways.*     agreement of the timeline and image pathways
  card.*         reliability card (same key names as facts_card, so checker.card_check applies unchanged)
  conformal.<p>.<80|90>.*  conformal sets in fixed phrases
  flags.<f>.*    f in pathways_disagree / out_of_range / card_tier / conformal_both
No label, no outcome, no other scan's data enters the facts.
"""

from __future__ import annotations

import re

from prism.report.facts import r0, r1, r2

VERSION = "v3"
FLAGS = ("pathways_disagree", "out_of_range", "card_tier", "conformal_both")
FLAG_NAMES = {"pathways_disagree": "pathways disagree", "out_of_range": "out of training range",
              "card_tier": "thin evidence", "conformal_both": "conformal set contains both outcomes"}
PATHWAYS = ("timeline", "images", "combined")
PATHWAY_NAMES = {"timeline": "timeline pathway", "images": "image pathway", "combined": "combined score"}
COHORT_TEXT = {"mu": "the MU-Glioma-Post development cohort (scores out-of-fold: the patient was not in training)",
               "lumiere": "LUMIERE (external test; models locked on MU-Glioma-Post)",
               "ucsf": "UCSF-ALPTDG scan 2 (external test; models locked on MU-Glioma-Post)"}
COHORT_SHORT = {"mu": "MU-Glioma-Post", "lumiere": "LUMIERE", "ucsf": "UCSF-ALPTDG"}
CARD_COHORT_SHORT = {"mu": "MU-Glioma-Post", "lumiere": "LUMIERE", "ucsf_locked": "UCSF-ALPTDG",
                     "ucsf_internal": "UCSF-ALPTDG", "ucsf": "UCSF-ALPTDG"}
PHASE_TEXT = {"pre_rt": "before radiotherapy", "during_rt": "during radiotherapy",
              "before_rt_end": "before the end of radiotherapy",
              "early_post_rt": "early after radiotherapy (within 12 weeks of its end)",
              "later_post_rt": "later after radiotherapy (more than 12 weeks after its end)",
              "unknown": "phase of care unknown (radiotherapy dates not available)",
              "rt_date_unknown": "phase of care unknown (radiotherapy date not recorded)",
              "no_rt": "no radiotherapy recorded"}
BASED_ON = {
    "B1": "clinical, timing and treatment inputs (age, sex, IDH and MGMT status, days from diagnosis, radiotherapy and "
          "chemotherapy timing and dose, surgery day and scan number); it does not read the images",
    "Tbase": "clinical and timing inputs that are available in the external cohort (age, sex, IDH and MGMT status, "
             "days since surgery, and whether the scan is within about 3 months after radiotherapy); it does not "
             "read the images",
    "I_pure": "measurements from the automatic segmentation only (compartment volumes and shape at this scan, change "
              "from the previous scan and from the smallest earlier volume); it uses no clinical or timing input",
    "I_scan": "the three segmentation volumes at this scan only (there is no previous scan to compare with); it uses "
              "no clinical or timing input",
    "Tbase_ucsf": "clinical and timing inputs that are available in the external cohort (age, sex, IDH and MGMT "
                  "status, days since surgery, and whether the scan is within about 3 months after radiotherapy, "
                  "here approximated from an assumed radiotherapy course); it does not read the images",
    "T_img": "segmentation volumes harmonised across cohorts (enhancing tumour, necrosis with cavity, FLAIR "
             "hyperintensity) and their change from the previous scan; it uses no clinical or timing input",
    "B1 + I_pure": "one model fitted on the inputs of both pathways together",
    "T_ucsf": "one model locked on MU-Glioma-Post that uses the transportable clinical and timing inputs (timing "
              "approximated from an assumed radiotherapy course) together with the segmentation volumes and their "
              "change from the previous scan",
    "T": "one model locked on MU-Glioma-Post that uses the transportable clinical and timing inputs together with "
         "the segmentation volumes and their change from the previous scan",
}
SCORE_MEANING = ("each score is a model output between 0 and 1 that ranks scans by how closely they resemble the "
                 "progression scans of the training data; it is not a diagnosis and not a calibrated probability "
                 "for this patient")
CONF_PHRASE = {(0, 1): "both outcomes", (1,): "progression only", (0,): "no progression only",
               (): "empty (no outcome)"}
CONF_MEANING = {(0, 1): "the score cannot single out one outcome at this level",
                (1,): "only the progression outcome is kept at this level",
                (0,): "only the no-progression outcome is kept at this level",
                (): "no outcome is kept at this level"}
OOD_NAMES = {"rt_start_day": "radiotherapy start day", "days_since_rt_end": "days since the end of radiotherapy",
             "surgery_day": "surgery day", "age": "age", "days_from_diagnosis": "days from diagnosis",
             "visit_index": "scan number", "rt_dose_gy": "radiotherapy dose (Gy)", "rt_fractions": "radiotherapy fractions",
             "rt_duration_days": "radiotherapy duration (days)", "log_days_since_surgery": "log days since surgery"}


def _plain_feature(f: str) -> str:
    if f in OOD_NAMES:
        return OOD_NAMES[f]
    s = f.replace("logratio_", "log ratio of ").replace("log_", "log ").replace("_cc", " volume")
    for a, b in (("et", "enhancing tumour"), ("snfh", "FLAIR hyperintensity"), ("netc", "necrosis"),
                 ("rc", "resection cavity"), ("prev", "previous scan"), ("nadir", "smallest earlier volume")):
        s = re.sub(rf"(?<![a-z]){a}(?![a-z])", b, s)
    return s.replace("_", " ")


def _g(x: str) -> str:
    v = float(x)
    return f"{v:.0f}" if abs(v) >= 100 else f"{v:.3g}"


def ood_text(reason: str) -> str:
    """'rt_duration_days = 48 outside training 1-99% [20.26, 45]' -> plain words, numbers kept (3 significant)."""
    m = re.match(r"(\w+) = (\S+) outside training 1-99% \[(\S+), (\S+)\]", reason.strip())
    if not m:
        return reason.strip()
    f, v, lo, hi = m.groups()
    return (f"{_plain_feature(f)} {_g(v)} is outside the training range ({_g(lo)} to {_g(hi)}, 1st to 99th "
            "percentile)")


def _signed_cc(x):
    v = r1(x)
    return None if v is None else (0.0 if v == 0 else v)


def _change_words(cc: float, what: str, ref: str, pct) -> str:
    if abs(cc) < 0.05:
        return f"{what} unchanged compared with {ref.removeprefix('at ')} (change below 0.1 cc)"
    s = f"{what} {abs(cc):.1f} cc {'larger' if cc > 0 else 'smaller'} than {ref}"
    return s + (f" ({abs(pct)}% {'more' if cc > 0 else 'less'})" if isinstance(pct, int) else "")


def _pct(change, base):
    if change is None or base is None or base < 1.0:
        return None
    return r0(100 * change / base)


def tier_statement(tier: str, n_pos: int, n_neg: int, cohort: str, aucs: dict | None = None) -> str:
    where = f"in {cohort}"
    if tier == "tested":
        s = (f"tested: the pathways were measured on {n_pos} progression and {n_neg} non-progression scans of this "
             f"situation {where}")
        if aucs:
            s += "; AUC " + ", ".join(f"{PATHWAY_NAMES[p].replace(' pathway', '').replace(' score', '')} "
                                      f"{a:.2f} (95% CI {lo:.2f} to {hi:.2f})" for p, (a, lo, hi) in aucs.items())
        return s
    if tier == "few cases":
        cnt = " and ".join(f"only {n} {w}" if n else f"no {w}" for n, w in ((n_pos, "progression"),
                                                                             (n_neg, "non-progression")))
        return (f"few cases: {cnt} scans of this situation {where}, too few to measure how well the pathways work "
                "here")
    return (f"not tested: no scan of this situation {where}, so how well the pathways work here has not been "
            "measured")


def _set(x) -> tuple:
    if isinstance(x, str):
        x = [int(c) for c in re.findall(r"[01]", x)]
    return tuple(sorted(set(int(v) for v in x)))


def model_key(desc: str) -> str:
    """Provenance model description -> BASED_ON key."""
    d = desc.strip()
    for k, pre in (("B1 + I_pure", "B1 + I_pure"), ("B1", "B1"), ("I_pure", "I_pure"), ("I_scan", "images_scan"),
                   ("T_img", "T_img"), ("Tbase_ucsf", "A-Tbase"), ("Tbase", "Tbase"), ("I_pure", "A-Ipure"),
                   ("T_ucsf", "A-T"), ("T", "T@")):
        if d.startswith(pre):
            return k
    return d


def _phase(rec: dict) -> str:
    p = rec.get("phase_of_care") or "unknown"
    return "unknown" if p.startswith("unknown") else p


def facts_v3(rec: dict) -> dict:
    """rec: one system record (schema prism.system_record/1, docs/results/SYSTEM_RESULTS.md)."""
    coh = rec["cohort"]
    F = {"system.version": VERSION,
         "system.task": "detection at the scan: whether this scan is the one at which progression is called",
         "system.cohort": COHORT_TEXT[coh]}
    F["scan.phase"] = PHASE_TEXT.get(_phase(rec), PHASE_TEXT["unknown"])
    if rec.get("rater_flag_within_3_months_after_rt") is not None:
        F["scan.rater_within_3_months_after_rt"] = "yes" if rec["rater_flag_within_3_months_after_rt"] else "no"
    # ------------------------------------------------ measurements (segmentation)
    ms = rec.get("measurements") or {}
    cur = ms.get("volumes_cc") or {}
    prev = ms.get("previous")
    dprev, emin, dmin = (ms.get("change_from_previous_cc") or {}, ms.get("earlier_minimum_cc") or {},
                         ms.get("change_from_earlier_minimum_cc") or {})
    F["meas.available"] = "yes" if cur.get("et") is not None else "no"
    F["scan.previous_available"] = "yes" if prev else "no"
    if F["meas.available"] == "yes":
        F["meas.label"] = "volumes from the automatic segmentation; indicative, not a RANO assessment"
        for k, name in (("et", "enhancing_cc"), ("snfh", "flair_hyperintensity_cc"), ("necrosis", "necrosis_cc"),
                        ("cavity", "cavity_cc"), ("necrosis_cavity", "necrosis_and_cavity_cc")):
            if cur.get(k) is not None:
                F[f"meas.{name}"] = r1(cur[k])
        if prev:
            if prev.get("days_before") is not None:
                F["scan.days_since_previous"] = r0(prev["days_before"])
            ref = (f"at the previous scan {F['scan.days_since_previous']} days earlier"
                   if "scan.days_since_previous" in F else "at the previous scan")
            pv = prev.get("volumes_cc") or {}
            for k, name, what in (("et", "enhancing", "enhancing tumour"),
                                  ("snfh", "flair_hyperintensity", "FLAIR hyperintensity")):
                ch = dprev.get(k)
                if ch is None:
                    continue
                F[f"meas.{name}_change_since_previous_cc"] = _signed_cc(ch)
                pc = _pct(ch, pv.get(k))
                if pc is not None:
                    F[f"meas.{name}_change_since_previous_percent"] = pc
                F[f"meas.{name}_change_since_previous_statement"] = _change_words(
                    F[f"meas.{name}_change_since_previous_cc"], what, ref, pc)
        if emin.get("et") is not None and dmin.get("et") is not None and ms.get("n_earlier_scans", 0) >= 2:
            ch = dmin["et"]
            F["meas.enhancing_earlier_minimum_cc"] = r1(emin["et"])
            F["meas.enhancing_change_since_earlier_minimum_cc"] = _signed_cc(ch)
            pc = _pct(ch, emin["et"])
            if pc is not None:
                F["meas.enhancing_change_since_earlier_minimum_percent"] = pc
            F["meas.enhancing_change_since_earlier_minimum_statement"] = _change_words(
                F["meas.enhancing_change_since_earlier_minimum_cc"], "enhancing tumour",
                f"its smallest volume on the {ms['n_earlier_scans']} earlier scans "
                f"({F['meas.enhancing_earlier_minimum_cc']:.1f} cc)", pc)
    # ------------------------------------------------ pathways
    c = rec["card"]
    a = c.get("agreement") or {}
    med = a.get("medians") or {}
    side = {"timeline": a.get("timeline_side"), "images": a.get("images_side")}
    cs = COHORT_SHORT[coh]
    models = rec["provenance"]["models"]
    F["pathways.score_meaning"] = SCORE_MEANING
    for p in PATHWAYS:
        F[f"pathway.{p}.name"] = PATHWAY_NAMES[p]
        F[f"pathway.{p}.based_on"] = BASED_ON.get(model_key(models[p]), models[p])
        F[f"pathway.{p}.score"] = r2(rec["scores"][p])
        label = PATHWAY_NAMES[p] if p == "combined" else PATHWAY_NAMES[p] + " score"
        if p in med and side.get(p):
            F[f"pathway.{p}.cohort_median"] = r2(med[p])
            F[f"pathway.{p}.side"] = side[p]
            just = "just " if F[f"pathway.{p}.score"] == F[f"pathway.{p}.cohort_median"] else ""
            F[f"pathway.{p}.statement"] = (f"{label} {F[f'pathway.{p}.score']:.2f}, {just}{side[p]} the median of its "
                                           f"scores in the {cs} evaluation scans "
                                           f"({F[f'pathway.{p}.cohort_median']:.2f})")
        else:
            F[f"pathway.{p}.statement"] = f"{label} {F[f'pathway.{p}.score']:.2f}"
    ts, is_ = F["pathway.timeline.side"], F["pathway.images.side"]
    agree = ts == is_
    F["pathways.agree"] = "yes" if agree else "no"
    F["pathways.agreement_statement"] = (
        f"the two pathways agree: the timeline and image scores are both {ts} their medians" if agree else
        f"the two pathways disagree: the timeline score is {ts} its median and the image score is {is_} its median")
    # ------------------------------------------------ reliability card (key names as facts_card)
    own = c["own_cohort"]
    e = c["evidence"][own]
    tier = e["tier"]
    F["card.status"] = "a lookup of results already measured for this situation, not a learned confidence"
    F["card.situation"] = c["situation"]["text"]
    F["card.tier"] = tier
    F["card.n_progression"], F["card.n_no_progression"] = e["n_progression"], e["n_no_progression"]
    aucs = {}
    for p, cp in (("timeline", "timeline"), ("images", "images"), ("combined", "both")):
        if cp in e:
            k = "both" if p == "combined" else p
            F[f"card.{k}.auc"], F[f"card.{k}.auc_low"], F[f"card.{k}.auc_high"] = (
                r2(e[cp]["auc"]), r2(e[cp]["auc_lo"]), r2(e[cp]["auc_hi"]))
            aucs[p] = (F[f"card.{k}.auc"], F[f"card.{k}.auc_low"], F[f"card.{k}.auc_high"])
    if aucs:
        F["card.interval_level_percent"] = 95
    F["card.tier_statement"] = tier_statement(tier, e["n_progression"], e["n_no_progression"],
                                              CARD_COHORT_SHORT.get(own, own), aucs)
    F["card.tier_rule"] = ("a situation counts as tested only with at least 10 progression and 10 non-progression "
                           "scans in this exact situation")
    if a.get("progression_rate_same_direction") is not None:
        F["card.agreement_progression_percent"] = round(100 * a["progression_rate_same_direction"])
        F["card.agreement_statement"] = (f"in {CARD_COHORT_SHORT.get(own, own)}, "
                                         f"{F['card.agreement_progression_percent']}% of the evaluation scans whose "
                                         "timeline and image scores fell on the same sides of their medians as here "
                                         "were progression scans")
    # ------------------------------------------------ conformal sets
    F["conformal.method"] = ("patient-level split conformal prediction calibrated on MU-Glioma-Post; a set lists "
                             "every outcome the score cannot exclude at that level")
    for lvl, alpha in (("80", "0.2"), ("90", "0.1")):
        for p in PATHWAYS:
            s = rec["conformal"].get(f"alpha_{alpha}", {}).get(p)
            if s is None:
                continue
            s = _set(s)
            F[f"conformal.{p}.{lvl}.set"] = CONF_PHRASE[s]
            F[f"conformal.{p}.{lvl}.statement"] = (f"at the {lvl}% level, the conformal set of the {PATHWAY_NAMES[p]} "
                                                   f"contains {CONF_PHRASE[s]}: {CONF_MEANING[s]}")
    # ------------------------------------------------ flags
    fl = rec["flags"]
    fl = {"pathways_disagree": fl["pathways_disagree"], "out_of_range": fl["out_of_range"],
          "card_tier": fl["tier_flag"], "conformal_both": fl["conformal_uncertain"]}
    reasons = [ood_text(x) for x in (rec["flags"].get("out_of_range_reasons") or [])]
    reason = {"pathways_disagree": (f"the timeline score is {ts} its median and the image score is {is_} its "
                                    "median"),
              "out_of_range": "; ".join(reasons) if reasons else "at least one input is outside the training range",
              "card_tier": f"the reliability card's tier for this situation is {tier}",
              "conformal_both": "at the 80% level, the conformal set of the combined score contains both outcomes"}
    act = []
    for f in FLAGS:
        on = bool(fl.get(f))
        F[f"flags.{f}.active"] = on
        F[f"flags.{f}.name"] = FLAG_NAMES[f]
        F[f"flags.{f}.reason"] = reason[f] if on else "not raised"
        act += [FLAG_NAMES[f]] * on
    F["flags.any_active"] = bool(act)
    F["flags.statement"] = ("flags raised: " + "; ".join(act)) if act else "no flag is raised"
    return F


def active_flags(F: dict) -> list[str]:
    return [f for f in FLAGS if F.get(f"flags.{f}.active") is True]
