"""Facts-only report field contract, using synthetic records only."""

import hashlib
import json
import unittest
from pathlib import Path

from prism.report.field_ablation import (
    FACTS_ONLY, FULL_EVIDENCE, facts_for_arm, freeze_manifest,
)
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


if __name__ == "__main__":
    unittest.main()
