"""Facts-only report field contract, using synthetic records only."""

import hashlib
import json
import unittest
from pathlib import Path

from prism.report.field_ablation import (
    FACTS_ONLY, FULL_EVIDENCE, facts_for_arm, freeze_manifest,
)
from prism.report import field_ablation
from tests.test_report_v3 import record
from tests.test_report_v3_1 import lumiere

EXCLUDED = ("pathway.", "pathways.", "conformal.", "card.", "flags.")


class TestFieldContract(unittest.TestCase):
    def test_facts_only_excludes_every_model_prefix(self):
        facts = facts_for_arm(record(), FACTS_ONLY)
        self.assertFalse([key for key in facts if key.startswith(EXCLUDED)])

    def test_shared_facts_match_the_full_contract(self):
        full = facts_for_arm(record(), FULL_EVIDENCE)
        facts_only = facts_for_arm(record(), FACTS_ONLY)
        for prefix in EXCLUDED:
            self.assertTrue(any(key.startswith(prefix) for key in full), prefix)
        self.assertEqual(facts_only, {key: value for key, value in full.items()
                                      if not key.startswith(EXCLUDED)})

    def test_availability_edges_keep_scan_facts(self):
        mu = facts_for_arm(record(), FACTS_ONLY)
        self.assertEqual(mu["scan.previous_available"], "yes")
        self.assertIn("meas.enhancing_change_since_previous_statement", mu)
        self.assertIn("meas.flair_hyperintensity_change_since_previous_cc", mu)
        self.assertNotIn("scan.rater_statement", mu)

        lu = facts_for_arm(lumiere(rater=True), FACTS_ONLY)
        self.assertEqual(lu["scan.rater_statement"],
                         "The rater recorded this scan as within 3 months after radiotherapy: yes.")
        self.assertIn("meas.enhancing_change_since_previous_statement", lu)

        missing = facts_for_arm(lumiere(measured=False), FACTS_ONLY)
        self.assertEqual(missing["meas.available"], "no")
        self.assertEqual(missing["scan.previous_available"], "no")
        self.assertNotIn("meas.enhancing_cc", missing)
        self.assertIn("scan.rater_statement", missing)
        for facts in (mu, lu, missing):
            self.assertFalse([key for key in facts if key.startswith(EXCLUDED)])

    def test_unknown_arm_fails_closed(self):
        with self.assertRaises(ValueError):
            facts_for_arm(record(), "other")


class TestManifest(unittest.TestCase):
    def test_manifest_freezes_canonical_input_and_writer(self):
        root = Path(__file__).resolve().parents[1]
        source = root / "outputs/results/analyses/report_v3_1/records/eval.jsonl"
        frozen = root / "outputs/results/analyses/report_v3_1/FROZEN_hashes.txt"
        manifest = freeze_manifest()
        self.assertEqual(manifest["record_count"], 406)
        self.assertEqual(manifest["counts_by_cohort"], {"mu": 114, "lumiere": 162, "ucsf": 130})
        self.assertEqual(manifest["field_contract"][FACTS_ONLY]["excluded_prefixes"], list(EXCLUDED))
        self.assertEqual(manifest["field_contract"][FULL_EVIDENCE]["excluded_prefixes"], [])
        self.assertEqual(manifest["frozen_hashes_txt"], frozen.read_text())
        self.assertEqual(manifest["primary_writer"], {
            "key": "qwen3.8-27b", "id": "Qwen/Qwen3.8-27B",
            "revision": "1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0"})
        lines = source.read_bytes().splitlines(keepends=True)
        self.assertEqual(len(manifest["records"]), len(lines))
        for line, entry in zip(lines, manifest["records"]):
            self.assertEqual(entry["record_id"], json.loads(line)["record_id"])
            self.assertEqual(entry["sha256"], hashlib.sha256(line).hexdigest())


class TestFactsOnlyContract(unittest.TestCase):
    def setUp(self):
        self.facts = facts_for_arm(record(), FACTS_ONLY)

    def valid_claims(self):
        f = self.facts
        return [
            {"section": "scan", "text": f"Scan timing: {f['scan.phase']}.", "fields": ["scan.phase"]},
            {"section": "scan", "text": "A previous scan is available.", "fields": ["scan.previous_available"]},
            {"section": "measurements", "text": f"Enhancing tumour volume is {f['meas.enhancing_cc']:.1f} cc from automatic segmentation; indicative.",
             "fields": ["meas.available", "meas.enhancing_cc", "meas.label"]},
            {"section": "measurements", "text": f"FLAIR hyperintensity volume is {f['meas.flair_hyperintensity_cc']:.1f} cc.",
             "fields": ["meas.flair_hyperintensity_cc"]},
            {"section": "measurements", "text": f"Necrosis volume is {f['meas.necrosis_cc']:.1f} cc.",
             "fields": ["meas.necrosis_cc"]},
            {"section": "measurements", "text": f"Resection cavity volume is {f['meas.cavity_cc']:.1f} cc.",
             "fields": ["meas.cavity_cc"]},
            {"section": "longitudinal", "text": f["meas.enhancing_change_since_previous_statement"].capitalize() + ".",
             "fields": ["meas.enhancing_change_since_previous_statement"]},
            {"section": "longitudinal", "text": f["meas.flair_hyperintensity_change_since_previous_statement"].capitalize() + ".",
             "fields": ["meas.flair_hyperintensity_change_since_previous_statement"]},
            {"section": "provenance", "text": "Source cohort: MU-Glioma-Post.", "fields": ["system.cohort"]},
        ]

    def test_prompt_names_only_available_shared_keys(self):
        messages = field_ablation.facts_only_messages(self.facts)
        prompt = messages[0]["content"]
        for prefix in EXCLUDED:
            self.assertNotIn(prefix, prompt)
        self.assertIn("scan.phase", prompt)
        self.assertIn("meas.enhancing_cc", prompt)
        self.assertNotIn("meas.enhancing_change_since_earlier_minimum_statement", prompt)
        self.assertNotIn("system.task", messages[1]["content"])
        self.assertNotIn("scores out-of-fold", messages[1]["content"])

    def test_checker_rejects_model_leakage(self):
        claims = [{"section": "scan", "text": "The combined score is 0.80.", "fields": []}]
        self.assertFalse(field_ablation.check_facts_only(claims, self.facts)["pass"])

    def test_valid_report_and_segmentation_volume_pass(self):
        result = field_ablation.check_facts_only(self.valid_claims(), self.facts)
        self.assertTrue(result["pass"], result)

    def test_structured_parser_preserves_sections(self):
        raw = json.dumps({"sentences": self.valid_claims()})
        claims = field_ablation.parse_facts_only(raw)
        self.assertEqual(claims[0]["section"], "scan")
        self.assertTrue(field_ablation.check_facts_only(claims, self.facts)["pass"])

    def test_checker_rejects_malformed_field_list(self):
        claims = self.valid_claims()
        claims[0]["fields"] = [{"scan.phase": True}]
        self.assertFalse(field_ablation.check_facts_only(claims, self.facts)["pass"])

    def test_missing_volume_or_change_fails(self):
        for key in ("meas.enhancing_cc", "meas.enhancing_change_since_previous_statement"):
            claims = [c for c in self.valid_claims() if key not in c["fields"]]
            self.assertIn(key, field_ablation.check_facts_only(claims, self.facts)["required"]["missing"])

    def test_filtered_citation_fails(self):
        claims = self.valid_claims() + [{"section": "provenance", "text": "This is available.",
                                         "fields": ["pathway.combined.score"]}]
        self.assertFalse(field_ablation.check_facts_only(claims, self.facts)["pass"])

    def test_unrelated_existing_citation_fails(self):
        claims = self.valid_claims() + [{"section": "provenance", "text": "A separate observation was recorded.",
                                         "fields": ["scan.phase"]}]
        self.assertFalse(field_ablation.check_facts_only(claims, self.facts)["pass"])

    def test_direct_and_indirect_model_wording_fail(self):
        for text in ("The combined score is 0.80.", "The pathways agree.",
                     "The prediction set contains both outcomes.", "This has the tested tier.",
                     "Progression is likely.", "Review the scan."):
            with self.subTest(text=text):
                claims = self.valid_claims() + [{"section": "provenance", "text": text, "fields": []}]
                self.assertFalse(field_ablation.check_facts_only(claims, self.facts)["pass"])

    def test_render_contains_only_shared_content(self):
        report = field_ablation.render_facts_only("S", self.facts, self.valid_claims())
        self.assertIn("Enhancing tumour", report)
        self.assertIn("## Limitations", report)
        self.assertNotIn("## The two pathways", report)
        self.assertNotIn("combined score", report.lower())

    def test_renderer_rejects_leaking_prose(self):
        claims = self.valid_claims() + [{"section": "provenance", "text": "The pathway score is high.", "fields": []}]
        with self.assertRaises(ValueError):
            field_ablation.render_facts_only("S", self.facts, claims)

    def test_unmeasured_scan_requires_availability_not_volumes(self):
        facts = facts_for_arm(lumiere(measured=False), FACTS_ONLY)
        claims = [
            {"section": "scan", "text": f"Scan timing: {facts['scan.phase']}.", "fields": ["scan.phase"]},
            {"section": "scan", "text": "No previous scan is available.", "fields": ["scan.previous_available"]},
            {"section": "scan", "text": facts["scan.rater_statement"], "fields": ["scan.rater_statement"]},
            {"section": "measurements", "text": "No usable segmentation volumes are available.",
             "fields": ["meas.available"]},
        ]
        self.assertTrue(field_ablation.check_facts_only(claims, facts)["pass"])
        self.assertNotIn("meas.enhancing_cc", field_ablation.facts_only_messages(facts)[0]["content"])


if __name__ == "__main__":
    unittest.main()
