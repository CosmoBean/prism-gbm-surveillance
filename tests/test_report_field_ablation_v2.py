"""Facts-only v2: one specification renders the prompt and the checker. Synthetic records only."""

import copy
import unittest
from unittest.mock import patch

from prism.report import facts_only_v2
from prism.report.facts_v3 import PHASE_TEXT
from prism.report.field_ablation import FACTS_ONLY, FULL_EVIDENCE, _BANNED, facts_for_arm
from tests.test_report_v3 import record
from tests.test_report_v3_1 import lumiere

CRITERIA = ("fail_unparsed", "fail_section_order", "fail_multi_sentence", "fail_form", "fail_required_missing",
            "fail_unsupported_number", "fail_invalid_citation", "fail_forbidden", "fail_banned_term",
            "fail_clinical_inference")


def _facts(rec):
    return facts_for_arm(rec, FACTS_ONLY)


def unchanged_change_facts():
    r = record()
    r["measurements"]["change_from_previous_cc"]["et"] = 0.02
    return _facts(r)


def edge_facts():
    out = []
    for phase in PHASE_TEXT:
        r = record()
        r["phase_of_care"] = phase
        out.append(_facts(r))
    no_prev = record()
    no_prev["measurements"].update(previous=None, change_from_previous_cc={})
    smaller = record()
    smaller["measurements"]["change_from_previous_cc"]["et"] = -3.2
    ucsf = record()
    ucsf["cohort"] = "ucsf"
    no_cohort = _facts(record())
    no_cohort.pop("system.cohort")
    out += [_facts(no_prev), _facts(smaller), _facts(ucsf), no_cohort, unchanged_change_facts(),
            _facts(lumiere(rater=True)), _facts(lumiere(rater=False, nadir=True)),
            _facts(lumiere(measured=False)), _facts(lumiere(rater=True, measured=False))]
    return out


def reference_with_extra_sentence(text, section="provenance"):
    facts = _facts(record())
    claims = facts_only_v2.reference_report(facts)
    claims.append({"section": section, "text": text, "fields": ["system.cohort"]})
    return claims, facts


def _only(r, *expected):
    """The failing criteria are exactly `expected`."""
    return sorted(c for c in CRITERIA if r[c]) == sorted(expected)


class TestEdgeFixtures(unittest.TestCase):
    def test_edge_records_cover_the_protocol_cases(self):
        F = edge_facts()
        self.assertEqual({f["scan.phase"] for f in F}, set(PHASE_TEXT.values()))
        self.assertTrue(any(f["scan.previous_available"] == "no" for f in F))
        self.assertTrue(any(f["meas.available"] == "no" for f in F))
        self.assertTrue(any("scan.rater_statement" in f for f in F))
        self.assertTrue(any("system.cohort" not in f for f in F))
        for key in facts_only_v2._MEASURED_KEYS + facts_only_v2._CHANGE_KEYS:
            self.assertTrue(any(key in f for f in F), key)
        stmts = [f.get("meas.enhancing_change_since_previous_statement", "") for f in F]
        self.assertTrue(any("unchanged" in s and "(change below 0.1 cc)" in s for s in stmts))
        self.assertTrue(any("smaller" in s for s in stmts) and any("larger" in s for s in stmts))
        for f in F:
            self.assertFalse([k for k in f if k.startswith(("pathway.", "pathways.", "conformal.", "card.", "flags."))])


class TestSpecification(unittest.TestCase):
    def test_version_and_banned_list(self):
        self.assertEqual(facts_only_v2.SPEC_VERSION, "v2-iter0")
        for word in ("above", "below", "higher", "lower"):
            self.assertIsNotNone(_BANNED.search(word))
            self.assertIsNone(facts_only_v2.BANNED_V2.search(word))
        for word in ("score", "models", "prediction", "pathway", "conformal", "tier", "flags", "risk", "probability",
                     "likelihood", "uncertainty", "confidence", "outcomes", "progression", "recurrence",
                     "pseudoprogression", "radiation necrosis", "treatment effect", "agreement", "performance",
                     "accuracy", "reliability"):
            self.assertIsNotNone(facts_only_v2.BANNED_V2.search(f"The {word} here."), word)

    def test_iteration0_forms(self):
        f = _facts(lumiere(rater=True))
        sf = facts_only_v2.sentence_forms
        self.assertEqual(sf("scan.phase", f), [f"Scan timing: {f['scan.phase']}."])
        self.assertEqual(sf("scan.previous_available", f), ["A previous scan is available."])
        self.assertEqual(sf("scan.rater_statement", f), [f["scan.rater_statement"]])
        self.assertEqual(sf("system.cohort", f), ["Source cohort: LUMIERE."])
        self.assertEqual(sf("meas.available", f), ["Segmentation volumes are available."])
        self.assertEqual(sf("meas.label", f), ["Volumes are from the automatic segmentation and are indicative."])
        self.assertEqual(sf("meas.necrosis_and_cavity_cc", f)[0], "Necrosis and cavity volume is 4.1 cc.")
        self.assertEqual(sf("meas.flair_hyperintensity_cc", f)[0], "FLAIR hyperintensity volume is 45.8 cc.")
        s = f["meas.enhancing_change_since_previous_statement"]
        self.assertEqual(sf("meas.enhancing_change_since_previous_statement", f), [s[0].upper() + s[1:] + "."])
        self.assertEqual(sf("system.task", f), [])
        self.assertEqual(sf("pathway.combined.score", f), [])
        g = _facts(lumiere(measured=False))
        self.assertEqual(sf("scan.previous_available", g), ["No previous scan is available."])
        self.assertEqual(sf("meas.available", g), ["No usable segmentation volumes are available."])
        self.assertEqual(sf("system.cohort", _facts(record())), ["Source cohort: MU-Glioma-Post."])
        u = record()
        u["cohort"] = "ucsf"
        self.assertEqual(sf("system.cohort", _facts(u)), ["Source cohort: UCSF-ALPTDG."])
        self.assertEqual(sf("meas.cavity_cc", _facts(record()))[0], "Resection cavity volume is 0.0 cc.")

    def test_sections_and_required_keys(self):
        S = facts_only_v2.SECTION_OF
        self.assertEqual(S["scan.phase"], "scan")
        self.assertEqual(S["meas.enhancing_cc"], "measurements")
        self.assertEqual(S["meas.enhancing_change_since_earlier_minimum_statement"], "longitudinal")
        self.assertEqual(S["system.cohort"], "provenance")
        self.assertTrue(set(S.values()) <= set(facts_only_v2.FACTS_SECTIONS))
        for f in edge_facts():
            self.assertEqual(facts_only_v2.required_keys(f), facts_only_v2._required_keys(f))

    def test_reference_report_shape(self):
        for facts in edge_facts():
            ref = facts_only_v2.reference_report(facts)
            keys = [k for c in ref for k in c["fields"]]
            want = facts_only_v2.required_keys(facts) + (["system.cohort"] if "system.cohort" in facts else [])
            self.assertEqual(sorted(keys), sorted(want))
            order = [facts_only_v2.FACTS_SECTIONS.index(c["section"]) for c in ref]
            self.assertEqual(order, sorted(order))
            for c in ref:
                self.assertEqual(c["section"], facts_only_v2.SECTION_OF[c["fields"][0]])
                self.assertEqual(c["text"], facts_only_v2.sentence_forms(c["fields"][0], facts)[0])

    def test_messages_refuse_excluded_fields(self):
        with self.assertRaises(ValueError):
            facts_only_v2.messages(facts_for_arm(record(), FULL_EVIDENCE))
        msgs = facts_only_v2.messages(_facts(record()))
        self.assertEqual([m["role"] for m in msgs], ["system", "user"])
        self.assertNotIn("pathway", msgs[1]["content"])


class TestConsistency(unittest.TestCase):
    def test_every_prompt_form_passes_the_checker(self):
        for facts in edge_facts():
            for key in facts:
                for form in facts_only_v2.sentence_forms(key, facts)[:1]:
                    self.assertIn(form, facts_only_v2.messages(facts)[0]["content"])
            r = facts_only_v2.check(facts_only_v2.reference_report(facts), facts)
            self.assertTrue(r["pass"], r)

    def test_every_accepted_form_passes_alone(self):
        for facts in edge_facts():
            for key in facts:
                for form in facts_only_v2.sentence_forms(key, facts):
                    claim = {"section": facts_only_v2.SECTION_OF[key], "text": form, "fields": [key]}
                    r = facts_only_v2.check([claim], facts)
                    self.assertTrue(_only(r, "fail_required_missing"), (key, r))

    def test_consistency_errors_empty_on_edge_records(self):
        for facts in edge_facts():
            self.assertEqual(facts_only_v2.consistency_errors(facts), [])

    def test_consistency_errors_on_a_broken_form(self):
        facts = _facts(record())
        real = facts_only_v2.sentence_forms

        def number(key, f):
            return ["Scan timing: 99 days."] if key == "scan.phase" else real(key, f)

        def banned(key, f):
            return ["The risk is stated."] if key == "meas.label" else real(key, f)

        def dropped(key, f):
            return [] if key == "scan.previous_available" else real(key, f)

        for broken, key in ((number, "scan.phase"), (banned, "meas.label"), (dropped, "scan.previous_available")):
            with patch.object(facts_only_v2, "sentence_forms", broken):
                errors = facts_only_v2.consistency_errors(facts)
            self.assertTrue(errors, broken.__name__)
            self.assertTrue(any(key in e for e in errors), errors)
            self.assertFalse([e for e in errors if "99" in e or "risk" in e])

    def test_leading_the_volume_form_passes(self):
        facts = _facts(record())
        claims = facts_only_v2.reference_report(facts)
        for c in claims:
            if c["fields"] == ["meas.enhancing_cc"]:
                c["text"] = "The enhancing tumour volume is 37.2 cc."
        r = facts_only_v2.check(claims, facts)
        self.assertTrue(r["pass"], r)

    def test_case_and_whitespace_are_normalised(self):
        facts = _facts(record())
        claims = facts_only_v2.reference_report(facts)
        claims[0]["text"] = "  " + claims[0]["text"].upper().replace(" ", "  ") + " "
        self.assertTrue(facts_only_v2.check(claims, facts)["pass"])


class TestBannedTerms(unittest.TestCase):
    def test_below_inside_a_copied_statement_is_not_banned(self):
        facts = unchanged_change_facts()  # statement contains "change below 0.1 cc"
        self.assertIn("change below 0.1 cc", facts["meas.enhancing_change_since_previous_statement"])
        r = facts_only_v2.check(facts_only_v2.reference_report(facts), facts)
        self.assertFalse(r["fail_banned_term"]); self.assertTrue(r["pass"])

    def test_model_derived_terms_outside_statements_fail(self):
        for word in ("risk", "progression", "pathway", "confidence"):
            claims, facts = reference_with_extra_sentence(f"The {word} is not stated.")
            self.assertTrue(facts_only_v2.check(claims, facts)["fail_banned_term"])

    def test_statements_are_removed_only_for_the_three_text_checks(self):
        facts = _facts(record())
        statement = facts["meas.enhancing_change_since_previous_statement"]
        claims, facts = reference_with_extra_sentence(f"{statement} with progression.", "longitudinal")
        claims.sort(key=lambda c: facts_only_v2.FACTS_SECTIONS.index(c["section"]))
        r = facts_only_v2.check(claims, facts)
        self.assertTrue(r["fail_banned_term"]); self.assertTrue(r["fail_form"])


class TestNegatives(unittest.TestCase):
    def setUp(self):
        self.facts = _facts(record())
        self.ref = facts_only_v2.reference_report(self.facts)
        self.assertTrue(facts_only_v2.check(self.ref, self.facts)["pass"])

    def _claim(self, key):
        return next(c for c in self.ref if key in c["fields"])

    def test_changed_volume_number(self):
        c = self._claim("meas.enhancing_cc")
        c["text"] = c["text"].replace("37.2", "37.9")
        r = facts_only_v2.check(self.ref, self.facts)
        self.assertFalse(r["pass"])
        self.assertTrue(r["fail_form"]); self.assertTrue(r["fail_unsupported_number"])

    def test_invalid_citation(self):
        self._claim("meas.label")["fields"].append("pathway.combined.score")
        r = facts_only_v2.check(self.ref, self.facts)
        self.assertTrue(_only(r, "fail_invalid_citation"), r)

    def test_dropped_required_sentence(self):
        self.ref.remove(self._claim("meas.necrosis_cc"))
        r = facts_only_v2.check(self.ref, self.facts)
        self.assertTrue(_only(r, "fail_required_missing"), r)
        self.assertEqual(r["missing"], ["meas.necrosis_cc"])

    def test_swapped_sections(self):
        i = self.ref.index(self._claim("scan.phase"))
        j = self.ref.index(self._claim("meas.enhancing_cc"))
        self.ref[i], self.ref[j] = self.ref[j], self.ref[i]
        r = facts_only_v2.check(self.ref, self.facts)
        self.assertTrue(_only(r, "fail_section_order"), r)

    def test_two_sentences_in_one_claim(self):
        a, b = self._claim("scan.phase"), self._claim("scan.previous_available")
        a["text"], a["fields"] = a["text"] + " " + b["text"], a["fields"] + b["fields"]
        self.ref.remove(b)
        r = facts_only_v2.check(self.ref, self.facts)
        self.assertTrue(r["fail_multi_sentence"]); self.assertFalse(r["pass"])

    def test_clinical_inference(self):
        claims, facts = reference_with_extra_sentence("The tumour has grown.")
        r = facts_only_v2.check(claims, facts)
        self.assertTrue(r["fail_clinical_inference"]); self.assertFalse(r["pass"])
        self.assertIn("grown", r["non_form_words"])

    def test_forbidden(self):
        claims, facts = reference_with_extra_sentence("The scan should be repeated.")
        r = facts_only_v2.check(claims, facts)
        self.assertTrue(r["fail_forbidden"]); self.assertFalse(r["pass"])

    def test_claim_citing_no_key_fails_form(self):
        self._claim("meas.label")["fields"] = []
        r = facts_only_v2.check(self.ref, self.facts)
        self.assertTrue(r["fail_form"]); self.assertFalse(r["pass"])

    def test_unparsed(self):
        for claims in (None, [], [{"section": "elsewhere", "text": "x", "fields": []}],
                       [{"section": "scan", "text": 3, "fields": []}]):
            r = facts_only_v2.check(claims, self.facts)
            self.assertTrue(r["fail_unparsed"]); self.assertFalse(r["pass"]); self.assertFalse(r["parsed"])
            self.assertTrue(_only(r, "fail_unparsed"), r)
            self.assertEqual(r["missing"], []); self.assertEqual(r["non_form_words"], [])

    def test_result_keys(self):
        r = facts_only_v2.check(self.ref, self.facts)
        self.assertEqual(set(r), {"pass", "parsed", "n_claims", "missing", "non_form_words", *CRITERIA})
        self.assertEqual(r["n_claims"], len(self.ref))
        self.assertTrue(_only(r)); self.assertEqual(r["non_form_words"], [])


if __name__ == "__main__":
    unittest.main()
