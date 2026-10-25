"""Report facts for the reliability card (EXPLORATORY): a flat {card.*: value} view of a record's
`reliability_card` block (prism.audit.reliability.build_card), rounded to display precision (AUC 2 dp).

Only additive: facts() and facts_v2() are unchanged; a report that uses the card gets {**facts_v2(rec),
**card_facts(rec)}. AUC keys exist only for cells whose tier is "tested", so a report cannot cite an AUC the card
does not show.
"""

from __future__ import annotations

from prism.audit.reliability import COHORTS, PATHWAYS
from prism.report.facts import r2

OWN_NAME = {"mu": "MU-Glioma-Post development cohort"}


def tier_statement(tier: str, n_pos: int, n_neg: int, where: str) -> str:
    if tier == "tested":
        return (f"tested: {n_pos} progression and {n_neg} non-progression scans of this situation in the {where}")
    if tier == "few cases":
        return (f"few cases: only {n_pos} progression and {n_neg} non-progression scans of this situation in the "
                f"{where}, too few to show an AUC")
    return f"not tested: no scan of this situation in the {where}; performance here has not been measured"


def card_facts(rec: dict) -> dict:
    c = rec.get("reliability_card")
    if c is None:
        return {}
    own = c["own_cohort"]
    e = c["evidence"][own]
    F = {"card.status": "exploratory lookup of results already measured (post hoc), not a learned confidence",
         "card.situation": c["situation"]["text"], "card.tier": e["tier"],
         "card.tier_statement": tier_statement(e["tier"], e["n_progression"], e["n_no_progression"],
                                               OWN_NAME.get(own, COHORTS[own])),
         "card.n_scans": e["n_scans"], "card.n_progression": e["n_progression"],
         "card.n_no_progression": e["n_no_progression"], "card.interval_level_percent": 95,
         "card.tier_rule": "an AUC is shown only with at least 10 progression and 10 non-progression scans in this "
                           "exact situation"}
    for p in PATHWAYS:
        if p in e:
            F[f"card.{p}.auc"], F[f"card.{p}.auc_low"], F[f"card.{p}.auc_high"] = (
                r2(e[p]["auc"]), r2(e[p]["auc_lo"]), r2(e[p]["auc_hi"]))
    for k, x in c["evidence"].items():
        if k == own:
            continue
        F[f"card.{k}.tier"] = x["tier"]
        F[f"card.{k}.n_progression"], F[f"card.{k}.n_no_progression"] = x["n_progression"], x["n_no_progression"]
        for p in PATHWAYS:
            if p in x:
                F[f"card.{k}.{p}_auc"] = r2(x[p]["auc"])
                F[f"card.{k}.{p}_auc_low"], F[f"card.{k}.{p}_auc_high"] = r2(x[p]["auc_lo"]), r2(x[p]["auc_hi"])
    a = c.get("agreement")
    if a is not None:
        F["card.agreement"] = a["text"]
        F["card.pathways_agree"] = "yes" if a["agree"] else "no"
        if "progression_rate_same_direction" in a:
            F["card.agreement_progression_percent"] = round(100 * a["progression_rate_same_direction"])
        m = a.get("measured")
        if m is not None:
            F["card.agreement_tier"] = m["tier"]
            for p in PATHWAYS:
                if p in m:
                    F[f"card.agreement_{p}_auc"] = r2(m[p]["auc"])
                    F[f"card.agreement_{p}_auc_low"], F[f"card.agreement_{p}_auc_high"] = (
                        r2(m[p]["auc_lo"]), r2(m[p]["auc_hi"]))
    rg = c.get("inputs_in_range")
    if rg is not None:
        F["card.inputs_in_range"] = "yes" if rg["in_range"] else "no"
        F["card.inputs_out_of_range"] = "; ".join(rg["reasons"]) if rg["reasons"] else "none"
    return F
