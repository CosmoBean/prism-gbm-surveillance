"""Reliability card: situations, tier rule, bootstrap AUC, card building, card facts and the checker's card rule
(synthetic data only)."""

from __future__ import annotations

import unittest

import numpy as np

from prism.audit import reliability as R
from prism.report import checker
from prism.report.facts_card import card_facts


def row(cohort, cell, npos, nneg, aucs=None):
    r = {"cohort": cohort, "cell": cell, "n_scans": npos + nneg, "n_pos": npos, "n_neg": nneg, "n_patients": npos + nneg,
         "tier": R.tier(npos, nneg)}
    for p in R.PATHWAYS:
        a = (aucs or {}).get(p)
        r.update({f"{p}_auc": a, f"{p}_auc_lo": None if a is None else a - 0.1,
                  f"{p}_auc_hi": None if a is None else a + 0.1})
    return r


TABLE = [row("mu", "later_post_rt|et_not_increased", 38, 16, {"timeline": 0.58, "images": 0.77, "both": 0.61}),
         row("mu", "early_post_rt|et_increased", 1, 8),
         row("lumiere", "unknown|et_increased", 28, 21, {"timeline": 0.91, "images": 0.61, "both": 0.83})]
AGREE = [{**row("mu", "agree", 42, 70, {"timeline": 0.9, "images": 0.9, "both": 0.91}), "subset": "agree",
          "pct_progression_both_above": 0.73, "pct_progression_both_below": 0.04},
         {**row("mu", "disagree", 22, 47, {"timeline": 0.74, "images": 0.31, "both": 0.64}), "subset": "disagree",
          "pct_progression_timeline_above_images_below": 0.49, "pct_progression_images_above_timeline_below": 0.14}]


def rec(phase="early_post_rt", enh="et_increased", t=0.7, i=0.2, reasons=()):
    card = R.build_card(phase, enh, TABLE, "mu", {"timeline": t, "images": i}, {"timeline": 0.4, "images": 0.4},
                        list(reasons), AGREE)
    return {"reliability_card": card}


class Situations(unittest.TestCase):
    def test_phase_cells(self):
        self.assertEqual(R.phase_cell("pre_rt"), "before_rt_end")
        self.assertEqual(R.phase_cell("during_rt"), "before_rt_end")
        self.assertEqual(R.phase_cell("early_post_rt"), "early_post_rt")
        self.assertEqual(R.phase_cell("rt_date_unknown"), "unknown")
        self.assertEqual(R.phase_cell("no_rt"), "unknown")

    def test_enhancement(self):
        self.assertEqual(R.enhancement_state(np.nan, 1.0), "unknown")
        self.assertEqual(R.enhancement_state(0.05, 3.0), "et_absent")
        self.assertEqual(R.enhancement_state(2.0, np.nan), "no_previous")
        self.assertEqual(R.enhancement_state(2.0, None), "no_previous")
        self.assertEqual(R.enhancement_state(4.0, 2.0), "et_increased")       # +2 cc, +100%
        self.assertEqual(R.enhancement_state(2.6, 2.0), "et_not_increased")   # +0.6 cc
        self.assertEqual(R.enhancement_state(12.0, 10.0), "et_not_increased")  # +2 cc but +20%
        self.assertEqual(R.enhancement_state(1.5, 0.0), "et_increased")        # new enhancement from ~0 cc

    def test_tier_rule(self):
        self.assertEqual(R.tier(10, 10), "tested")
        self.assertEqual(R.tier(9, 50), "few cases")
        self.assertEqual(R.tier(50, 9), "few cases")
        self.assertEqual(R.tier(0, 1), "few cases")
        self.assertEqual(R.tier(0, 0), "not tested")


class Bootstrap(unittest.TestCase):
    def test_auc_and_ci(self):
        rng = np.random.default_rng(0)
        y = np.r_[np.ones(40), np.zeros(60)].astype(int)
        g = np.repeat(np.arange(50), 2)
        good = y + rng.normal(0, 0.5, 100)
        noise = rng.normal(0, 1, 100)
        self.assertAlmostEqual(R.auc(y, y.astype(float)), 1.0)
        self.assertAlmostEqual(R.auc(y, np.zeros(100)), 0.5)
        res = R.bootstrap_auc(y, {"a": good[None], "b": noise[None]}, g, {"all": np.ones(100, bool)}, n_boot=200)
        p, lo, hi = res[("a", "all")]
        self.assertTrue(lo <= p <= hi and p > 0.8)
        p, lo, hi = res[("b", "all")]
        self.assertTrue(lo < 0.5 < hi)
        # fixed seed: identical results
        self.assertEqual(res, R.bootstrap_auc(y, {"a": good[None], "b": noise[None]}, g, {"all": np.ones(100, bool)},
                                              n_boot=200))

    def test_repeat_masks(self):
        y = np.array([1, 0, 1, 0])
        S = np.array([[0.9, 0.1, 0.8, 0.2], [0.1, 0.9, 0.8, 0.2]])
        M = np.array([[1, 1, 0, 0], [0, 0, 1, 1]], bool)
        self.assertAlmostEqual(R.mean_auc(y, S, M), 1.0)


class Card(unittest.TestCase):
    def test_few_cases_no_auc(self):
        c = rec()["reliability_card"]
        self.assertEqual(c["tier"], "few cases")
        self.assertNotIn("timeline", c["evidence"]["mu"])
        self.assertEqual(c["evidence"]["lumiere"]["tier"], "not tested")
        self.assertFalse(c["agreement"]["agree"])
        self.assertEqual(c["agreement"]["measured"]["tier"], "tested")
        self.assertAlmostEqual(c["agreement"]["progression_rate_same_direction"], 0.49)  # timeline above, images below
        self.assertEqual(card_facts({"reliability_card": c})["card.agreement_progression_percent"], 49)
        self.assertTrue(c["inputs_in_range"]["in_range"])
        self.assertIn("few cases", R.render_text(c))

    def test_tested_shows_auc(self):
        c = rec("later_post_rt", "et_not_increased", 0.6, 0.6, ["rt_dose_gy = 80 outside training 1-99% [40, 60]"])
        F = card_facts(c)
        self.assertEqual(F["card.tier"], "tested")
        self.assertEqual(F["card.images.auc"], 0.77)
        self.assertEqual(F["card.pathways_agree"], "yes")
        self.assertEqual(F["card.inputs_in_range"], "no")
        self.assertNotIn("card.lumiere.images_auc", F)  # LUMIERE never saw this cell

    def test_not_tested(self):
        F = card_facts(rec("before_rt_end", "et_absent"))
        self.assertEqual(F["card.tier"], "not tested")
        self.assertTrue(F["card.tier_statement"].startswith("not tested"))
        self.assertFalse(any(k.startswith("card.timeline") for k in F))

    def test_no_card(self):
        self.assertEqual(card_facts({}), {})


class CheckerCardRule(unittest.TestCase):
    def F(self, *a, **k):
        return {"risk.percent": 52, "risk.tier": "middle third", **card_facts(rec(*a, **k))}

    def test_old_check_unchanged_without_flag(self):
        F = self.F()
        cl = [{"text": "The model estimates a 52% risk.", "fields": ["risk.percent"]}]
        out = checker.check(cl, F)
        self.assertTrue(out["pass"])
        self.assertNotIn("card", out)
        self.assertFalse(checker.check(cl, F, card=True)["pass"])  # few cases, tier not stated

    def test_tier_must_be_stated(self):
        F = self.F()
        ok = [{"text": "This situation has few cases in development: only 1 progression and 8 non-progression scans, "
                       "too few to show an AUC.", "fields": ["card.tier", "card.tier_statement"]}]
        out = checker.check(ok, F, card=True)
        self.assertTrue(out["pass"], out)
        uncited = [{"text": ok[0]["text"], "fields": ["card.n_progression", "card.n_no_progression"]}]
        self.assertFalse(checker.check(uncited, F, card=True)["card"]["tier_mentioned"])
        # prose (no citations): keywords suffice
        self.assertTrue(checker.card_check([{"text": ok[0]["text"], "fields": []}], F, cited=False)["tier_mentioned"])

    def test_not_tested_wording(self):
        F = self.F("before_rt_end", "et_absent")
        good = [{"text": "Performance in this situation has not been tested.", "fields": ["card.tier"]}]
        wrong = [{"text": "There are few cases of this situation.", "fields": ["card.tier"]}]
        self.assertTrue(checker.check(good, F, card=True)["pass"])
        c = checker.check(wrong, F, card=True)["card"]
        self.assertFalse(c["tier_mentioned"])
        self.assertTrue(c["tier_inconsistent"])

    def test_auc_must_match_card(self):
        F = self.F("later_post_rt", "et_not_increased", 0.6, 0.6)
        ok = [{"text": "In this situation the images reached an AUC of 0.77 (95% interval 0.67-0.87).",
               "fields": ["card.images.auc", "card.images.auc_low", "card.images.auc_high", "card.interval_level_percent"]}]
        self.assertTrue(checker.check(ok, F, card=True)["pass"])
        bad = [{"text": "The model has a development AUC of 0.70.", "fields": ["risk.percent"]}]
        c = checker.check(bad, F, card=True)["card"]
        self.assertEqual(c["unsupported_performance"][0]["numbers"], ["0.70"])
        # an AUC that is in a cited non-card field still fails the card rule
        F2 = {**F, "model.cv_auc": 0.7}
        bad2 = [{"text": "The model has a development AUC of 0.70.", "fields": ["model.cv_auc"]}]
        out = checker.check(bad2, F2, card=True)
        self.assertEqual(out["n_unsupported"], 0)
        self.assertFalse(out["pass"])

    def test_confidence_interval_is_not_a_performance_claim(self):
        F = self.F("later_post_rt", "et_not_increased", 0.6, 0.6)
        cl = [{"text": "The risk is 52% with a 95% confidence interval.", "fields": ["risk.percent"]}]
        self.assertEqual(checker.card_check(cl, F)["n_performance_claims"], 0)

    def test_overclaim(self):
        F = self.F()
        cl = [{"text": "The model has high confidence here; this situation has few cases (only 1 progression).",
               "fields": ["card.tier", "card.n_progression"]}]
        c = checker.check(cl, F, card=True)["card"]
        self.assertTrue(c["overclaims"])
        self.assertFalse(c["card_pass"])
        neg = [{"text": "This situation is not well validated: few cases, only 1 progression scan.",
                "fields": ["card.tier", "card.n_progression"]}]
        self.assertTrue(checker.check(neg, F, card=True)["pass"])

    def test_performed_is_not_performance(self):
        F = self.F()
        cl = [{"text": "This scan was performed 90 days from diagnosis.", "fields": []},
              {"text": "The model did not use performance status.", "fields": []},
              {"text": "Given the concordance between the criteria and the model, 3 flags.", "fields": []}]
        self.assertEqual(checker.card_check(cl, F)["n_performance_claims"], 0)


if __name__ == "__main__":
    unittest.main()
