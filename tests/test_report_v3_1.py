"""Report v3.1: facts_v3_1 (rater statement, no number words), prompt v3.4 (conditional lines), and that the frozen
checker applies its v3 rules to the v3.1 facts. Synthetic records only."""

import copy
import unittest

from prism.report import checker
from prism.report.facts_v3 import facts_v3
from prism.report.facts_v3_1 import facts_v3_1
from prism.report.prompts_v3_1 import grounded_v3_1, system_prompt
try:
    from test_report_v3 import good_claims, record
except ImportError:  # run from the repo root
    from tests.test_report_v3 import good_claims, record


def lumiere(rater=False, nadir=False, agreement=True, measured=True):
    r = record()
    r.update(cohort="lumiere", rater_flag_within_3_months_after_rt=rater)
    r["card"]["own_cohort"] = "lumiere"
    r["card"]["evidence"] = {"lumiere": {**r["card"]["evidence"]["mu"], "cohort": "lumiere"}}
    m = r["measurements"]
    m["volumes_cc"] = {"et": 37.248, "snfh": 45.757, "necrosis_cavity": 4.1}
    if nadir:
        m["n_earlier_scans"] = 2
    if not agreement:
        r["card"]["agreement"].pop("progression_rate_same_direction")
    if not measured:
        r["measurements"] = {"volumes_cc": {}, "previous": None}
    r["provenance"]["models"]["images"] = "images_scan (3 volumes)"
    return r


def rater_claim(F):
    return {"text": "The rater did not record this scan as within 3 months after radiotherapy.",
            "fields": ["scan.rater_statement"]}


class TestFactsV31(unittest.TestCase):
    def test_version_kept_for_frozen_checker(self):
        F = facts_v3_1(record())
        self.assertEqual(F["system.version"], "v3")
        self.assertEqual(F["system.facts_version"], "v3.1")

    def test_rater_statement_replaces_yes_no(self):
        F = facts_v3_1(lumiere(rater=False))
        self.assertEqual(F["scan.rater_statement"],
                         "The rater recorded this scan as within 3 months after radiotherapy: no.")
        self.assertNotIn("scan.rater_within_3_months_after_rt", F)
        self.assertTrue(facts_v3_1(lumiere(rater=True))["scan.rater_statement"].endswith(": yes."))
        self.assertNotIn("scan.rater_statement", facts_v3_1(record()))

    def test_no_number_words(self):
        F3, F = facts_v3(lumiere()), facts_v3_1(lumiere())
        self.assertRegex(F3["pathway.images.based_on"], r"\bthree\b")
        self.assertIn("the 3 segmentation volumes", F["pathway.images.based_on"])
        for f in (F, facts_v3_1(record()), facts_v3_1(lumiere(measured=False))):
            self.assertFalse([k for k, v in f.items() if isinstance(v, str) and checker.NUMBER_WORDS.search(v)])

    def test_other_values_unchanged(self):
        F3, F = facts_v3(record()), facts_v3_1(record())
        self.assertEqual({k: v for k, v in F.items() if k != "system.facts_version"}, F3)


class TestCheckerOnV31(unittest.TestCase):
    """The v3 LUMIERE failure and its fix, under the unchanged checker."""

    def test_rater_sentence_with_3_passes_on_v3_1(self):
        F = facts_v3_1(lumiere())
        C = good_claims(F) + [rater_claim(F)]
        r = checker.check(C, F, card=True)
        self.assertTrue(r["pass"], r)

    def test_same_sentence_failed_on_v3_facts(self):
        F = facts_v3(lumiere())
        C = good_claims(F) + [{"text": rater_claim(F)["text"], "fields": ["scan.rater_within_3_months_after_rt"]}]
        r = checker.check(C, F, card=True)
        self.assertFalse(r["pass"])
        self.assertEqual(r["unsupported"][0]["unsupported_numbers"], ["3"])

    def test_number_word_still_fails(self):
        F = facts_v3_1(lumiere())
        C = good_claims(F) + [{"text": "The image pathway uses the three segmentation volumes.",
                               "fields": ["pathway.images.based_on"]}]
        self.assertFalse(checker.check(C, F, card=True)["pass"])


class TestPromptV34(unittest.TestCase):
    def test_rater_line_only_with_field(self):
        self.assertIn("scan.rater_statement", system_prompt(facts_v3_1(lumiere())))
        self.assertNotIn("rater", system_prompt(facts_v3_1(record())))

    def test_necrosis_lines_follow_fields(self):
        mu, lu = system_prompt(facts_v3_1(record())), system_prompt(facts_v3_1(lumiere()))
        self.assertIn("meas.necrosis_cc", mu)
        self.assertIn("meas.cavity_cc", mu)
        self.assertNotIn("necrosis_and_cavity", mu)
        self.assertIn("meas.necrosis_and_cavity_cc", lu)
        self.assertNotIn("meas.necrosis_cc", lu)

    def test_earlier_minimum_line_only_with_field(self):
        self.assertNotIn("earlier_minimum", system_prompt(facts_v3_1(lumiere(nadir=False))))
        F = facts_v3_1(lumiere(nadir=True))
        self.assertIn("meas.enhancing_change_since_earlier_minimum_statement", F)
        self.assertIn("meas.enhancing_change_since_earlier_minimum_statement", system_prompt(F))

    def test_agreement_statistic_line_only_with_field(self):
        self.assertIn("card.agreement_statement", system_prompt(facts_v3_1(lumiere())))
        self.assertNotIn("card.agreement_statement", system_prompt(facts_v3_1(lumiere(agreement=False))))

    def test_unmeasured_scan(self):
        F = facts_v3_1(lumiere(measured=False))
        sp = system_prompt(F)
        self.assertIn("no segmentation volumes", sp)
        self.assertNotIn("meas.enhancing_cc", sp)

    def test_every_key_named_exists(self):
        import re
        for rec in (record(), lumiere(), lumiere(nadir=True), lumiere(agreement=False), lumiere(measured=False)):
            F = facts_v3_1(rec)
            named = set(re.findall(r"\b((?:scan|meas|card|pathways?|conformal|flags)\.[a-z_.0-9]+[a-z0-9])\b",
                                   system_prompt(F)))
            named = {k for k in named if "<" not in k and not k.startswith("flags.<")}
            self.assertFalse({k for k in named if k not in F}, rec["cohort"])

    def test_messages(self):
        m = grounded_v3_1(facts_v3_1(record()))
        self.assertEqual([x["role"] for x in m], ["system", "user"])
        self.assertTrue(m[1]["content"].startswith("FACTS:\n{"))


if __name__ == "__main__":
    unittest.main()
