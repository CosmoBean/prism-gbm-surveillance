"""Report v3: facts_v3, checker v3 (check_v3 via check(..., card=True)), perturbation rule. Synthetic records only."""

import copy
import unittest

from prism.report import checker
from prism.report.facts_v3 import facts_v3, ood_text


def card(tier="few cases", n_pos=3, n_neg=8, sides=("below", "above")):
    ev = {"cohort": "mu", "tier": tier, "n_scans": n_pos + n_neg, "n_progression": n_pos, "n_no_progression": n_neg}
    if tier == "tested":
        ev.update({p: {"auc": a, "auc_lo": a - 0.12, "auc_hi": a + 0.1}
                   for p, a in (("timeline", 0.58), ("images", 0.77), ("both", 0.61))})
    return {"situation": {"text": "early post-RT (within 12 weeks of RT end); enhancing tumour increased since the "
                                  "previous scan"}, "own_cohort": "mu", "tier": tier, "evidence": {"mu": ev},
            "agreement": {"timeline_side": sides[0], "images_side": sides[1], "agree": sides[0] == sides[1],
                          "medians": {"timeline": 0.343, "images": 0.3227},
                          "progression_rate_same_direction": 0.139}}


def record(tier="few cases", sides=("below", "above"), conf80="{0, 1}", ood=("MGMT status unknown",)):
    return {"cohort": "mu", "record_id": "mu|grade4|S", "scan_id": "S", "phase_of_care": "early_post_rt",
            "scores": {"timeline": 0.0548 if sides[0] == "below" else 0.5, "images": 0.3819 if sides[1] == "above"
                       else 0.2, "combined": 0.2267},
            "measurements": {"volumes_cc": {"et": 37.248, "snfh": 45.757, "necrosis": 2.81, "cavity": 0.0},
                             "n_earlier_scans": 1,
                             "previous": {"days_before": 56.0, "volumes_cc": {"et": 33.779, "snfh": 44.251}},
                             "change_from_previous_cc": {"et": 3.469, "snfh": 1.506},
                             "earlier_minimum_cc": {"et": 33.779}, "change_from_earlier_minimum_cc": {"et": 3.469}},
            "card": card(tier, sides=sides),
            "conformal": {"alpha_0.2": {"timeline": "{0}", "images": "{0, 1}", "combined": conf80},
                          "alpha_0.1": {"timeline": "{0, 1}", "images": "{0, 1}", "combined": "{0, 1}"}},
            "flags": {"pathways_disagree": sides[0] != sides[1], "out_of_range": bool(ood),
                      "out_of_range_reasons": list(ood), "tier_flag": tier != "tested",
                      "conformal_uncertain": conf80 == "{0, 1}"},
            "provenance": {"models": {"timeline": "B1 (C2)", "images": "I_pure (volumes)", "combined": "B1 + I_pure"}}}


def good_claims(F):
    C = [{"text": "The scan was taken early after radiotherapy, 56 days after the previous scan.",
          "fields": ["scan.phase", "scan.days_since_previous"]},
         {"text": "Indicative volumes, not a RANO assessment, are 37.2 cc of enhancing tumour and 45.8 cc of FLAIR "
                  "hyperintensity.", "fields": ["meas.label", "meas.enhancing_cc", "meas.flair_hyperintensity_cc"]},
         {"text": "The " + F["meas.enhancing_change_since_previous_statement"] + ".",
          "fields": ["meas.enhancing_change_since_previous_statement"]},
         {"text": "The timeline pathway uses clinical and treatment inputs; " + F["pathway.timeline.statement"] + ".",
          "fields": ["pathway.timeline.based_on", "pathway.timeline.statement"]},
         {"text": "The image pathway uses segmentation measurements; " + F["pathway.images.statement"] + ".",
          "fields": ["pathway.images.based_on", "pathway.images.statement"]},
         {"text": "In short, " + F["pathways.agreement_statement"] + ".",
          "fields": ["pathways.agreement_statement", "flags.pathways_disagree.active"]},
         {"text": "The " + F["pathway.combined.statement"] + ".", "fields": ["pathway.combined.statement"]},
         {"text": F["conformal.combined.80.statement"].capitalize() + ".",
          "fields": ["conformal.combined.80.statement", "flags.conformal_both.reason"]},
         {"text": "The reliability card's tier here is " + F["card.tier_statement"] + ".",
          "fields": ["card.tier_statement", "card.tier", "flags.card_tier.reason"]}]
    if F["flags.out_of_range.active"]:
        C.append({"text": "Out of training range flag: " + F["flags.out_of_range.reason"] + ".",
                  "fields": ["flags.out_of_range.reason"]})
    return C


class TestFactsV3(unittest.TestCase):
    def test_rounding_and_statements(self):
        F = facts_v3(record())
        self.assertEqual(F["meas.enhancing_cc"], 37.2)
        self.assertEqual(F["meas.enhancing_change_since_previous_percent"], 10)
        self.assertEqual(F["pathway.timeline.score"], 0.05)
        self.assertIn("disagree", F["pathways.agreement_statement"])
        self.assertTrue(F["card.tier_statement"].startswith("few cases: only 3 progression"))
        self.assertEqual(F["conformal.combined.80.set"], "both outcomes")
        self.assertEqual(F["conformal.timeline.80.set"], "no progression only")
        self.assertNotIn("card.timeline.auc", F)

    def test_tested_has_aucs(self):
        F = facts_v3(record(tier="tested"))
        self.assertEqual(F["card.images.auc"], 0.77)
        self.assertIn("AUC", F["card.tier_statement"])
        self.assertFalse(F["flags.card_tier.active"])

    def test_ood_text(self):
        self.assertEqual(ood_text("rt_duration_days = 48 outside training 1-99% [20.26, 45]"),
                         "radiotherapy duration (days) 48 is outside the training range (20.3 to 45, 1st to 99th "
                         "percentile)")


class TestCheckerV3(unittest.TestCase):
    def setUp(self):
        self.F = facts_v3(record())
        self.C = good_claims(self.F)

    def test_good_report_passes(self):
        r = checker.check(self.C, self.F, card=True)
        self.assertTrue(r["pass"], r)
        self.assertTrue(r["card_tier_stated"])

    def test_wrong_number_fails(self):
        C = copy.deepcopy(self.C)
        C[1]["text"] = C[1]["text"].replace("37.2", "38.2")
        self.assertFalse(checker.check(C, self.F, card=True)["pass"])

    def test_number_word_fails(self):
        C = copy.deepcopy(self.C)
        C[0]["text"] += " It is the third of four scans."
        self.assertFalse(checker.check(C, self.F, card=True)["pass"])

    def test_tier_omitted_fails(self):
        C = [c for c in self.C if "card.tier_statement" not in c["fields"]]
        r = checker.check(C, self.F, card=True)
        self.assertFalse(r["card_tier_stated"])
        self.assertFalse(r["pass"])

    def test_advice_fails(self):
        for s in ("A repeat MRI should be considered.", "We recommend clinician review.", "This needs to be decided.",
                  "Progression is likely.", "The scan shows progression."):
            C = self.C + [{"text": s, "fields": []}]
            self.assertFalse(checker.check(C, self.F, card=True)["pass"], s)

    def test_conformal_wrong_phrase_fails(self):
        C = copy.deepcopy(self.C)
        C[7]["text"] = "At the 80% level, the conformal set of the combined score contains progression only."
        r = checker.check(C, self.F, card=True)
        self.assertFalse(r["conformal"]["conformal_pass"])
        self.assertFalse(r["pass"])

    def test_conformal_uncited_fails(self):
        C = copy.deepcopy(self.C)
        C[7]["fields"] = []
        self.assertFalse(checker.check(C, self.F, card=True)["pass"])

    def test_agreement_wrong_fails(self):
        C = copy.deepcopy(self.C)
        C[5]["text"] = "The two pathways agree."
        r = checker.check(C, self.F, card=True)
        self.assertFalse(r["agreement"]["agreement_pass"])
        self.assertFalse(r["pass"])

    def test_side_wrong_fails(self):
        C = copy.deepcopy(self.C)
        C[4]["text"] = C[4]["text"].replace("above", "below")
        self.assertFalse(checker.check(C, self.F, card=True)["agreement"]["agreement_pass"])

    def test_flag_omitted_fails(self):
        C = [c for c in self.C if "flags.out_of_range.reason" not in c["fields"]]
        r = checker.check(C, self.F, card=True)
        self.assertIn("out_of_range", r["flags_omitted"])
        self.assertFalse(r["pass"])

    def test_spurious_out_of_range(self):
        F = facts_v3(record(ood=()))
        C = good_claims(F) + [{"text": "The inputs are out of the training range.", "fields": []}]
        self.assertIn("out_of_range", checker.check(C, F, card=True)["flags_spurious"])
        C = good_claims(F) + [{"text": "No input is outside the training range.", "fields": ["flags.out_of_range.active"]}]
        self.assertTrue(checker.check(C, F, card=True)["pass"])

    def test_tested_and_agree(self):
        F = facts_v3(record(tier="tested", sides=("above", "above"), conf80="{1}", ood=()))
        r = checker.check(good_claims(F), F, card=True)
        self.assertTrue(r["pass"], r)
        self.assertFalse(r["card_tier_required"])

    def test_v1_path_unchanged(self):
        self.assertNotIn("system.version", {"risk.tier": "lower third"})


if __name__ == "__main__":
    unittest.main()
