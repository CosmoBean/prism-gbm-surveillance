"""Facts-only report field contract, using synthetic records only."""

import hashlib
import json
import re
import shutil
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pandas as pd

from prism.report.field_ablation import (
    FACTS_ONLY, FULL_EVIDENCE, facts_for_arm, freeze_manifest,
)
from prism.report import field_ablation
from tests.test_report_v3 import record
from tests.test_report_v3_1 import lumiere
from prism.analyses.report_field_ablation import (_facts_row, evaluate_step, generate_step, paired_rows,
                                                  paired_summary, requests_step, freeze_step,
                                                  verify_v31_baseline, summarise_arm)
from prism.analyses import report_field_ablation as pipeline

# Shapes of the cohorts' subject IDs (MU PatientID_####, LUMIERE Patient-###, UCSF ######_timeN, and
# "<cohort>|grade" record-ID prefixes). Tests use synthetic IDs only.
SUBJECT_ID = re.compile(r"PatientID_\d+|Patient-\d+|\b\d{5,6}_time\d+|\b(?:mu|lumiere|ucsf)\|grade\d")


def _jsonl_records(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_bytes().splitlines() if line.strip()]


EXCLUDED = ("pathway.", "pathways.", "conformal.", "card.", "flags.")
# Every prism/report/* source listed in the v3.1 FROZEN_hashes.txt; the provenance gate checks each one.
GATED_SOURCES = tuple(
    line.split()[0] for line in (Path(__file__).resolve().parents[1] / pipeline.BASE / "FROZEN_hashes.txt")
    .read_text().splitlines() if line.startswith("prism/report/"))


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
        committed = {**manifest, "records": [{"cohort": e["record_id"].split("|", 1)[0], "sha256": e["sha256"]}
                                             for e in manifest["records"]]}
        self.assertEqual(pipeline._manifest(root), committed)

    def test_committed_docs_hold_no_record_ids(self):
        root = Path(__file__).resolve().parents[1]
        manifest = pipeline._manifest(root)
        self.assertEqual(len(manifest["records"]), 406)
        for entry in manifest["records"]:
            self.assertEqual(set(entry), {"cohort", "sha256"})
        source = root / pipeline.BASE / "records/eval.jsonl"
        identifiers = set()
        for rec in _jsonl_records(source):
            identifiers |= {rec["record_id"], rec["scan_id"], rec["patient_id"]}
        for relative in ("docs/results/REPORT_FIELD_ABLATION_PLAN.md", "docs/results/REPORT_FIELD_ABLATION.md"):
            text = (root / relative).read_text()
            with self.subTest(doc=relative):
                self.assertNotIn('"record_id"', text)
                self.assertIsNone(SUBJECT_ID.search(text))
                self.assertEqual({i for i in identifiers if i in text}, set())

    def test_subject_id_pattern_matches_each_cohort_id_shape(self):
        # Synthetic IDs in each cohort's shape.
        for synthetic in ("mu|grade4|PatientID_0001_Timepoint_1", "PatientID_0001", "lumiere|grade4|Patient-001_week-001",
                          "Patient-001", "ucsf|grade4|100001_time2", "100001_time2"):
            with self.subTest(synthetic=synthetic):
                self.assertIsNotNone(SUBJECT_ID.search(synthetic))


def _copy_gated_root(source_root: Path, root: Path) -> None:
    for relative in ("docs/results/REPORT_FIELD_ABLATION_PLAN.md", *GATED_SOURCES, *
                     (f"outputs/results/analyses/report_v3_1/{name}" for name in pipeline.BASE_FILES)):
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_root / relative, target)


def _gated_steps() -> dict:
    return {"freeze_step": freeze_step, "requests_step": requests_step,
            "generate_step": generate_step, "evaluate_step": evaluate_step,
            "render_step": pipeline.render_step, "stress_step": pipeline.stress_step,
            "requests_step[stress]": lambda r, o: requests_step(r, o, set_name="stress"),
            "generate_step[stress]": lambda r, o: generate_step(r, o, set_name="stress"),
            "evaluate_stress_step": pipeline.evaluate_stress_step}


class TestProvenanceAndPairing(unittest.TestCase):
    def test_canonical_baseline_passes_provenance_gate(self):
        root = Path(__file__).resolve().parents[1]
        manifest = verify_v31_baseline(root)
        self.assertEqual(manifest["record_count"], 406)

    def test_changed_frozen_checker_blocks_every_gated_step(self):
        source_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _copy_gated_root(source_root, root)
            out = root / "ablation"
            freeze_step(root, out)
            checker = root / "prism/report/checker.py"
            checker.write_bytes(checker.read_bytes() + b"\n# changed after freeze\n")
            with patch("prism.analyses.report_field_ablation.subprocess.run",
                       side_effect=AssertionError("model runner must not start")):
                for name, step in _gated_steps().items():
                    with self.subTest(step=name):
                        with self.assertRaisesRegex(RuntimeError, "checker.*hash"):
                            step(root, out)

    def test_changed_non_checker_frozen_source_blocks_every_gated_step(self):
        source_root = Path(__file__).resolve().parents[1]
        self.assertIn("prism/report/facts_v3_1.py", GATED_SOURCES)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _copy_gated_root(source_root, root)
            out = root / "ablation"
            freeze_step(root, out)
            facts = root / "prism/report/facts_v3_1.py"
            facts.write_bytes(facts.read_bytes() + b"\n# changed after freeze\n")
            with patch("prism.analyses.report_field_ablation.subprocess.run",
                       side_effect=AssertionError("model runner must not start")):
                for name, step in _gated_steps().items():
                    with self.subTest(step=name):
                        with self.assertRaisesRegex(
                                RuntimeError, r"frozen source hash mismatch: prism/report/facts_v3_1\.py"):
                            step(root, out)

    def test_freeze_rejects_a_changed_v31_record_hash(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            copy = Path(directory)
            paths = (
                "outputs/results/analyses/report_v3_1/records/eval.jsonl",
                *GATED_SOURCES,
                "outputs/results/analyses/report_v3_1/FROZEN_hashes.txt",
                "outputs/results/analyses/report_v3_1/llm/outputs_eval.jsonl",
                "outputs/results/analyses/report_v3_1/checks_eval.csv",
                "outputs/results/analyses/report_v3_1/summary_eval.csv",
                "outputs/results/analyses/report_v3_1/stress.csv",
                "outputs/results/analyses/report_v3_1/summary_stress.csv",
            )
            for relative in paths:
                target = copy / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(root / relative, target)
            target = copy / paths[0]
            target.write_bytes(target.read_bytes().replace(b'"schema":', b'"schema" :', 1))
            with self.assertRaisesRegex(RuntimeError, "record hash"):
                verify_v31_baseline(copy)

    def test_gate_derives_record_ids_from_verified_source_lines_in_order(self):
        root = Path(__file__).resolve().parents[1]
        manifest = verify_v31_baseline(root)
        source = _jsonl_records(root / pipeline.BASE / "records/eval.jsonl")
        self.assertEqual([e["record_id"] for e in manifest["records"]], [r["record_id"] for r in source])
        self.assertEqual([e["cohort"] for e in manifest["records"]], [r["cohort"] for r in source])
        self.assertNotIn("record_id", pipeline._manifest(root)["records"][0])

    def test_gate_rejects_reordered_source_lines_and_changed_cohort(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            copy = Path(directory)
            _copy_gated_root(root, copy)
            target = copy / pipeline.BASE / "records/eval.jsonl"
            lines = target.read_bytes().splitlines(keepends=True)
            target.write_bytes(b"".join([lines[1], lines[0], *lines[2:]]))
            with self.assertRaisesRegex(RuntimeError, "record hash"):
                verify_v31_baseline(copy)
            target.write_bytes(b"".join(lines))
            plan = copy / pipeline.MANIFEST
            text = plan.read_text()
            first = text.index('"cohort": "mu"', text.index('"records"'))
            plan.write_text(text[:first] + '"cohort": "ucsf"' + text[first + len('"cohort": "mu"'):])
            with self.assertRaisesRegex(RuntimeError, "record hash mismatch"):
                verify_v31_baseline(copy)

    def test_gate_rejects_changed_full_output_even_when_counts_remain_unchanged(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            copy = Path(directory)
            paths = (
                *GATED_SOURCES,
                "outputs/results/analyses/report_v3_1/records/eval.jsonl",
                "outputs/results/analyses/report_v3_1/FROZEN_hashes.txt",
                "outputs/results/analyses/report_v3_1/llm/requests_eval.jsonl",
                "outputs/results/analyses/report_v3_1/llm/outputs_eval.jsonl",
                "outputs/results/analyses/report_v3_1/llm/outputs_eval.jsonl.meta.json",
                "outputs/results/analyses/report_v3_1/checks_eval.csv",
                "outputs/results/analyses/report_v3_1/summary_eval.csv",
                "outputs/results/analyses/report_v3_1/stress.csv",
                "outputs/results/analyses/report_v3_1/summary_stress.csv",
            )
            for relative in paths:
                target = copy / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(root / relative, target)
            target = copy / "outputs/results/analyses/report_v3_1/llm/outputs_eval.jsonl"
            target.write_bytes(target.read_bytes().replace(b"The scan", b"This scan", 1))
            with self.assertRaisesRegex(RuntimeError, "baseline artifact hash"):
                verify_v31_baseline(copy)

    def test_pairing_retains_missing_output_as_a_failure(self):
        rec = {"record_id": "a", "cohort": "mu", "patient_id": "p"}
        full_ok = {"scan_id": "a", "pass": True, "parsed": True, "missing_output": False}
        paired = paired_rows(records={"a": rec}, full={"a": full_ok}, facts_only={})
        self.assertTrue(bool(paired.loc[0, "facts_only_missing_output"]))
        self.assertFalse(bool(paired.loc[0, "facts_only_pass"]))

    def test_summary_uses_all_records_including_missing_outputs(self):
        rows = [
            {"scan_id": "a", "cohort": "mu", "pass": True, "parsed": True,
             "missing_output": False, "finish_reason": "stop", "required_content_pass": True,
             "model_leak": False, "words": 12, "n_prompt_tokens": 10, "n_output_tokens": 6},
            {"scan_id": "b", "cohort": "mu", "pass": False, "parsed": False,
             "missing_output": True, "finish_reason": None, "required_content_pass": False,
             "model_leak": False, "words": 0, "n_prompt_tokens": None, "n_output_tokens": None},
        ]
        summary = summarise_arm(rows)
        all_row = summary.loc[summary.cohort == "all"].iloc[0]
        self.assertEqual(int(all_row["n"]), 2)
        self.assertEqual(int(all_row["pass"]), 1)
        self.assertEqual(int(all_row["failed"]), 1)
        self.assertEqual(int(all_row["unparsed"]), 1)
        self.assertEqual(int(all_row["missing_output"]), 1)
        self.assertEqual(float(all_row["pass_rate"]), 0.5)

    def test_unparsed_model_claim_still_counts_as_leakage(self):
        rec = record()
        rec["patient_id"] = "synthetic-patient"
        row = _facts_row(rec["record_id"], rec, {"text": "The model score is high.",
                                                   "finish_reason": "stop", "n_prompt_tokens": 10,
                                                   "n_output_tokens": 8})
        self.assertFalse(row["parsed"])
        self.assertTrue(row["model_leak"])
        self.assertEqual(row["words"], 5)

    def test_generation_retries_only_the_identical_whole_batch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            baseline = root / "outputs/results/analyses/report_v3_1/llm/outputs_eval.jsonl"
            baseline.parent.mkdir(parents=True)
            baseline.write_text('{"id":"eval|a","text":"full"}\n')
            Path(str(baseline) + ".meta.json").write_text('{"n":1}\n')
            out = root / "ablation"
            (out / "llm").mkdir(parents=True)
            request = out / "llm/requests_facts_only.jsonl"
            request.write_text('{"id":"eval|a"}\n')
            commands = []

            def local_batch(cmd, **kwargs):
                commands.append(cmd)
                target = Path(cmd[cmd.index("--out") + 1])
                target.write_text(f'{{"id":"eval|a","text":"attempt{len(commands)}"}}\n')
                if len(commands) == 2:
                    Path(str(target) + ".meta.json").write_text('{"n":1}\n')
                return SimpleNamespace(returncode=1 if len(commands) == 1 else 0)

            with patch("prism.analyses.report_field_ablation._guard_requests"), patch(
                    "prism.analyses.report_field_ablation.subprocess.run", side_effect=local_batch):
                generate_step(root, out)
            self.assertEqual(len(commands), 2)
            self.assertEqual(commands[0][commands[0].index("--requests") + 1], str(request))
            self.assertEqual(commands[1][commands[1].index("--requests") + 1], str(request))
            self.assertEqual(request.read_text(), '{"id":"eval|a"}\n')
            self.assertIn("attempt2", (out / "llm/outputs_facts_only.jsonl").read_text())
            self.assertTrue((out / "llm/outputs_facts_only_attempt1.jsonl").exists())
            self.assertTrue((out / "llm/outputs_facts_only_attempt1.jsonl.meta.json").exists())

    def test_generation_puts_the_llm_env_bin_first_on_path(self):
        # vLLM's flashinfer JIT needs the LLM env's tools (ninja) on PATH, as report_v3/report_v3_1 provide.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            out = root / "ablation"
            (out / "llm").mkdir(parents=True)
            request = out / "llm/requests_facts_only.jsonl"
            request.write_text('{"id":"eval|a"}\n')
            envs = []

            def local_batch(cmd, **kwargs):
                envs.append(kwargs["env"])
                target = Path(cmd[cmd.index("--out") + 1])
                target.write_text('{"id":"eval|a","text":"ok"}\n')
                Path(str(target) + ".meta.json").write_text('{"n":1}\n')
                return SimpleNamespace(returncode=0)

            from prism.analyses import report_v3 as R3
            with patch.dict("os.environ", {"PATH": "/usr/bin:/bin"}), patch(
                    "prism.analyses.report_field_ablation.subprocess.run", side_effect=local_batch):
                pipeline._whole_batch(root, request, out / "llm/outputs_facts_only.jsonl", lambda: None)
            self.assertEqual(len(envs), 1)
            self.assertEqual(envs[0]["PATH"], f"{R3.LLM_ENV}/bin:/usr/bin:/bin")

    def test_paired_difference_uses_record_denominator_and_patient_clusters(self):
        records = {"a1": {"cohort": "mu", "patient_id": "a"},
                   "a2": {"cohort": "mu", "patient_id": "a"},
                   "b1": {"cohort": "mu", "patient_id": "b"}}
        full = {rid: {"pass": True, "parsed": True, "required_content_pass": True}
                for rid in records}
        facts = {"a1": {"pass": False, "parsed": True, "required_content_pass": False},
                 "a2": {"pass": False, "parsed": True, "required_content_pass": False},
                 "b1": {"pass": True, "parsed": True, "required_content_pass": True}}
        summary = paired_summary(paired_rows(records, full, facts))
        row = summary.loc[summary.cohort == "all"].iloc[0]
        self.assertEqual(int(row["n"]), 3)
        self.assertEqual(int(row["n_patients"]), 2)
        self.assertAlmostEqual(row["pass_difference_full_minus_facts_only"], 2 / 3)
        self.assertGreaterEqual(row["pass_difference_ci_high"], row["pass_difference_ci_low"])

    def test_generation_retains_metadata_when_local_runner_cannot_start(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            baseline = root / "outputs/results/analyses/report_v3_1/llm/outputs_eval.jsonl"
            baseline.parent.mkdir(parents=True)
            baseline.write_text('{"id":"eval|a","text":"full"}\n')
            Path(str(baseline) + ".meta.json").write_text('{"n":1}\n')
            out = root / "ablation"
            (out / "llm").mkdir(parents=True)
            (out / "llm/requests_facts_only.jsonl").write_text('{"id":"eval|a"}\n')
            with patch("prism.analyses.report_field_ablation._guard_requests"), patch(
                    "prism.analyses.report_field_ablation.subprocess.run", side_effect=OSError("runner unavailable")):
                generate_step(root, out)
            for attempt in (1, 2):
                meta = out / f"llm/outputs_facts_only_attempt{attempt}.jsonl.meta.json"
                self.assertTrue(meta.exists())
                self.assertFalse(json.loads(meta.read_text())["complete"])
            self.assertEqual((out / "llm/outputs_facts_only.jsonl").read_text(), "")
            final = json.loads((out / "llm/outputs_facts_only.jsonl.meta.json").read_text())
            self.assertFalse(final["complete"])
            self.assertEqual(final["n_attempts"], 2)

    def test_double_batch_failure_still_yields_failed_summaries(self):
        rec = record()
        rec["patient_id"] = "synthetic-patient"
        rid = rec["record_id"]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            baseline = root / "outputs/results/analyses/report_v3_1"
            (baseline / "llm").mkdir(parents=True)
            full_line = json.dumps({"id": f"eval|{rid}", "text": "{}", "finish_reason": "stop",
                                    "n_prompt_tokens": 10, "n_output_tokens": 2}) + "\n"
            (baseline / "llm/outputs_eval.jsonl").write_text(full_line)
            (baseline / "llm/outputs_eval.jsonl.meta.json").write_text('{"n":1,"batch_wall_s":5}\n')
            (baseline / "checks_eval.csv").write_text(
                "scan_id,cohort,pass,parsed,finish_reason,n_output_tokens,words,card_tier_stated,fail_required_missing\n"
                f"{rid},mu,True,True,stop,2,2,True,False\n")
            out = root / "ablation"
            (out / "llm").mkdir(parents=True)
            (out / "llm/requests_facts_only.jsonl").write_text(json.dumps({"id": f"eval|{rid}"}) + "\n")
            calls = []

            def failing_batch(cmd, **kwargs):
                calls.append(cmd)
                target = Path(cmd[cmd.index("--out") + 1])
                target.write_text('{"id":"eval|' + rid + '","text":"partial')  # crashed mid-write
                return SimpleNamespace(returncode=1)

            with patch("prism.analyses.report_field_ablation._guard_requests"), patch(
                    "prism.analyses.report_field_ablation._records", return_value={rid: rec}), patch(
                    "prism.analyses.report_field_ablation.subprocess.run", side_effect=failing_batch):
                generate_step(root, out)
                evaluate_step(root, out)
            self.assertEqual(len(calls), 2)
            for attempt in (1, 2):
                self.assertIn("partial", (out / f"llm/outputs_facts_only_attempt{attempt}.jsonl").read_text())
            checks = pd.read_csv(out / "checks_facts_only.csv")
            self.assertEqual(len(checks), 1)
            self.assertTrue(bool(checks.loc[0, "missing_output"]))
            self.assertFalse(bool(checks.loc[0, "pass"]))
            summary = pd.read_csv(out / "summary_facts_only.csv").set_index("cohort")
            self.assertEqual(int(summary.loc["all", "n"]), 1)
            self.assertEqual(int(summary.loc["all", "failed"]), 1)
            self.assertEqual(int(summary.loc["all", "missing_output"]), 1)
            self.assertFalse(bool(summary.loc["all", "batch_complete"]))
            self.assertEqual(int(summary.loc["all", "n_attempts"]), 2)
            paired = pd.read_csv(out / "paired_rows.csv")
            self.assertEqual(paired.scan_id.tolist(), [rid])
            self.assertTrue(bool(paired.loc[0, "facts_only_missing_output"]))
            self.assertTrue((out / "paired_summary.csv").exists())

    def test_retry_runtime_and_cost_include_the_failed_attempt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            baseline = root / "outputs/results/analyses/report_v3_1/llm/outputs_eval.jsonl"
            baseline.parent.mkdir(parents=True)
            baseline.write_text('{"id":"eval|a","text":"full"}\n')
            Path(str(baseline) + ".meta.json").write_text('{"n":1}\n')
            out = root / "ablation"
            (out / "llm").mkdir(parents=True)
            (out / "llm/requests_facts_only.jsonl").write_text('{"id":"eval|a"}\n')
            calls = []

            def flaky_batch(cmd, **kwargs):
                calls.append(cmd)
                if len(calls) == 2:
                    target = Path(cmd[cmd.index("--out") + 1])
                    target.write_text('{"id":"eval|a","text":"ok"}\n')
                    Path(str(target) + ".meta.json").write_text(
                        '{"n":1,"batch_wall_s":80,"batch_s_per_request":80,"gpu_name":"synthetic"}\n')
                return SimpleNamespace(returncode=1 if len(calls) == 1 else 0)

            with patch("prism.analyses.report_field_ablation._guard_requests"), patch(
                    "prism.analyses.report_field_ablation.subprocess.run", side_effect=flaky_batch), patch(
                    "prism.analyses.report_field_ablation.time.monotonic", side_effect=[0.0, 30.0, 30.0, 130.0]):
                generate_step(root, out)
            meta = json.loads((out / "llm/outputs_facts_only.jsonl.meta.json").read_text())
            self.assertTrue(meta["complete"])
            self.assertEqual([a["process_wall_s"] for a in meta["attempts"]], [30.0, 100.0])
            self.assertEqual([a["returncode"] for a in meta["attempts"]], [1, 0])
            self.assertEqual(meta["attempts"][1]["batch_wall_s"], 80)
            self.assertEqual(meta["total_process_wall_s"], 130.0)
            self.assertEqual(meta["total_batch_wall_s"], 80)
            attempt1 = json.loads((out / "llm/outputs_facts_only_attempt1.jsonl.meta.json").read_text())
            self.assertEqual(attempt1["process_wall_s"], 30.0)
            rows = [{"scan_id": "a", "cohort": "mu", "pass": True, "parsed": True, "missing_output": False,
                     "finish_reason": "stop", "required_content_pass": True, "model_leak": False,
                     "words": 3, "n_prompt_tokens": 1, "n_output_tokens": 1}]
            row = summarise_arm(rows, meta, gpu_hour_price_usd=3.6).set_index("cohort").loc["all"]
            self.assertEqual(float(row["total_process_wall_s"]), 130.0)
            self.assertEqual(int(row["n_attempts"]), 2)
            self.assertEqual(json.loads(row["attempt_process_wall_s"]), [30.0, 100.0])
            self.assertAlmostEqual(float(row["estimated_batch_cost_usd"]), 0.13)

    def test_requests_write_separate_aligned_arms_from_synthetic_record(self):
        rec = record()
        rid = rec["record_id"]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            baseline = root / "outputs/results/analyses/report_v3_1/llm/requests_eval.jsonl"
            baseline.parent.mkdir(parents=True)
            baseline.write_text(json.dumps({"id": f"eval|{rid}", "messages": [{"role": "user",
                                                                               "content": "full arm"}]}) + "\n")
            out = root / "ablation"
            manifest = {"records": [{"record_id": rid}]}
            with patch("prism.analyses.report_field_ablation._guard", return_value=manifest), patch(
                    "prism.analyses.report_field_ablation._records", return_value={rid: rec}):
                requests_step(root, out)
            full = json.loads((out / "llm/requests_full_evidence.jsonl").read_text())
            facts = json.loads((out / "llm/requests_facts_only.jsonl").read_text())
            self.assertEqual(full["id"], facts["id"])
            self.assertIn("full arm", full["messages"][0]["content"])
            self.assertNotIn("pathway.", json.dumps(facts["messages"]))
            self.assertNotIn("conformal.", json.dumps(facts["messages"]))

    def test_evaluation_counts_absent_facts_output_in_every_denominator(self):
        rec = record()
        rec["patient_id"] = "synthetic-patient"
        rid = rec["record_id"]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            baseline = root / "outputs/results/analyses/report_v3_1"
            (baseline / "llm").mkdir(parents=True)
            full_line = json.dumps({"id": f"eval|{rid}", "text": "{}", "finish_reason": "stop",
                                    "n_prompt_tokens": 10, "n_output_tokens": 2}) + "\n"
            (baseline / "llm/outputs_eval.jsonl").write_text(full_line)
            (baseline / "checks_eval.csv").write_text(
                "scan_id,cohort,pass,parsed,finish_reason,n_output_tokens,words,card_tier_stated,fail_required_missing\n"
                f"{rid},mu,True,True,stop,2,2,True,False\n")
            out = root / "ablation"
            (out / "llm").mkdir(parents=True)
            (out / "llm/outputs_full_evidence.jsonl").write_text(full_line)
            with patch("prism.analyses.report_field_ablation._guard_requests"), patch(
                    "prism.analyses.report_field_ablation._records", return_value={rid: rec}):
                evaluate_step(root, out)
            facts_checks = pd.read_csv(out / "checks_facts_only.csv")
            facts_summary = pd.read_csv(out / "summary_facts_only.csv")
            paired = pd.read_csv(out / "paired_summary.csv")
            self.assertTrue(bool(facts_checks.loc[0, "missing_output"]))
            self.assertFalse(bool(facts_checks.loc[0, "pass"]))
            self.assertEqual(int(facts_summary.loc[facts_summary.cohort == "all", "n"].iloc[0]), 1)
            self.assertEqual(int(facts_summary.loc[facts_summary.cohort == "all", "failed"].iloc[0]), 1)
            self.assertEqual(float(paired.loc[paired.cohort == "all",
                                              "pass_difference_full_minus_facts_only"].iloc[0]), 1.0)


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

    def test_longitudinal_statement_cannot_carry_extra_clinical_conclusion(self):
        claims = self.valid_claims()
        claims[6]["text"] += " The tumour has grown."
        self.assertFalse(field_ablation.check_facts_only(claims, self.facts)["pass"])

    def test_volume_sentence_cannot_infer_tumour_growth(self):
        claims = self.valid_claims()
        claims[2]["text"] += " The tumour has grown."
        self.assertFalse(field_ablation.check_facts_only(claims, self.facts)["pass"])

    def test_volume_sentence_rejects_other_clinical_inferences(self):
        for inference in ("The tumour is enlarged.", "There is an increase in tumour burden.",
                          "This represents aggressive disease."):
            with self.subTest(inference=inference):
                claims = self.valid_claims()
                claims[2]["text"] += " " + inference
                self.assertFalse(field_ablation.check_facts_only(claims, self.facts)["pass"])

    def test_claim_cannot_append_a_second_sentence_with_allowed_words(self):
        for second in ("The scan is available.", "the scan is available."):
            with self.subTest(second=second):
                claims = self.valid_claims()
                claims[2]["text"] += " " + second
                self.assertFalse(field_ablation.check_facts_only(claims, self.facts)["pass"])

    def test_measurement_words_cannot_be_rearranged_into_clinical_claim(self):
        claims = self.valid_claims()
        claims[2]["text"] = ("Enhancing tumour volume is 37.2 cc from automatic segmentation; indicative; "
                             "the tumour is available.")
        self.assertFalse(field_ablation.check_facts_only(claims, self.facts)["pass"])

    def test_swapped_measurement_values_fail_even_with_both_citations(self):
        claims = self.valid_claims()
        claims[2]["text"] = ("Enhancing tumour volume is 45.8 cc and FLAIR hyperintensity volume is "
                             "37.2 cc from automatic segmentation; indicative.")
        claims[2]["fields"] = ["meas.available", "meas.enhancing_cc", "meas.flair_hyperintensity_cc", "meas.label"]
        claims.pop(3)
        self.assertFalse(field_ablation.check_facts_only(claims, self.facts)["pass"])

    def test_availability_claim_must_match_yes_or_no(self):
        claims = self.valid_claims() + [
            {"section": "provenance", "text": "No usable segmentation volumes are available.",
             "fields": ["meas.available"]},
        ]
        self.assertFalse(field_ablation.check_facts_only(claims, self.facts)["pass"])
        no_facts = facts_for_arm(lumiere(measured=False), FACTS_ONLY)
        self.assertFalse(field_ablation.check_facts_only(
            [{"section": "measurements", "text": "Segmentation volumes are available.",
              "fields": ["meas.available"]}], no_facts)["pass"])

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


def facts_only_claims(facts):
    """A passing facts-only report for record()-shaped facts (synthetic)."""
    claims = [
        {"section": "scan", "text": f"Scan timing: {facts['scan.phase']}.", "fields": ["scan.phase"]},
        {"section": "scan", "text": "A previous scan is available.", "fields": ["scan.previous_available"]},
        {"section": "measurements",
         "text": f"Enhancing tumour volume is {facts['meas.enhancing_cc']:.1f} cc from automatic segmentation; indicative.",
         "fields": ["meas.available", "meas.enhancing_cc", "meas.label"]},
        {"section": "measurements", "text": f"FLAIR hyperintensity volume is {facts['meas.flair_hyperintensity_cc']:.1f} cc.",
         "fields": ["meas.flair_hyperintensity_cc"]},
        {"section": "measurements", "text": f"Necrosis volume is {facts['meas.necrosis_cc']:.1f} cc.",
         "fields": ["meas.necrosis_cc"]},
        {"section": "measurements", "text": f"Resection cavity volume is {facts['meas.cavity_cc']:.1f} cc.",
         "fields": ["meas.cavity_cc"]},
    ]
    for key in ("meas.enhancing_change_since_previous_statement",
                "meas.flair_hyperintensity_change_since_previous_statement"):
        claims.append({"section": "longitudinal", "text": facts[key].capitalize() + ".", "fields": [key]})
    claims.append({"section": "provenance", "text": "Source cohort: MU-Glioma-Post.", "fields": ["system.cohort"]})
    return claims


def zero_change_record(record_id="mu|grade4|Z"):
    rec = record()
    rec["record_id"], rec["scan_id"] = record_id, record_id.split("|")[-1]
    m = rec["measurements"]
    m["previous"]["volumes_cc"]["et"] = m["volumes_cc"]["et"]
    m["change_from_previous_cc"]["et"] = 0.0
    return rec


def other_record(record_id="mu|grade4|S2"):
    rec = record()
    rec["record_id"] = record_id
    return rec


class TestStressContract(unittest.TestCase):
    def test_sampling_frame_excludes_records_ambiguous_by_construction(self):
        near_zero = record()
        near_zero["record_id"] = "mu|grade4|near"
        near_zero["measurements"]["volumes_cc"]["et"] = 0.0
        near_zero["measurements"]["change_from_previous_cc"]["et"] = -0.1  # new: "change below 0.1 cc"
        candidates = [zero_change_record(), near_zero]
        for rec in candidates:
            entry = pipeline._stress_candidate(rec)
            self.assertIsNotNone(entry, rec["record_id"])
            self.assertTrue(pipeline.ambiguous_by_construction(entry), rec["record_id"])
        pool = [other_record(f"mu|grade4|S{i}") for i in range(8)]
        self.assertFalse(any(pipeline.ambiguous_by_construction(pipeline._stress_candidate(r)) for r in pool))
        mixed = candidates + pool
        first = pipeline.shared_stress_records(mixed)
        second = pipeline.shared_stress_records(list(mixed))
        self.assertEqual(len(first), 6)
        self.assertEqual([e["perturbed_id"] for e in first], [e["perturbed_id"] for e in second])
        self.assertFalse({"mu|grade4|Z", "mu|grade4|near"} & {e["record_id"] for e in first})
        for entry in first:
            new = facts_for_arm(entry["record"], FACTS_ONLY)
            self.assertFalse(pipeline.ambiguous_by_construction(entry))
            old = facts_for_arm(other_record(entry["record_id"]), FACTS_ONLY)
            self.assertEqual(pipeline.facts_only_follows(entry, old, new, facts_only_claims(new))["status"],
                             "follows")

    @unittest.skipUnless((Path(__file__).resolve().parents[1] /
                          "outputs/results/analyses/report_v3_1/records/eval.jsonl").exists(), "v3.1 records absent")
    def test_real_sampling_frame_is_unambiguous_and_deterministic(self):
        root = Path(__file__).resolve().parents[1]
        records = list(pipeline._records(root).values())  # read only; nothing is written
        frame = pipeline.shared_stress_records(records, n=10 ** 6)
        self.assertEqual(len(frame), 217)
        self.assertFalse(any(pipeline.ambiguous_by_construction(e) for e in frame))
        first = pipeline.shared_stress_records(records)
        self.assertEqual(len(first), 6)
        self.assertEqual([e["perturbed_id"] for e in first],
                         [e["perturbed_id"] for e in pipeline.shared_stress_records(records)])

    def test_evaluate_stress_requires_generation_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            root, out, (guard, recs) = self.stress_root(directory, [record()])
            with guard, recs:
                pipeline.stress_step(root, out)
                pipeline.requests_step(root, out, set_name="stress")
                with self.assertRaisesRegex(RuntimeError, "generate"):
                    pipeline.evaluate_stress_step(root, out)

    def test_double_stress_batch_failure_is_visible_in_stress_summary(self):
        source = Path(__file__).resolve().parents[1] / "outputs/results/analyses/report_v3_1"
        with tempfile.TemporaryDirectory() as directory:
            root, out, (guard, recs) = self.stress_root(directory, [record(), other_record()])
            base = root / "outputs/results/analyses/report_v3_1"
            base.mkdir(parents=True)
            for name in ("stress.csv", "summary_stress.csv"):
                shutil.copyfile(source / name, base / name)
            calls = []

            def failing_batch(cmd, **kwargs):
                calls.append(cmd)
                Path(cmd[cmd.index("--out") + 1]).write_text('{"id":"stress|x","text":"partial')
                return SimpleNamespace(returncode=1)

            with guard, recs, patch("prism.analyses.report_field_ablation.subprocess.run",
                                    side_effect=failing_batch), patch(
                    "prism.analyses.report_field_ablation.time.monotonic", side_effect=[0.0, 30.0, 100.0, 140.0]):
                pipeline.stress_step(root, out)
                pipeline.requests_step(root, out, set_name="stress")
                generate_step(root, out, set_name="stress")
                pipeline.evaluate_stress_step(root, out)
            self.assertEqual(len(calls), 2)
            rows = pd.read_csv(out / "stress_facts_only.csv")
            self.assertEqual(len(rows), 2)
            self.assertEqual(set(rows.status), {"failed"})
            summary = pd.read_csv(out / "summary_stress_facts_only.csv").set_index("kind")
            for kind in ("enhancing_volume_change", "total"):
                row = summary.loc[kind]
                self.assertEqual((int(row["n"]), int(row["failed_output"])), (2, 2))
                self.assertFalse(bool(row["batch_complete"]))
                self.assertEqual(int(row["n_attempts"]), 2)
                self.assertAlmostEqual(float(row["total_process_wall_s"]), 70.0)
                self.assertEqual(json.loads(row["attempt_process_wall_s"]), [30.0, 40.0])

    def test_shared_volume_change_is_tested_in_both_arms(self):
        records = pipeline.shared_stress_records([record()])
        self.assertEqual(records[0]["kind"], "enhancing_volume_change")
        # The full arm's immutable v3.1 set already contains the same shared change (as et_change).
        self.assertIn(pipeline.V31_SHARED_KIND, pipeline.eligible_kinds(FULL_EVIDENCE))
        self.assertEqual(pipeline.V31_SHARED_KIND, "et_change")

    def test_model_only_v31_perturbations_are_not_run_for_facts_only(self):
        self.assertEqual(pipeline.eligible_kinds(FACTS_ONLY), ("enhancing_volume_change",))
        self.assertEqual(pipeline.eligible_kinds(FULL_EVIDENCE),
                         ("card_tier", "agreement", "et_change", "out_of_range", "conformal"))
        with self.assertRaises(ValueError):
            pipeline.eligible_kinds("other")

    def test_stress_record_keeps_pairing_and_exact_shared_field_updates(self):
        entry = pipeline.shared_stress_records([record()])[0]
        rec = entry["record"]
        self.assertEqual(entry["record_id"], "mu|grade4|S")
        self.assertEqual(entry["perturbed_id"], "mu|grade4|S|perturbed:enhancing_volume_change")
        self.assertEqual(rec["record_id"], entry["perturbed_id"])
        self.assertEqual(rec["scan_id"], "S")
        old = facts_for_arm(record(), FACTS_ONLY)
        new = facts_for_arm(rec, FACTS_ONLY)
        self.assertFalse([key for key in new if key.startswith(EXCLUDED)])
        changed = {key for key in set(old) | set(new) if old.get(key) != new.get(key)}
        self.assertEqual(set(entry["expected_updates"]), changed)
        self.assertTrue(changed)
        self.assertTrue(all(key.startswith("meas.enhancing_change_since_previous") for key in changed), changed)
        for key, (before, after) in entry["expected_updates"].items():
            self.assertEqual((old.get(key), new.get(key)), (before, after))
        self.assertEqual(entry["old_statement"], old["meas.enhancing_change_since_previous_statement"])
        self.assertEqual(entry["new_statement"], new["meas.enhancing_change_since_previous_statement"])
        self.assertEqual((entry["old"], entry["new"]), (3.5, -5.0))

    def test_sampling_is_fixed_by_seed_and_excludes_ineligible_records(self):
        pool = []
        for i in range(8):
            rec = record()
            rec["record_id"] = f"mu|grade4|S{i}"
            pool.append(rec)
        no_previous = record()
        no_previous["record_id"] = "mu|grade4|none"
        no_previous["measurements"]["previous"] = None
        noop = record()
        noop["record_id"] = "mu|grade4|noop"
        noop["measurements"]["volumes_cc"]["et"] = 0.0
        noop["measurements"]["change_from_previous_cc"]["et"] = -0.01
        records = pool + [no_previous, noop]
        first = pipeline.shared_stress_records(records, seed=pipeline.STRESS_SEED, n=6)
        second = pipeline.shared_stress_records(list(records), seed=pipeline.STRESS_SEED, n=6)
        self.assertEqual(len(first), 6)
        self.assertEqual([e["perturbed_id"] for e in first], [e["perturbed_id"] for e in second])
        self.assertFalse({"mu|grade4|none", "mu|grade4|noop"} & {e["record_id"] for e in first})
        order = [r["record_id"] for r in records]
        self.assertEqual([e["record_id"] for e in first],
                         sorted((e["record_id"] for e in first), key=order.index))
        self.assertEqual(pipeline.STRESS_N, 6)

    def test_facts_only_follows_new_statement_and_rejects_old(self):
        entry = pipeline.shared_stress_records([record()])[0]
        old = facts_for_arm(record(), FACTS_ONLY)
        new = facts_for_arm(entry["record"], FACTS_ONLY)
        claims = facts_only_claims(new)
        self.assertTrue(field_ablation.check_facts_only(claims, new)["pass"])
        result = pipeline.facts_only_follows(entry, old, new, claims)
        self.assertEqual(result["status"], "follows")
        self.assertTrue(result["follows"])

        stale = facts_only_claims(old)
        result = pipeline.facts_only_follows(entry, old, new, stale)
        self.assertEqual(result["status"], "not_follows")
        self.assertFalse(result["follows"])
        self.assertFalse(result["new_supported"])

        both = claims + [{"section": "longitudinal", "text": old["meas.enhancing_change_since_previous_statement"]
                          .capitalize() + ".", "fields": ["meas.enhancing_change_since_previous_statement"]}]
        result = pipeline.facts_only_follows(entry, old, new, both)
        self.assertEqual(result["status"], "not_follows")
        self.assertTrue(result["old_present"])

        missing = pipeline.facts_only_follows(entry, old, new, None)
        self.assertEqual(missing["status"], "failed")
        self.assertFalse(missing["follows"])

    def test_old_number_with_a_unique_representation_must_be_absent(self):
        entry = pipeline.shared_stress_records([record()])[0]
        old = facts_for_arm(record(), FACTS_ONLY)
        new = facts_for_arm(entry["record"], FACTS_ONLY)
        claims = facts_only_claims(new) + [{"section": "longitudinal", "text": "The earlier change was 3.5 cc.",
                                            "fields": ["meas.enhancing_change_since_previous_cc"]}]
        result = pipeline.facts_only_follows(entry, old, new, claims)
        self.assertEqual(result["status"], "not_follows")
        self.assertEqual(result["old_unique_hits"], ["3.5"])

    def test_zero_value_ambiguity_is_unscorable_not_a_failure(self):
        source = zero_change_record()
        self.assertEqual(pipeline.shared_stress_records([source]), [])  # excluded from the sampling frame
        entry = pipeline._stress_candidate(source)  # the unscorable branch remains as a guard
        self.assertEqual((entry["old"], entry["new"]), (0.0, -5.0))
        old = facts_for_arm(source, FACTS_ONLY)
        new = facts_for_arm(entry["record"], FACTS_ONLY)
        claims = facts_only_claims(new)  # "Resection cavity volume is 0.0 cc." is a correct, required sentence.
        self.assertTrue(field_ablation.check_facts_only(claims, new)["pass"])
        result = pipeline.facts_only_follows(entry, old, new, claims)
        self.assertEqual(result["status"], "unscorable")
        self.assertIsNone(result["follows"])
        self.assertEqual(result["old_unique_hits"], [])
        self.assertTrue(result["old_ambiguous_hits"])
        stale = facts_only_claims(old)
        self.assertEqual(pipeline.facts_only_follows(entry, old, new, stale)["status"], "not_follows")

    def test_stress_summary_keeps_unscorable_and_failed_rows_in_denominators(self):
        rows = [{"kind": "enhancing_volume_change", "status": status, "follows": follows,
                 "check_pass": check, "follows_and_pass": bool(follows) and check}
                for status, follows, check in (("follows", True, True), ("not_follows", False, True),
                                               ("unscorable", None, True), ("failed", False, False))]
        summary = pipeline.summarise_stress(pd.DataFrame(rows), pipeline.FACTS_RULE).set_index("kind")
        for kind in ("enhancing_volume_change", "total"):
            row = summary.loc[kind]
            self.assertEqual(int(row["n"]), 4)
            self.assertEqual(int(row["follows"]), 1)
            self.assertEqual(int(row["not_follows"]), 1)
            self.assertEqual(int(row["unscorable"]), 1)
            self.assertEqual(int(row["failed_output"]), 1)
            self.assertEqual(int(row["n_scorable"]), 3)
            self.assertEqual(int(row["check_pass"]), 3)

    def stress_root(self, directory, records):
        root = Path(directory)
        out = root / "ablation"
        out.mkdir()
        lookup = {r["record_id"]: r for r in records}
        patches = (patch("prism.analyses.report_field_ablation._guard"),
                   patch("prism.analyses.report_field_ablation._records", return_value=lookup))
        return root, out, patches

    def test_stress_set_is_written_once_and_never_overwritten(self):
        records = [record(), other_record()]
        with tempfile.TemporaryDirectory() as directory:
            root, out, (guard, recs) = self.stress_root(directory, records)
            with guard, recs:
                pipeline.stress_step(root, out)
                data = (out / "records/stress_shared.jsonl").read_bytes()
                log = pd.read_csv(out / "stress_log.csv")
                self.assertEqual(len(log), 2)
                self.assertEqual(set(log.kind), {"enhancing_volume_change"})
                self.assertEqual(set(log.seed), {pipeline.STRESS_SEED})
                with patch("prism.analyses.report_field_ablation.shared_stress_records",
                           side_effect=AssertionError("must not resample")):
                    pipeline.stress_step(root, out)
                self.assertEqual((out / "records/stress_shared.jsonl").read_bytes(), data)
                (out / "stress_log.csv").unlink()
                with self.assertRaisesRegex(RuntimeError, "stress"):
                    pipeline.stress_step(root, out)

    def test_stress_generation_uses_the_same_whole_batch_machinery(self):
        records = [record()]
        with tempfile.TemporaryDirectory() as directory:
            root, out, (guard, recs) = self.stress_root(directory, records)
            commands = []

            def failing_batch(cmd, **kwargs):
                commands.append(cmd)
                Path(cmd[cmd.index("--out") + 1]).write_text('{"id":"stress|x","text":"partial')
                return SimpleNamespace(returncode=1)

            with guard, recs, patch("prism.analyses.report_field_ablation.subprocess.run",
                                    side_effect=failing_batch):
                pipeline.stress_step(root, out)
                pipeline.requests_step(root, out, set_name="stress")
                request = out / "llm/requests_stress_facts_only.jsonl"
                rows = [json.loads(line) for line in request.read_text().splitlines()]
                self.assertEqual([r["id"] for r in rows],
                                 ["stress|mu|grade4|S|perturbed:enhancing_volume_change"])
                self.assertNotIn("pathway.", json.dumps(rows[0]["messages"]))
                final = generate_step(root, out, set_name="stress")
                self.assertEqual(len(commands), 2)
                self.assertTrue(all(c[c.index("--requests") + 1] == str(request) for c in commands))
                self.assertFalse(final["complete"])
                self.assertEqual(final["n_attempts"], 2)
                self.assertTrue((out / "llm/outputs_stress_facts_only_attempt2.jsonl").exists())
                self.assertFalse((out / "llm/outputs_full_evidence.jsonl").exists())
                self.assertIsNone(generate_step(root, out, set_name="stress"))
                self.assertEqual(len(commands), 2)

    def test_evaluate_stress_scores_facts_only_and_reports_full_v31_separately(self):
        records = [record(), other_record()]
        source = Path(__file__).resolve().parents[1] / "outputs/results/analyses/report_v3_1"
        with tempfile.TemporaryDirectory() as directory:
            root, out, (guard, recs) = self.stress_root(directory, records)
            base = root / "outputs/results/analyses/report_v3_1"
            base.mkdir(parents=True)
            for name in ("stress.csv", "summary_stress.csv"):
                shutil.copyfile(source / name, base / name)
            with guard, recs:
                pipeline.stress_step(root, out)
                pipeline.requests_step(root, out, set_name="stress")
                entries = {json.loads(line)["record_id"]: json.loads(line)
                           for line in (out / "records/stress_shared.jsonl").read_text().splitlines()}
                pid = "mu|grade4|S|perturbed:enhancing_volume_change"
                facts = facts_for_arm(entries[pid], FACTS_ONLY)
                (out / "llm/outputs_stress_facts_only.jsonl").write_text(json.dumps(
                    {"id": f"stress|{pid}", "text": json.dumps({"sentences": facts_only_claims(facts)}),
                     "finish_reason": "stop"}) + "\n")
                (out / "llm/outputs_stress_facts_only.jsonl.meta.json").write_text(json.dumps(
                    {"complete": True, "n_attempts": 1, "total_process_wall_s": 12.0,
                     "attempts": [{"attempt": 1, "process_wall_s": 12.0}]}))
                pipeline.evaluate_stress_step(root, out)
            facts = pd.read_csv(out / "stress_facts_only.csv").set_index("perturbed_id")
            self.assertEqual(facts.loc[pid, "status"], "follows")
            self.assertTrue(bool(facts.loc[pid, "check_pass"]))
            self.assertEqual(facts.loc["mu|grade4|S2|perturbed:enhancing_volume_change", "status"], "failed")
            summary = pd.read_csv(out / "summary_stress_facts_only.csv").set_index("kind")
            self.assertEqual(int(summary.loc["total", "n"]), 2)
            self.assertEqual(int(summary.loc["total", "failed_output"]), 1)
            self.assertTrue(bool(summary.loc["total", "batch_complete"]))
            self.assertEqual(int(summary.loc["total", "n_attempts"]), 1)
            full = pd.read_csv(out / "summary_stress_full_evidence.csv").set_index("kind")
            self.assertEqual((int(full.loc["total", "n"]), int(full.loc["total", "follows"])), (30, 28))
            self.assertEqual(set(full.rule), {pipeline.V31_RULE})
            self.assertEqual(len(pd.read_csv(out / "stress_full_evidence.csv")), 30)
            self.assertEqual(set(pd.read_csv(out / "stress_full_evidence.csv").kind), set(pipeline.eligible_kinds(FULL_EVIDENCE)))


class TestRenderedReports(unittest.TestCase):
    MODEL_ONLY_HEADINGS = ("## 2. The two pathways", "## 3. The combined score", "## 4. How much to trust this here")

    def test_facts_only_markdown_has_no_model_only_headings_or_tables(self):
        rec = record()
        facts = facts_for_arm(rec, FACTS_ONLY)
        output = {"text": json.dumps({"sentences": facts_only_claims(facts)})}
        for passed in (True, False):
            with self.subTest(passed=passed):
                report = pipeline.render_report(FACTS_ONLY, rec, output, passed)
                headings = [line for line in report.splitlines() if line.startswith("#")]
                self.assertEqual(headings, ["# Scan facts: S", "## Scan", "## Measurements", "## Longitudinal",
                                            "## Provenance", "## Limitations"])
                for heading in self.MODEL_ONLY_HEADINGS:
                    self.assertNotIn(heading, report)
                for word in ("Pathway", "Score", "Conformal", "Tier", "Flag", "Agreement", "80% set", "Card"):
                    self.assertNotIn(word.lower(), report.lower())
                self.assertEqual(passed, "Enhancing tumour volume is 37.2 cc" in report)

    def test_full_arm_markdown_is_byte_identical_to_v31_renderer_on_frozen_fixture(self):
        from prism.analyses import report_v3_1 as R31
        rec = record()
        rec["record_id"] = "mu|grade4|S"
        text = json.dumps({"sentences": [{"section": "scan", "text": "Fixture scan sentence.", "fields": []},
                                         {"section": "trust", "text": "Fixture trust sentence.", "fields": []}]})
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            (out / "records").mkdir()
            (out / "llm").mkdir()
            (out / "records/eval.jsonl").write_text(json.dumps(rec) + "\n")
            (out / "llm/outputs_eval.jsonl").write_text(json.dumps({"id": "eval|mu|grade4|S", "text": text}) + "\n")
            with patch.object(R31, "OUT", out):
                R31.render_set("eval")
            canonical = (out / "reports/eval/mu__grade4__S.md").read_bytes()
        self.assertEqual(pipeline.render_report(FULL_EVIDENCE, rec, {"text": text}, True).encode(), canonical)
        self.assertEqual(pipeline.render_report(FULL_EVIDENCE, rec, {"text": text}, False).encode(), canonical)
        self.assertIn("## 2. The two pathways", canonical.decode())

    @unittest.skipUnless((Path(__file__).resolve().parents[1] /
                          "outputs/results/analyses/report_v3_1/reports/eval").exists(), "v3.1 reports absent")
    def test_full_arm_markdown_matches_frozen_v31_reports(self):
        base = Path(__file__).resolve().parents[1] / "outputs/results/analyses/report_v3_1"
        examples = set(json.loads((base / "examples.json").read_text()))  # rendered with a figure link
        outputs = {r["id"]: r for r in map(json.loads, (base / "llm/outputs_eval.jsonl").read_text().splitlines())}
        checked = 0
        for line in (base / "records/eval.jsonl").read_text().splitlines():
            rec = json.loads(line)
            rid = rec["record_id"]
            if rid in examples:
                continue
            frozen = (base / "reports/eval" / f"{rid.replace('|', '__')}.md").read_bytes()
            self.assertEqual(pipeline.render_report(FULL_EVIDENCE, rec, outputs.get(f"eval|{rid}"), True).encode(),
                             frozen, rid)
            checked += 1
        self.assertEqual(checked, 403)


if __name__ == "__main__":
    unittest.main()
