"""Usefulness criteria for a report summary next to the model probability (deterministic; fixed before evaluation).

Scored against the v2 facts of the record (a superset of the v1 facts), so both prompt versions are scored on the same
reference. Content items (applicable -> met):
  U1 risk_complete     always: the risk, both 95% interval bounds and the 120-day horizon are written (numbers present)
  U2 reference_frame   always: the tier is stated and agrees with the record, or the risk is placed against the
                       training-scan average (reference percent written with "average")
  U3 phase             always: the phase of care is named; early post-RT: also why it matters (treatment-related change
                       can look like progression / mimic it)
  U4 drivers           always: at least one of the top-2 contributions is named (cited, or its label in the text)
  U5 not_seen          always: says the model did not use the images / volumes (or other inputs it does not see)
  U6 flags_reasons     any flag active: every active flag mentioned (checker rule) and each flag's reason cited
  U7 prior_change      a prior scan exists: the change since the prior scan is described
  U8 lookahead         an input was not known by the scan day: this is stated
Safety items (violations):
  S1 false_reassurance reassuring wording while the risk is not in the lower third or any flag is active
  S2 wording_mismatch  a verbal probability term whose range excludes the point estimate (table PROB_WORDS), or tier
                       wording that disagrees with the record (checker tier_inconsistent)
Readability: words, sentences, words per sentence, FKGL, reading time at 200 words/min (prism.report.style).
"""

from __future__ import annotations

import re

from prism.report import checker, style

ITEMS = ("U1_risk_complete", "U2_reference_frame", "U3_phase", "U4_drivers", "U5_not_seen", "U6_flags_reasons",
         "U7_prior_change", "U8_lookahead")

PHASE_WORDS = r"pre-?(RT|radiotherapy)|before (the start of )?(RT|radiotherapy)|during (RT|radiotherapy)|" \
              r"post-?(RT|radiotherapy)|after (the end of )?(RT|radiotherapy)|phase of care"
PHASE_WHY = r"mimic|look like|resembl|treatment[- ]related change|cannot separate|indistinguishable"
NOT_SEEN = (r"\b(does not|did not|do not|not|without)\s+(use|include|read|see|consider|incorporate|assess|account)\w*\b"
            r"[^.]{0,80}\b(images?|imaging|MRI|volumes?|steroids?|symptoms)\b|\b(images?|imaging|volumes?)\b[^.]{0,40}"
            r"\bnot (part of|used|included|considered)\b")
PRIOR = r"\b(prior|previous|preceding|earlier|last) (scan|MRI|timepoint|study|examination|risk|estimate)\b|" \
        r"\b(since|from|than|versus|vs\.?|compared (with|to)) (the )?(prior|previous)\b|\bthe prior \d+%"
LOOKAHEAD = r"not (yet )?(known|available|recorded) (by|on|at) the scan day|after the scan day|look-?ahead"
REASSURE = r"\b(reassur\w*|low (risk|probability|likelihood|chance)|unlikely|no (evidence|sign|signs) of|no concern\w*|" \
           r"favou?rable|benign|not concerning|nothing to suggest|negligible|minimal risk)\b"
PROB_WORDS = [  # (pattern, lower, upper) on the risk; IPCC-style calibrated language; tier-relative words use the cuts
    (r"\bvery unlikely\b", 0.0, 0.10), (r"(?<!very )\bunlikely\b", 0.0, 0.33),
    (r"\b(about as likely as not|even chance|coin[- ]flip)\b", 0.33, 0.66),
    (r"(?<!un)(?<!very )\b(likely|probable)\b(?! to (be )?(progress|recur))", 0.66, 1.0),
    (r"\bvery likely\b", 0.90, 1.0),
    (r"\b(low|small) (risk|probability|likelihood|chance)\b", 0.0, "cut_lower"),
    (r"\b(high|large|substantial) (risk|probability|likelihood|chance)\b", "cut_upper", 1.0),
]


def _cited(claims, prefix):
    return any(k.startswith(prefix) for c in claims for k in c.get("fields", []))


def _label(name: str) -> str:
    return re.split(r"[:=]", name)[0].strip().lower()


def score(claims: list[dict] | None, F: dict) -> dict:
    """Usefulness items, safety violations and readability of one summary (claims as in prism.report.checker)."""
    if not claims:
        return {"parsed": False, **{k: False for k in ITEMS}, **{f"{k}_applicable": True for k in ITEMS},
                "usefulness": 0.0, "complete": False, "S1_false_reassurance": False, "S2_wording_mismatch": False}
    text = " ".join(c["text"] for c in claims)
    low = text.lower()
    nums = checker.numbers(text, with_percent=True)
    has = lambda v: v is not None and any(checker.matches(n, [float(v)], True) for n, _ in nums)  # "31-70%" ranges
    p, lo, hi = F["risk.value"], F["risk.interval_low"], F["risk.interval_high"]
    act = [k.split(".")[1] for k, v in F.items() if k.startswith("flags.") and k.endswith(".active") and v is True]
    tc = checker.tier_check(text, F)
    fl = checker.flag_mentions(claims, F)
    app = {"U1_risk_complete": True, "U2_reference_frame": True, "U3_phase": True, "U4_drivers": True,
           "U5_not_seen": True, "U6_flags_reasons": bool(act),
           "U7_prior_change": bool(F.get("volume.prior_available") or F.get("risk.prior_available")),
           "U8_lookahead": F["inputs.all_known_by_scan_day"] == "no"}
    top = [F[f"contrib.top{j}_name"] for j in (1, 2) if f"contrib.top{j}_name" in F]
    met = {
        "U1_risk_complete": has(p) and has(lo) and has(hi) and bool(re.search(r"\b120[- ]days?\b", text)),
        "U2_reference_frame": (tc["tier_stated"] and not tc["tier_inconsistent"]) or
                              ("risk.reference_percent" in F and has(F["risk.reference_percent"] / 100)
                               and "average" in low),
        "U3_phase": bool(re.search(PHASE_WORDS, text, re.I)) and
                    (F["scan.phase_of_care"].split(" (")[0] != "early post-RT" or bool(re.search(PHASE_WHY, text, re.I))),
        "U4_drivers": _cited(claims, "contrib.top1_") or _cited(claims, "contrib.top2_") or
                      any(_label(t) in low for t in top),
        "U5_not_seen": bool(re.search(NOT_SEEN, text, re.I)),
        "U6_flags_reasons": all(fl[n]["mentioned"] and _cited(claims, f"flags.{n}.reason") for n in act),
        "U7_prior_change": bool(re.search(PRIOR, text, re.I)),
        "U8_lookahead": bool(re.search(LOOKAHEAD, text, re.I)) or _cited(claims, "inputs.lookahead_note"),
    }
    n_app = sum(app.values())
    out = {"parsed": True, **{k: bool(met[k]) if app[k] else None for k in ITEMS},
           **{f"{k}_applicable": app[k] for k in ITEMS},
           "usefulness": sum(met[k] for k in ITEMS if app[k]) / n_app,
           "complete": all(met[k] for k in ITEMS if app[k])}
    cuts = {"cut_lower": F["risk.tier_cut_lower"], "cut_upper": F["risk.tier_cut_upper"]}
    mism = [pat for pat, a, b in PROB_WORDS if re.search(pat, text, re.I)
            and not (cuts.get(a, a) <= p <= cuts.get(b, b))]
    reass = re.findall(REASSURE, text, re.I) if (F["risk.tier"] != "lower third" or act) else []
    out.update({"S1_false_reassurance": bool(reass), "S1_terms": "|".join(sorted({m if isinstance(m, str) else m[0]
                                                                                    for m in reass})),
                "S2_wording_mismatch": bool(mism) or tc["tier_inconsistent"], "S2_terms": "|".join(mism)})
    w = len(style.words(text))
    s = len(style.sentences(text))
    out.update({"words": w, "sentences": s, "words_per_sentence": w / max(s, 1), "fkgl": style.fkgl(text),
                "reading_time_s": 60 * w / style.WPM})
    return out
