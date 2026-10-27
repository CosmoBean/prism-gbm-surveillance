"""Facts-only v2: one specification renders the prompt and the checker. Synthetic records only."""

import contextlib
import copy
import io
import json
import shutil
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from prism.report import facts_only_v2
from prism.report.facts_v3 import PHASE_TEXT
from prism.report.field_ablation import FACTS_ONLY, FULL_EVIDENCE, _BANNED, facts_for_arm
from tests.test_report_v3 import good_claims, record
from tests.test_report_v3_1 import lumiere
from tests.test_report_field_ablation import SUBJECT_ID, _copy_gated_root, facts_only_claims, zero_change_record
from prism.analyses import report_field_ablation as V1
from prism.analyses import report_field_ablation_v2 as V2

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



# ---------------------------------------------------------------- v2 runner (Task 2), synthetic records only
REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = "prism/report/facts_only_v2.py"
RUNNER = "prism/analyses/report_field_ablation_v2.py"


def synthetic_dev() -> list[dict]:
    """58 synthetic development records: MU 32 (20 patients), LUMIERE 16 (10), UCSF 10 (10)."""
    rows = []
    for cohort, n, n_patients in (("mu", 32, 20), ("lumiere", 16, 10), ("ucsf", 10, 10)):
        for i in range(n):
            rec = lumiere(rater=bool(i % 2), measured=i % 4 != 3) if cohort == "lumiere" else record()
            rec["cohort"] = cohort
            rec.update(record_id=f"{cohort}|synthetic|dev{i:02d}", scan_id=f"synthetic-{cohort}-dev{i:02d}",
                       patient_id=f"synthetic-{cohort}-p{i % n_patients:02d}")
            rows.append(rec)
    return rows


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))


def reference_text(rec: dict) -> str:
    return json.dumps({"sentences": facts_only_v2.reference_report(_facts(rec))})


def fake_batch(records: list[dict], bad=(), missing=(), calls=None):
    """Stands in for V1._whole_batch: writes a complete synthetic output and its metadata (no model)."""
    by_id = {r["record_id"]: r for r in records}

    def run(root, request, target, guard):
        guard()
        if calls is not None:
            calls.append(request)
        rows = []
        for req in V1._jsonl(request):
            rid = req["id"].split("|", 1)[1]
            if rid in missing:
                continue
            text = ('{"sentences":[{"section":"scan","text":"The model score is high.","fields":["scan.phase"]}]}'
                    if rid in bad else reference_text(by_id[rid]) if rid in by_id else "not json")
            rows.append({"id": req["id"], "text": text, "finish_reason": "stop", "n_prompt_tokens": 10,
                         "n_output_tokens": 5})
        _write_jsonl(target, rows)
        meta = {"request_sha256": V1._digest(request), "complete": True, "n_attempts": 1,
                "attempts": [{"attempt": 1, "complete": True, "process_wall_s": 1.0, "batch_wall_s": 0.5}],
                "total_process_wall_s": 1.0, "total_batch_wall_s": 0.5, "batch_wall_s": 0.5}
        Path(str(target) + ".meta.json").write_text(json.dumps(meta) + "\n")
        return meta
    return run


class V2Root:
    """A temporary gated root (v1 gate inputs copied, v1 lock frozen there) with a synthetic development set."""

    def __init__(self, dev=None):
        self._dir = tempfile.TemporaryDirectory()
        self.root = Path(self._dir.name)
        _copy_gated_root(REPO_ROOT, self.root)
        for relative in (SPEC, RUNNER):
            (self.root / relative).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(REPO_ROOT / relative, self.root / relative)
        self.v1 = self.root / "v1"
        V1.freeze_step(self.root, self.v1)
        _write_jsonl(self.v1 / V1.STRESS_RECORDS, [{"record_id": "synthetic|stress|0"}])
        (self.v1 / V1.STRESS_LOG).write_text("record_id,perturbed_id\nsynthetic|stress,synthetic|stress|0\n")
        self.out = self.root / "v2"
        self.dev = synthetic_dev() if dev is None else dev
        _write_jsonl(self.root / V1.BASE / "records/dev.jsonl", self.dev)
        self.pass_preflight()

    def pass_preflight(self, complete=True, parsed=True):
        self.out.mkdir(parents=True, exist_ok=True)
        (self.out / "preflight.json").write_text(json.dumps({"complete": complete, "parsed": parsed,
                                                             "request_sha256": "0" * 64}))

    def dev_step(self, iteration, batch=None):
        with patch("prism.analyses.report_field_ablation._whole_batch", batch or fake_batch(self.dev)), \
                contextlib.redirect_stdout(io.StringIO()):
            return V2.dev_step(self.root, self.out, iteration, v1_output_root=self.v1)

    def preflight(self, batch=None):
        with patch("prism.analyses.report_field_ablation._whole_batch", batch or fake_batch([])), \
                contextlib.redirect_stdout(io.StringIO()):
            return V2.preflight_step(self.root, self.out, v1_output_root=self.v1)

    def freeze(self):
        with contextlib.redirect_stdout(io.StringIO()):
            return V2.freeze_step(self.root, self.out, v1_output_root=self.v1)

    def eval_requests(self):
        with patch("prism.analyses.report_field_ablation._whole_batch", _no_model), \
                contextlib.redirect_stdout(io.StringIO()):
            return V2.requests_step(self.root, self.out, "eval", v1_output_root=self.v1)

    def cleanup(self):
        self._dir.cleanup()


def failed_batch(calls=None):
    """Stands in for V1._whole_batch when both whole-batch attempts fail: attempt files, an empty final output and
    complete false, as V1._whole_batch writes them (no exception)."""
    def run(root, request, target, guard):
        guard()
        if calls is not None:
            calls.append(request)
        attempts = []
        for attempt in (1, 2):
            attempt_path = target.with_name(f"{target.stem}_attempt{attempt}{target.suffix}")
            attempt_path.with_suffix(".log").write_text("engine failed\n")
            Path(str(attempt_path) + ".meta.json").write_text(json.dumps({"attempt": attempt, "complete": False}))
            attempts.append({"attempt": attempt, "returncode": 1, "complete": False, "process_wall_s": 2.0,
                             "batch_wall_s": None})
        meta = {"request_sha256": V1._digest(request), "complete": False, "attempts": attempts, "n_attempts": 2,
                "total_process_wall_s": 4.0, "total_batch_wall_s": 0}
        target.write_text("")
        Path(str(target) + ".meta.json").write_text(json.dumps(meta) + "\n")
        return meta
    return run


def _no_model(*_args, **_kwargs):
    raise AssertionError("model runner must not start")


def summary_frame(mu, lumiere_, ucsf):
    rows = [("all", 58, mu + lumiere_ + ucsf), ("lumiere", 16, lumiere_), ("mu", 32, mu), ("ucsf", 10, ucsf)]
    return pd.DataFrame([{"cohort": c, "n": n, "pass": p} for c, n, p in rows])


class TestV2Constants(unittest.TestCase):
    def test_protocol_values(self):
        self.assertEqual(V2.MAX_ITERATIONS, 3)
        self.assertEqual(V2.DEV_CRITERION, {"all": 55, "mu": 29, "lumiere": 15, "ucsf": 9})
        self.assertEqual(V2.OUT2.parts[-2:], ("analyses", "report_field_ablation_v2"))


class TestQualifies(unittest.TestCase):
    def test_qualifies_thresholds(self):
        self.assertTrue(V2.qualifies(summary_frame(31, 15, 9)))   # 55/58; LUMIERE and UCSF at their minimum
        self.assertTrue(V2.qualifies(summary_frame(29, 16, 10)))  # 55/58; MU at its minimum
        self.assertFalse(V2.qualifies(summary_frame(29, 15, 10)))  # 54/58
        self.assertFalse(V2.qualifies(summary_frame(32, 15, 8)))   # 55/58 but UCSF 8/10
        self.assertFalse(V2.qualifies(summary_frame(32, 14, 9)))   # 55/58 but LUMIERE 14/16

    def test_qualifies_refuses_an_incomplete_summary(self):
        self.assertFalse(V2.qualifies(summary_frame(31, 15, 9).query("cohort != 'ucsf'")))
        wrong_n = summary_frame(31, 15, 9)
        wrong_n.loc[wrong_n.cohort == "all", "n"] = 57
        self.assertFalse(V2.qualifies(wrong_n))


class TestDevStep(unittest.TestCase):
    def setUp(self):
        self.env = V2Root()
        self.addCleanup(self.env.cleanup)

    def test_dev_writes_iteration_outputs(self):
        bad = {self.env.dev[0]["record_id"], self.env.dev[40]["record_id"]}
        result = self.env.dev_step(0, fake_batch(self.env.dev, bad=bad))
        out = self.env.out
        for name in ("llm/requests_dev_iter0.jsonl", "llm/outputs_dev_iter0.jsonl", "checks_dev_iter0.csv",
                     "summary_dev_iter0.csv", "non_form_word_counts_dev_iter0.csv", "dev_iter0.json",
                     "dev_lock.json"):
            self.assertTrue((out / name).exists(), name)
        requests = V1._jsonl(out / "llm/requests_dev_iter0.jsonl")
        self.assertEqual([r["id"] for r in requests], [f"dev|{r['record_id']}" for r in self.env.dev])
        self.assertEqual(requests[0]["messages"], facts_only_v2.messages(_facts(self.env.dev[0])))
        self.assertEqual(requests[0]["schema"], facts_only_v2.FACTS_SCHEMA)
        info = json.loads((out / "dev_iter0.json").read_text())
        self.assertEqual(info["spec_version"], facts_only_v2.SPEC_VERSION)
        self.assertEqual(info["spec_blob"], V1._git_blob(self.env.root / SPEC))
        self.assertTrue(info["qualifies"])
        self.assertEqual(result["qualifies"], True)
        summary = pd.read_csv(out / "summary_dev_iter0.csv").set_index("cohort")
        self.assertEqual(int(summary.loc["all", "pass"]), 56)
        self.assertEqual(int(summary.loc["mu", "pass"]), 31)
        self.assertEqual(int(summary.loc["lumiere", "pass"]), 15)
        self.assertEqual(int(summary.loc["all", "fail_banned_term"]), 2)
        words = pd.read_csv(out / "non_form_word_counts_dev_iter0.csv").set_index("word")
        self.assertEqual(int(words.loc["model", "n_reports"]), 2)

    def test_dev_summary_has_one_column_per_criterion(self):
        missing = {self.env.dev[5]["record_id"]}
        self.env.dev_step(0, fake_batch(self.env.dev, missing=missing))
        summary = pd.read_csv(self.env.out / "summary_dev_iter0.csv")
        self.assertEqual(sorted(summary.cohort), ["all", "lumiere", "mu", "ucsf"])
        self.assertEqual([c for c in summary.columns if c.startswith("fail_")], list(facts_only_v2.CRITERIA))
        for column in ("n", "pass", *facts_only_v2.CRITERIA):
            self.assertEqual(Counter(summary.columns)[column], 1, column)
        row = summary.set_index("cohort").loc["all"]
        self.assertEqual((int(row["n"]), int(row["pass"]), int(row["fail_unparsed"])), (58, 57, 1))
        self.assertEqual(int(row["missing_output"]), 1)
        checks = pd.read_csv(self.env.out / "checks_dev_iter0.csv")
        self.assertEqual(len(checks), 58)
        self.assertEqual([c for c in checks.columns if c.startswith("fail_")], list(facts_only_v2.CRITERIA))

    def test_dev_summaries_hold_no_text(self):
        bad = {self.env.dev[0]["record_id"]}
        self.env.dev_step(0, fake_batch(self.env.dev, bad=bad))
        for name in ("summary_dev_iter0.csv", "non_form_word_counts_dev_iter0.csv", "dev_iter0.json",
                     "dev_lock.json"):
            text = (self.env.out / name).read_text()
            with self.subTest(name=name):
                self.assertNotIn("synthetic|", text)
                self.assertNotIn("synthetic-", text)
                self.assertNotIn("The model score", text)
        checks = (self.env.out / "checks_dev_iter0.csv").read_text()
        self.assertNotIn("The model score", checks)
        self.assertNotIn("model", checks)

    def test_dev_refuses_fourth_iteration(self):
        with self.assertRaisesRegex(RuntimeError, "at most 3 development iterations"):
            self.env.dev_step(3, _no_model)
        with self.assertRaisesRegex(RuntimeError, "iteration"):
            self.env.dev_step(-1, _no_model)
        self.assertFalse((self.env.out / "llm/requests_dev_iter3.jsonl").exists())

    def test_dev_refuses_without_previous_summary(self):
        with self.assertRaisesRegex(RuntimeError, "iteration 0 has no summary"):
            self.env.dev_step(1, _no_model)

    def test_dev_refuses_after_a_qualifying_iteration(self):
        self.env.dev_step(0)
        self.assertTrue(json.loads((self.env.out / "dev_iter0.json").read_text())["qualifies"])
        with self.assertRaisesRegex(RuntimeError, "iteration 0 already qualified"):
            self.env.dev_step(1, _no_model)

    def test_dev_continues_after_a_nonqualifying_iteration(self):
        bad = {r["record_id"] for r in self.env.dev[:4]}
        self.assertFalse(self.env.dev_step(0, fake_batch(self.env.dev, bad=bad))["qualifies"])
        self.assertTrue(self.env.dev_step(1)["qualifies"])
        self.assertTrue((self.env.out / "summary_dev_iter1.csv").exists())

    def test_dev_refuses_rerun_of_existing_iteration(self):
        bad = {r["record_id"] for r in self.env.dev[:4]}
        self.env.dev_step(0, fake_batch(self.env.dev, bad=bad))
        with self.assertRaisesRegex(RuntimeError, "iteration 0 output already exists.*logged deviation"):
            self.env.dev_step(0, _no_model)
        # A partial iteration (requests only) is refused too.
        (self.env.out / "llm/requests_dev_iter1.jsonl").write_text("")
        with self.assertRaisesRegex(RuntimeError, "iteration 1 output already exists"):
            self.env.dev_step(1, _no_model)

    def test_failed_batch_does_not_use_up_the_iteration(self):
        with self.assertRaisesRegex(RuntimeError, "iteration 0 batch failed.*moved to deviation_dev_iter0_1/.*"
                                                  "logged deviation is required"):
            self.env.dev_step(0, failed_batch())
        out = self.env.out
        for name in ("summary_dev_iter0.csv", "non_form_word_counts_dev_iter0.csv", "dev_iter0.json",
                     "checks_dev_iter0.csv"):
            self.assertFalse((out / name).exists(), name)
        self.assertEqual(list((out / "llm").iterdir()), [])
        moved = out / "deviation_dev_iter0_1"
        self.assertEqual(sorted(p.name for p in moved.iterdir()), sorted([
            "infra_failure.json", "requests_dev_iter0.jsonl", "outputs_dev_iter0.jsonl",
            "outputs_dev_iter0.jsonl.meta.json", "outputs_dev_iter0_attempt1.log",
            "outputs_dev_iter0_attempt1.jsonl.meta.json", "outputs_dev_iter0_attempt2.log",
            "outputs_dev_iter0_attempt2.jsonl.meta.json"]))
        failure = json.loads((moved / "infra_failure.json").read_text())
        self.assertEqual((failure["iteration"], failure["complete"], failure["n_attempts"]), (0, False, 2))
        self.assertNotIn("synthetic", (moved / "infra_failure.json").read_text())
        # A second failure goes to the next free directory; then the iteration runs normally.
        with self.assertRaisesRegex(RuntimeError, "deviation_dev_iter0_2/"):
            self.env.dev_step(0, failed_batch())
        info = self.env.dev_step(0)
        self.assertTrue(info["qualifies"])
        self.assertTrue((out / "summary_dev_iter0.csv").exists())
        self.assertTrue((out / "dev_iter0.json").exists())

    def test_dev_refuses_without_a_passing_preflight(self):
        (self.env.out / "preflight.json").unlink()
        with self.assertRaisesRegex(RuntimeError, "passing preflight"):
            self.env.dev_step(0, _no_model)
        for complete, parsed in ((True, False), (False, True)):
            self.env.pass_preflight(complete=complete, parsed=parsed)
            with self.subTest(complete=complete, parsed=parsed):
                with self.assertRaisesRegex(RuntimeError, "passing preflight"):
                    self.env.dev_step(0, _no_model)
        self.assertFalse((self.env.out / "llm/requests_dev_iter0.jsonl").exists())

    def test_spec_change_during_generation_is_refused(self):
        spec = self.env.root / SPEC
        good = fake_batch(self.env.dev)

        def change_spec_then_run(root, request, target, guard):
            spec.write_bytes(spec.read_bytes() + b"\n# changed during generation\n")
            return good(root, request, target, guard)
        before = V1._git_blob(spec)
        with self.assertRaisesRegex(RuntimeError, "specification changed during development iteration 0"):
            self.env.dev_step(0, change_spec_then_run)
        self.assertFalse((self.env.out / "dev_iter0.json").exists())
        spec.write_bytes((REPO_ROOT / SPEC).read_bytes())
        self.assertEqual(V1._git_blob(spec), before)

    def test_dev_refuses_when_consistency_check_fails(self):
        original = facts_only_v2.sentence_forms

        def drop_label(key, facts):
            return [] if key == "meas.label" else original(key, facts)
        with patch("prism.report.facts_only_v2.sentence_forms", drop_label):
            with self.assertRaisesRegex(RuntimeError, "consistency check failed") as caught:
                self.env.dev_step(0, _no_model)
        message = str(caught.exception)
        self.assertIn("meas.label", message)
        self.assertNotIn("synthetic", message)
        self.assertNotIn("37.2", message)
        self.assertFalse((self.env.out / "llm/requests_dev_iter0.jsonl").exists())


class TestGuardV2(unittest.TestCase):
    def test_dev_refuses_patient_overlap_with_eval(self):
        env = V2Root()
        self.addCleanup(env.cleanup)
        # Copy one evaluation (cohort, patient) pair from the temporary gated copy into a synthetic record.
        # Every record of one synthetic MU patient takes that patient's ID, so the dev counts are unchanged.
        first = next(r for r in V1._jsonl(env.root / V1.BASE / "records/eval.jsonl") if r["cohort"] == "mu")
        moved = env.dev[0]["patient_id"]
        for rec in env.dev:
            if rec["cohort"] == "mu" and rec["patient_id"] == moved:
                rec["patient_id"] = first["patient_id"]
        _write_jsonl(env.root / V1.BASE / "records/dev.jsonl", env.dev)
        with self.assertRaisesRegex(RuntimeError, "development/evaluation patient overlap: 1 patient") as caught:
            env.dev_step(0, _no_model)
        self.assertTrue(first["patient_id"] not in str(caught.exception), "evaluation patient ID leaked")
        with self.assertRaisesRegex(RuntimeError, "patient overlap"):
            env.preflight(_no_model)
        self.assertFalse((env.out / "dev_lock.json").exists())

    def test_guard_records_and_enforces_the_dev_lock(self):
        env = V2Root()
        self.addCleanup(env.cleanup)
        V2.guard_v2(env.root, env.out, v1_output_root=env.v1)
        lock = json.loads((env.out / "dev_lock.json").read_text())
        self.assertEqual(lock["dev_sha256"], V1._digest(env.root / V1.BASE / "records/dev.jsonl"))
        self.assertEqual(lock["v1_provenance_sha256"], V1._digest(env.v1 / "provenance.json"))
        dev = env.root / V1.BASE / "records/dev.jsonl"
        dev.write_bytes(dev.read_bytes().replace(b'"scan_id": ', b'"scan_id" : ', 1))
        with self.assertRaisesRegex(RuntimeError, "development set hash mismatch"):
            env.dev_step(0, _no_model)

    def test_guard_refuses_a_changed_v1_lock(self):
        env = V2Root()
        self.addCleanup(env.cleanup)
        V2.guard_v2(env.root, env.out, v1_output_root=env.v1)
        lock = env.v1 / "provenance.json"
        lock.write_text(lock.read_text() + "\n")
        with self.assertRaisesRegex(RuntimeError, "v1 provenance hash mismatch"):
            env.dev_step(0, _no_model)

    def test_guard_refuses_wrong_dev_counts(self):
        env = V2Root(dev=synthetic_dev()[:-1])
        self.addCleanup(env.cleanup)
        with self.assertRaisesRegex(RuntimeError, "development set count mismatch"):
            env.dev_step(0, _no_model)

    def test_v1_gate_blocks_every_v2_step(self):
        env = V2Root()
        self.addCleanup(env.cleanup)
        checker = env.root / "prism/report/checker.py"
        checker.write_bytes(checker.read_bytes() + b"\n# changed after freeze\n")
        for name, step in (("dev", lambda: env.dev_step(0, _no_model)), ("preflight", lambda: env.preflight(_no_model)),
                           ("guard", lambda: V2.guard_v2(env.root, env.out, v1_output_root=env.v1))):
            with self.subTest(step=name):
                with self.assertRaisesRegex(RuntimeError, "checker.*hash"):
                    step()

    def test_v1_lock_is_required(self):
        env = V2Root()
        self.addCleanup(env.cleanup)
        shutil.rmtree(env.v1)
        with self.assertRaisesRegex(RuntimeError, "run freeze"):
            env.dev_step(0, _no_model)


class TestPreflight(unittest.TestCase):
    def setUp(self):
        self.env = V2Root()
        self.addCleanup(self.env.cleanup)

    def test_preflight_uses_no_patient_record(self):
        calls = []
        result = self.env.preflight(fake_batch([V2.synthetic_record()], calls=calls))
        self.assertEqual(len(calls), 1)
        request = calls[0]
        self.assertEqual(request.parent.parent, self.env.out / "preflight")
        text = request.read_text()
        self.assertEqual(len(V1._jsonl(request)), 1)
        self.assertIsNone(SUBJECT_ID.search(text))
        ids = set()
        for name in ("eval.jsonl", "dev.jsonl"):
            for rec in V1._jsonl(self.env.root / V1.BASE / "records" / name):
                ids |= {rec["record_id"], rec["scan_id"], rec["patient_id"]}
        self.assertFalse(any(i in text for i in ids), "record ID in preflight request")
        self.assertEqual(V1._jsonl(request)[0]["messages"], facts_only_v2.messages(_facts(V2.synthetic_record())))
        state = json.loads((self.env.out / "preflight.json").read_text())
        self.assertEqual({k: state[k] for k in ("complete", "parsed", "request_sha256")},
                         {"complete": True, "parsed": True, "request_sha256": V1._digest(request)})
        self.assertEqual(result["parsed"], True)
        # Nothing is written where the evaluation batch, its requests or its attempts go.
        self.assertFalse((self.env.out / "llm").exists())
        self.assertFalse((self.env.out / "request_hashes.json").exists())

    def test_preflight_can_be_repeated_and_logs_each_run(self):
        failed = fake_batch([])  # output does not parse
        self.assertFalse(self.env.preflight(failed)["parsed"])
        self.assertTrue(self.env.preflight(fake_batch([V2.synthetic_record()]))["parsed"])
        log = V1._jsonl(self.env.out / "preflight" / "preflight_log.jsonl")
        self.assertEqual([(r["run"], r["parsed"]) for r in log], [(1, False), (2, True)])
        self.assertTrue(json.loads((self.env.out / "preflight.json").read_text())["parsed"])

    def test_synthetic_record_is_not_a_patient_record(self):
        rec = V2.synthetic_record()
        self.assertTrue(rec["record_id"].startswith("synthetic|"))
        self.assertIsNone(SUBJECT_ID.search(json.dumps(rec)))
        self.assertEqual(facts_only_v2.consistency_errors(_facts(rec)), [])


# ---------------------------------------------------------------- freeze, evaluation, analyses (Task 3)
def _qualify(env):
    info = env.dev_step(0)
    assert info["qualifies"]
    return info


class TestFreeze(unittest.TestCase):
    def setUp(self):
        self.env = V2Root()
        self.addCleanup(self.env.cleanup)

    def test_freeze_refuses_nonqualifying_iteration(self):
        with self.assertRaisesRegex(RuntimeError, "no qualifying development iteration"):
            self.env.freeze()
        bad = {r["record_id"] for r in self.env.dev[:4]}
        self.assertFalse(self.env.dev_step(0, fake_batch(self.env.dev, bad=bad))["qualifies"])
        with self.assertRaisesRegex(RuntimeError, "no qualifying development iteration"):
            self.env.freeze()
        self.assertFalse((self.env.out / "FROZEN_v2.json").exists())

    def test_freeze_records_the_protocol_values(self):
        _qualify(self.env)
        frozen = self.env.freeze()
        root, base = self.env.root, self.env.root / V1.BASE
        self.assertEqual(json.loads((self.env.out / "FROZEN_v2.json").read_text()), frozen)
        self.assertEqual(frozen["spec_blob"], V1._git_blob(root / SPEC))
        self.assertEqual(frozen["spec_sha256"], V1._digest(root / SPEC))
        self.assertEqual(frozen["runner_blob"], V1._git_blob(root / RUNNER))
        self.assertEqual(frozen["runner_sha256"], V1._digest(root / RUNNER))
        self.assertEqual(frozen["writer"], V1.EXPECTED_WRITER)
        self.assertEqual(frozen["prefixes"], ["pathway.", "pathways.", "conformal.", "card.", "flags."])
        self.assertEqual(frozen["v1_manifest_sha256"], V1._digest(root / V1.MANIFEST))
        self.assertEqual(frozen["eval_sha256"], V1._digest(base / "records/eval.jsonl"))
        self.assertEqual(frozen["dev_sha256"], V1._digest(base / "records/dev.jsonl"))
        self.assertEqual(len(frozen["eval_line_sha256"]), 406)
        self.assertEqual(len(frozen["dev_line_sha256"]), 58)
        self.assertEqual(frozen["stress_sha256"], V1._digest(self.env.v1 / V1.STRESS_RECORDS))
        self.assertEqual(frozen["qualifying_iteration"], 0)
        self.assertEqual(frozen["spec_version"], facts_only_v2.SPEC_VERSION)
        text = (self.env.out / "FROZEN_v2.json").read_text()
        self.assertTrue("synthetic" not in text and SUBJECT_ID.search(text) is None, "record ID in FROZEN_v2.json")
        self.assertEqual(self.env.freeze(), frozen)  # identical re-run is a no-op

    def test_freeze_refuses_to_overwrite_a_different_freeze(self):
        _qualify(self.env)
        self.env.freeze()
        path = self.env.out / "FROZEN_v2.json"
        frozen = json.loads(path.read_text())
        frozen["qualifying_iteration"] = 1
        path.write_text(json.dumps(frozen))
        with self.assertRaisesRegex(RuntimeError, "FROZEN_v2.json exists and differs"):
            self.env.freeze()
        self.assertEqual(json.loads(path.read_text())["qualifying_iteration"], 1)

    def test_freeze_refuses_when_spec_changed_since_the_qualifying_iteration(self):
        _qualify(self.env)
        spec = self.env.root / SPEC
        spec.write_bytes(spec.read_bytes() + b"\n# changed after the iteration\n")
        with self.assertRaisesRegex(RuntimeError, "specification changed since development iteration 0"):
            self.env.freeze()
        self.assertFalse((self.env.out / "FROZEN_v2.json").exists())


class TestEvalRequestGuards(unittest.TestCase):
    def setUp(self):
        self.env = V2Root()
        self.addCleanup(self.env.cleanup)
        _qualify(self.env)

    def _no_eval_requests(self):
        self.assertFalse((self.env.out / "llm/requests_facts_only_v2.jsonl").exists())
        self.assertFalse((self.env.out / "request_hashes.json").exists())

    def test_eval_requests_refuse_without_freeze(self):
        with self.assertRaisesRegex(RuntimeError, "run freeze"):
            self.env.eval_requests()
        self._no_eval_requests()

    def test_eval_requests_refuse_when_spec_changed_after_freeze(self):
        self.env.freeze()
        real = V1._git_blob

        def changed(path):
            return "0" * 40 if Path(path).name == "facts_only_v2.py" else real(path)
        with patch.object(V1, "_git_blob", changed):
            with self.assertRaisesRegex(RuntimeError, "frozen spec_blob mismatch"):
                self.env.eval_requests()
        self._no_eval_requests()
        runner = self.env.root / RUNNER
        runner.write_bytes(runner.read_bytes() + b"\n# changed after freeze\n")
        with self.assertRaisesRegex(RuntimeError, "frozen runner_blob mismatch"):
            self.env.eval_requests()
        self._no_eval_requests()

    def test_eval_requests_refuse_when_stress_set_changed_after_freeze(self):
        self.env.freeze()
        _write_jsonl(self.env.v1 / V1.STRESS_RECORDS, [{"record_id": "synthetic|stress|1"}])
        with self.assertRaisesRegex(RuntimeError, "frozen stress_sha256 mismatch"):
            self.env.eval_requests()
        self._no_eval_requests()

    def test_eval_requests_refuse_without_successful_preflight(self):
        self.env.freeze()
        for complete, parsed in ((True, False), (False, True)):
            self.env.pass_preflight(complete=complete, parsed=parsed)
            with self.subTest(complete=complete, parsed=parsed):
                with self.assertRaisesRegex(RuntimeError, "passing preflight"):
                    self.env.eval_requests()
        (self.env.out / "preflight.json").unlink()
        with self.assertRaisesRegex(RuntimeError, "passing preflight"):
            self.env.eval_requests()
        self._no_eval_requests()


def synthetic_eval() -> list[dict]:
    """Four synthetic evaluation records (MU 2 from one patient, LUMIERE 1, UCSF 1)."""
    rows = []
    for i, (cohort, rec) in enumerate((("mu", record()), ("mu", record()), ("lumiere", lumiere(rater=True)),
                                       ("ucsf", record()))):
        rec["cohort"] = cohort
        rec.update(record_id=f"{cohort}|synthetic|e{i}", scan_id=f"synthetic-e{i}",
                   patient_id=f"synthetic-{cohort}-p{i // 2}")
        rows.append(rec)
    return rows


def full_text(rec: dict) -> str:
    return json.dumps({"sentences": good_claims(facts_for_arm(rec, FULL_EVIDENCE))})


class EvalEnv:
    """A temporary root with a synthetic v3.1 baseline (requests, outputs, metadata, checks) and a frozen v2 guard
    stood in by the synthetic manifest. No patient record is read."""

    def __init__(self, records=None, full_texts=None):
        self._dir = tempfile.TemporaryDirectory()
        self.root = Path(self._dir.name)
        self.records = synthetic_eval() if records is None else records
        self.manifest = {"records": [{"record_id": r["record_id"], "cohort": r["cohort"], "sha256": "0" * 64}
                                     for r in self.records]}
        base = self.root / V1.BASE
        texts = full_texts or {}
        _write_jsonl(base / "llm/requests_eval.jsonl",
                     [{"id": f"eval|{r['record_id']}", "messages": [{"role": "user", "content": "full arm"}]}
                      for r in self.records])
        _write_jsonl(base / "llm/outputs_eval.jsonl",
                     [{"id": f"eval|{r['record_id']}", "text": texts.get(r["record_id"], full_text(r)),
                       "finish_reason": "stop", "n_prompt_tokens": 20, "n_output_tokens": 9} for r in self.records])
        (base / "llm/outputs_eval.jsonl.meta.json").write_text(json.dumps({"model": "synthetic", "n": 4}) + "\n")
        pd.DataFrame([{"scan_id": r["record_id"], "cohort": r["cohort"], "pass": True, "parsed": True,
                       "fail_required_missing": False} for r in self.records]).to_csv(base / "checks_eval.csv",
                                                                                      index=False)
        self.out = self.root / "v2"
        self.out.mkdir()
        (self.out / "preflight.json").write_text(json.dumps({"complete": True, "parsed": True}))

    def _patched(self, batch=None):
        stack = contextlib.ExitStack()
        stack.enter_context(patch.object(V2, "guard_frozen", return_value=self.manifest))
        stack.enter_context(patch.object(V1, "_records",
                                         return_value={r["record_id"]: r for r in self.records}))
        stack.enter_context(patch.object(V1, "_whole_batch", batch or _no_model))
        stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
        return stack

    def run(self, missing=(), bad=(), steps=("requests", "generate", "evaluate")):
        with self._patched(fake_batch(self.records, bad=bad, missing=missing)):
            if "requests" in steps:
                V2.requests_step(self.root, self.out, "eval")
            if "generate" in steps:
                V2.generate_step(self.root, self.out, "eval")
            if "evaluate" in steps:
                V2.evaluate_step(self.root, self.out)

    def cleanup(self):
        self._dir.cleanup()


class TestEvalSteps(unittest.TestCase):
    def setUp(self):
        self.env = EvalEnv()
        self.addCleanup(self.env.cleanup)

    def test_requests_pair_the_frozen_full_arm_with_spec_prompts_in_manifest_order(self):
        self.env.run(steps=("requests",))
        llm = self.env.out / "llm"
        self.assertEqual((llm / "requests_full_evidence.jsonl").read_bytes(),
                         (self.env.root / V1.BASE / "llm/requests_eval.jsonl").read_bytes())
        facts = V1._jsonl(llm / "requests_facts_only_v2.jsonl")
        self.assertEqual([r["id"] for r in facts], [f"eval|{r['record_id']}" for r in self.env.records])
        self.assertEqual(facts[2]["messages"], facts_only_v2.messages(_facts(self.env.records[2])))
        self.assertEqual(facts[0]["schema"], facts_only_v2.FACTS_SCHEMA)
        self.assertEqual(facts[0]["max_tokens"], V2.MAX_TOKENS)
        hashes = json.loads((self.env.out / "request_hashes.json").read_text())
        self.assertEqual(hashes, {"full_evidence": V1._digest(llm / "requests_full_evidence.jsonl"),
                                  "facts_only_v2": V1._digest(llm / "requests_facts_only_v2.jsonl")})
        self.env.run(steps=("requests",))  # identical re-run is allowed
        (llm / "requests_facts_only_v2.jsonl").write_text("")
        with self.assertRaisesRegex(RuntimeError, "frozen facts-only v2 request mismatch"):
            self.env.run(steps=("requests",))

    def test_generation_imports_the_full_arm_byte_for_byte(self):
        calls = []
        with self.env._patched(fake_batch(self.env.records, calls=calls)):
            V2.requests_step(self.env.root, self.env.out, "eval")
            V2.generate_step(self.env.root, self.env.out, "eval")
        llm, base = self.env.out / "llm", self.env.root / V1.BASE / "llm"
        self.assertEqual((llm / "outputs_full_evidence.jsonl").read_bytes(), (base / "outputs_eval.jsonl").read_bytes())
        self.assertEqual((llm / "outputs_full_evidence.jsonl.meta.json").read_bytes(),
                         (base / "outputs_eval.jsonl.meta.json").read_bytes())
        self.assertEqual(calls, [llm / "requests_facts_only_v2.jsonl"])
        self.assertTrue((llm / "outputs_facts_only_v2.jsonl").exists())
        with self.env._patched(_no_model):  # an existing facts-only output is never regenerated
            self.assertIsNone(V2.generate_step(self.env.root, self.env.out, "eval"))

    def test_generation_refuses_changed_requests(self):
        self.env.run(steps=("requests",))
        path = self.env.out / "llm/requests_facts_only_v2.jsonl"
        path.write_bytes(path.read_bytes() + b"\n")
        with self.env._patched(_no_model), self.assertRaisesRegex(RuntimeError, "frozen request hash mismatch"):
            V2.generate_step(self.env.root, self.env.out, "eval")

    def test_missing_facts_only_output_is_a_failure_in_every_summary(self):
        gone = self.env.records[1]["record_id"]
        self.env.run(missing={gone})
        out = self.env.out
        checks = pd.read_csv(out / "checks_facts_only_v2.csv")
        self.assertEqual(len(checks), 4)
        self.assertEqual([c for c in checks.columns if c.startswith("fail_")], list(facts_only_v2.CRITERIA))
        row = checks.set_index("record_id").loc[gone]
        self.assertTrue(bool(row["fail_unparsed"]) and not bool(row["pass"]) and bool(row["missing_output"]))
        summary = pd.read_csv(out / "summary_facts_only_v2.csv").set_index("cohort")
        self.assertEqual((int(summary.loc["all", "n"]), int(summary.loc["all", "pass"]),
                          int(summary.loc["all", "fail_unparsed"])), (4, 3, 1))
        self.assertEqual((int(summary.loc["mu", "n"]), int(summary.loc["mu", "pass"])), (2, 1))
        for column in ("pass_ci_low", "pass_ci_high", "batch_complete", "n_attempts", "words_median"):
            self.assertIn(column, summary.columns)
        gate = json.loads((out / "gate.json").read_text())
        self.assertEqual(set(gate), {"overall_pass", "by_cohort", "met"})
        self.assertEqual(gate["overall_pass"], 3)
        self.assertEqual(gate["by_cohort"]["mu"]["pass"], 1)
        self.assertFalse(gate["met"])
        paired = pd.read_csv(out / "paired_summary.csv").set_index("cohort")
        self.assertEqual((int(paired.loc["all", "pass_full"]), int(paired.loc["all", "pass_facts_only"])), (4, 3))
        self.assertAlmostEqual(float(paired.loc["all", "pass_difference_full_minus_facts_only"]), 0.25)
        for column in ("pass_difference_ci_low", "pass_difference_ci_high"):
            self.assertIn(column, paired.columns)
        info = pd.read_csv(out / "information_added.csv").set_index("cohort")
        self.assertEqual(int(info.loc["all", "n_both_pass"]), 3)
        self.assertEqual(int(info.loc["mu", "n_both_pass"]), 1)
        common = pd.read_csv(out / "common_criteria.csv").set_index("cohort")
        self.assertEqual(int(common.loc["all", "facts_only_unparsed"]), 1)
        self.assertEqual(int(common.loc["all", "full_evidence_unparsed"]), 0)
        for criterion in ("unsupported_number", "invalid_citation", "forbidden", "clinical_inference"):
            self.assertEqual(int(common.loc["all", f"facts_only_fail_{criterion}"]), 1, criterion)
        reference = pd.read_csv(out / "reference_check.csv").set_index("cohort")
        self.assertEqual((int(reference.loc["all", "n"]), int(reference.loc["all", "pass"])), (4, 4))
        for name in ("summary_facts_only_v2.csv", "paired_summary.csv", "gate.json", "information_added.csv",
                     "common_criteria.csv", "reference_check.csv"):
            text = (out / name).read_text()
            self.assertTrue("synthetic" not in text, f"record ID in {name}")

    def test_failed_whole_batch_counts_every_record_as_a_failure(self):
        with self.env._patched(failed_batch()):
            V2.requests_step(self.env.root, self.env.out, "eval")
            V2.generate_step(self.env.root, self.env.out, "eval")
            V2.evaluate_step(self.env.root, self.env.out)
        summary = pd.read_csv(self.env.out / "summary_facts_only_v2.csv").set_index("cohort")
        self.assertEqual((int(summary.loc["all", "pass"]), int(summary.loc["all", "fail_unparsed"])), (0, 4))
        self.assertFalse(bool(summary.loc["all", "batch_complete"]))
        self.assertEqual(json.loads((self.env.out / "gate.json").read_text())["overall_pass"], 0)

    def test_full_arm_recheck_must_reproduce_the_v31_pass(self):
        rec = self.env.records[0]
        claims = good_claims(facts_for_arm(rec, FULL_EVIDENCE))
        claims[1]["text"] = claims[1]["text"].replace("37.2", "39.9")
        env = EvalEnv(full_texts={rec["record_id"]: json.dumps({"sentences": claims})})
        self.addCleanup(env.cleanup)
        with self.assertRaisesRegex(RuntimeError, "full-arm recheck does not reproduce the v3.1 pass on 1 record"):
            env.run()
        self.assertFalse((env.out / "summary_facts_only_v2.csv").exists())


def gate_summary(mu, lumiere_, ucsf):
    rows = [("all", 406, mu + lumiere_ + ucsf), ("lumiere", 162, lumiere_), ("mu", 114, mu), ("ucsf", 130, ucsf)]
    return pd.DataFrame([{"cohort": c, "n": n, "pass": p} for c, n, p in rows])


class TestAnalyses(unittest.TestCase):
    def test_gate_threshold(self):
        self.assertTrue(V2.gate(gate_summary(108, 156, 122))["met"])   # 386/406, each cohort >= 0.90
        self.assertEqual(V2.gate(gate_summary(108, 156, 122))["overall_pass"], 386)
        self.assertFalse(V2.gate(gate_summary(107, 156, 122))["met"])  # 385/406
        self.assertFalse(V2.gate(gate_summary(114, 160, 116))["met"])  # 390/406 but UCSF 116/130
        self.assertTrue(V2.gate(gate_summary(114, 160, 117))["met"])   # UCSF 117/130 = 0.90 exactly
        wrong_n = gate_summary(114, 160, 122)
        wrong_n.loc[wrong_n.cohort == "ucsf", "n"] = 129
        self.assertFalse(V2.gate(wrong_n)["met"])

    def _paired(self):
        return pd.DataFrame([
            {"scan_id": "a", "cohort": "mu", "patient_id": "p1", "full_evidence_pass": True, "facts_only_pass": True},
            {"scan_id": "b", "cohort": "mu", "patient_id": "p2", "full_evidence_pass": True, "facts_only_pass": True},
            {"scan_id": "c", "cohort": "ucsf", "patient_id": "p3", "full_evidence_pass": True,
             "facts_only_pass": False}])

    def test_information_added_counts_only_supported_model_keys_on_both_pass_records(self):
        def claim(fields, supported=True, invalid=()):
            return {"fields": list(fields), "supported": supported, "invalid_fields": list(invalid)}
        details = {
            "a": [claim(["scan.phase"]), claim(["card.tier", "card.tier_statement"]),
                  claim(["pathway.combined.statement"])],
            "b": [claim(["scan.phase"]), claim(["card.tier"], supported=False),
                  claim(["flags.out_of_range.reason"], supported=False, invalid=["flags.out_of_range.reason"])],
            "c": [claim(["card.tier"]), claim(["conformal.combined.80.statement"])]}
        facts_claims = {"a": [{"fields": ["scan.phase"]}, {"fields": ["meas.enhancing_cc"]}],
                        "b": [{"fields": ["scan.phase"]}], "c": None}
        info = V2.information_added(self._paired(), details, facts_claims).set_index("cohort")
        row = info.loc["all"]
        self.assertEqual(int(row["n_both_pass"]), 2)
        self.assertEqual(int(row["n_full_citing_model_key"]), 1)
        self.assertAlmostEqual(float(row["share_full_citing_model_key"]), 0.5)
        self.assertAlmostEqual(float(row["model_keys_median"]), 1.5)  # a: 3 keys, b: 0
        self.assertEqual(int(row["n_reports_card"]), 1)
        self.assertEqual(int(row["n_keys_card"]), 2)
        self.assertEqual(int(row["n_reports_pathway"]), 1)
        self.assertEqual(int(row["n_reports_flags"]), 0)
        self.assertEqual(int(row["n_reports_conformal"]), 0)  # only on c, where facts-only failed
        # Shared keys: a full {scan.phase} vs facts-only {scan.phase, meas.enhancing_cc}; b {scan.phase} both.
        self.assertAlmostEqual(float(row["shared_keys_difference_full_minus_facts_only"]), -0.5)
        self.assertEqual(int(row["n_full_shared_not_facts_only"]), 0)
        self.assertEqual(int(row["n_facts_only_shared_not_full"]), 1)
        for column in ("shared_keys_difference_ci_low", "shared_keys_difference_ci_high", "model_keys_q1",
                       "model_keys_q3"):
            self.assertIn(column, info.columns)
        self.assertEqual(int(info.loc["ucsf", "n_both_pass"]), 0)
        self.assertTrue(pd.isna(info.loc["ucsf", "share_full_citing_model_key"]))

    def test_common_criteria_applies_the_same_tests_to_both_arms(self):
        rec = synthetic_eval()[0]
        full = facts_for_arm(rec, FULL_EVIDENCE)
        good = good_claims(full)
        bad = good + [{"text": "The scan should be repeated at 99 cc.", "fields": ["pathway.combined.statement",
                                                                                   "nothing.here"]},
                      {"text": "The tumour has grown.", "fields": ["scan.phase"]}]
        frame = V2.common_criteria({"a": good, "b": bad}, {"a": facts_only_v2.reference_report(_facts(rec)),
                                                            "b": None}, {"a": full, "b": full})
        rows = frame.set_index(["record_id", "arm"])
        self.assertEqual(len(frame), 4)
        clean = rows.loc[("a", "full_evidence")]
        self.assertFalse(any(bool(clean[f"fail_{c}"]) for c in V2.COMMON_CRITERIA))
        self.assertFalse(any(bool(rows.loc[("a", "facts_only")][f"fail_{c}"]) for c in V2.COMMON_CRITERIA))
        dirty = rows.loc[("b", "full_evidence")]
        for criterion in V2.COMMON_CRITERIA:
            self.assertTrue(bool(dirty[f"fail_{criterion}"]), criterion)
        self.assertEqual(int(dirty["n_invalid_citations"]), 1)
        unparsed = rows.loc[("b", "facts_only")]
        self.assertTrue(bool(unparsed["unparsed"]))
        self.assertTrue(all(bool(unparsed[f"fail_{c}"]) for c in V2.COMMON_CRITERIA))


# ---------------------------------------------------------------- paired shared-fact stress test (Task 4)
STATEMENT = V1.STATEMENT_KEY


def synthetic_stress_sources() -> list[dict]:
    """Four synthetic source records eligible for the v1 enhancing-volume-change perturbation."""
    rows = []
    for i, cohort in enumerate(("mu", "mu", "lumiere", "ucsf")):
        rec = record()
        rec["cohort"] = cohort
        rec.update(record_id=f"synthetic|stress|s{i}", scan_id=f"synthetic-stress-s{i}",
                   patient_id=f"synthetic-{cohort}-sp{i // 2}")
        rows.append(rec)
    return rows


def _entry(rec=None):
    """A v1 stress entry for one synthetic record, with its old and new facts-only facts."""
    rec = rec or synthetic_stress_sources()[0]
    entry = V1._stress_candidate(rec)
    return entry, facts_for_arm(rec, FACTS_ONLY), facts_for_arm(entry["record"], FACTS_ONLY)


def stress_batch(entries: list[dict], calls=None, bad_full=(), missing=()):
    """Stands in for V1._whole_batch on the stress requests: the reference report for the facts-only arm and the
    synthetic passing full report for the full arm, on the perturbed records (no model)."""
    by_id = {e["perturbed_id"]: e["record"] for e in entries}

    def run(root, request, target, guard):
        guard()
        if calls is not None:
            calls.append(request)
        full = "full_evidence" in request.name
        rows = []
        for req in V1._jsonl(request):
            rid = req["id"].split("|", 1)[1]
            if rid in missing:
                continue
            rec = by_id[rid]
            text = ('{"sentences":[{"text":"No report.","fields":[]}]}' if full and rid in bad_full
                    else full_text(rec) if full else reference_text(rec))
            rows.append({"id": req["id"], "text": text, "finish_reason": "stop", "n_prompt_tokens": 10,
                         "n_output_tokens": 5})
        _write_jsonl(target, rows)
        meta = {"request_sha256": V1._digest(request), "complete": True, "n_attempts": 1,
                "attempts": [{"attempt": 1, "complete": True, "process_wall_s": 1.0, "batch_wall_s": 0.5}],
                "total_process_wall_s": 1.0, "total_batch_wall_s": 0.5, "batch_wall_s": 0.5}
        Path(str(target) + ".meta.json").write_text(json.dumps(meta) + "\n")
        return meta
    return run


class StressEnv:
    """A temporary root holding a v1-format stress set built from synthetic sources by the v1 stress step, and a
    v2 output root whose frozen guard is stood in. No patient record is read."""

    def __init__(self):
        self._dir = tempfile.TemporaryDirectory()
        self.root = Path(self._dir.name)
        self.sources = synthetic_stress_sources()
        self.v1 = self.root / "v1"
        self.v1.mkdir()
        with patch.object(V1, "_guard"), patch.object(V1, "_records", return_value=self.lookup()), \
                contextlib.redirect_stdout(io.StringIO()):
            V1.stress_step(self.root, self.v1)
        with patch.object(V1, "_records", return_value=self.lookup()):
            self.entries = V1._stress_entries(self.root, self.v1)
        self.out = self.root / "v2"
        self.out.mkdir()
        (self.out / "preflight.json").write_text(json.dumps({"complete": True, "parsed": True}))

    def lookup(self):
        return {r["record_id"]: r for r in self.sources}

    def patched(self, batch=None):
        stack = contextlib.ExitStack()
        stack.enter_context(patch.object(V2, "guard_frozen", return_value={"records": []}))
        stack.enter_context(patch.object(V1, "_records", return_value=self.lookup()))
        stack.enter_context(patch.object(V1, "_whole_batch", batch or _no_model))
        stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
        return stack

    def step(self, name, batch=None, **kwargs):
        with self.patched(batch):
            if name == "evaluate":
                return V2.evaluate_stress_step(self.root, self.out, v1_output_root=self.v1, **kwargs)
            return getattr(V2, f"{name}_step")(self.root, self.out, "stress", v1_output_root=self.v1, **kwargs)

    def run(self, **batch):
        self.step("requests")
        self.step("generate", stress_batch(self.entries, **batch))
        self.step("evaluate")

    def cleanup(self):
        self._dir.cleanup()


class TestSharedFollows(unittest.TestCase):
    def test_shared_follows_accepts_new_statement_inside_longer_full_sentence(self):
        entry, old, new = _entry()
        sentence = {"text": "Compared with the previous scan, the " + new[STATEMENT] + ", as measured.",
                    "fields": [STATEMENT]}
        result = V2.shared_follows(entry, old, new, [sentence])
        self.assertEqual((result["status"], result["follows"]), ("follows", True))
        self.assertTrue(result["new_supported"])
        # v1's strict rule needs sentence equality, so it does not accept the same sentence.
        self.assertEqual(V1.facts_only_follows(entry, old, new, [sentence])["status"], "not_follows")
        # The statement must be cited and present, with only a trailing full stop ignored.
        uncited = [{"text": sentence["text"], "fields": ["scan.phase"]}]
        self.assertEqual(V2.shared_follows(entry, old, new, uncited)["status"], "not_follows")
        upper = [{"text": new[STATEMENT].upper() + ".", "fields": [STATEMENT]}]
        self.assertEqual(V2.shared_follows(entry, old, new, upper)["status"], "follows")
        self.assertEqual(V2.shared_follows(entry, old, new, None)["status"], "failed")
        self.assertFalse(V2.shared_follows(entry, old, new, None)["follows"])

    def test_shared_follows_rejects_old_statement_present(self):
        entry, old, new = _entry()
        claims = [{"text": "The " + new[STATEMENT] + ".", "fields": [STATEMENT]},
                  {"text": "Earlier, the " + old[STATEMENT] + ".", "fields": [STATEMENT]}]
        result = V2.shared_follows(entry, old, new, claims)
        self.assertEqual((result["status"], result["follows"]), ("not_follows", False))
        self.assertTrue(result["old_present"])
        stale = [{"text": "The " + old[STATEMENT] + ".", "fields": [STATEMENT]}]
        result = V2.shared_follows(entry, old, new, stale)
        self.assertEqual(result["status"], "not_follows")
        self.assertFalse(result["new_supported"])
        number = [{"text": "The " + new[STATEMENT] + "; the earlier change was 3.5 cc.", "fields": [STATEMENT]}]
        result = V2.shared_follows(entry, old, new, number)
        self.assertEqual(result["status"], "not_follows")
        self.assertEqual(result["old_unique_hits"], ["3.5"])

    def test_shared_follows_marks_zero_value_ambiguity_unscorable(self):
        source = zero_change_record("synthetic|stress|z")
        entry, old, new = _entry(source)
        claims = facts_only_claims(new)  # "Resection cavity volume is 0.0 cc." is a correct sentence.
        result = V2.shared_follows(entry, old, new, claims)
        self.assertEqual((result["status"], result["follows"]), ("unscorable", None))
        self.assertTrue(result["old_ambiguous_hits"])
        self.assertEqual(result["old_unique_hits"], [])
        self.assertEqual(V2.shared_follows(entry, old, new, facts_only_claims(old))["status"], "not_follows")


class TestStress(unittest.TestCase):
    def setUp(self):
        self.env = StressEnv()
        self.addCleanup(self.env.cleanup)

    def test_stress_refuses_changed_v1_stress_set(self):
        env = V2Root()
        self.addCleanup(env.cleanup)
        _qualify(env)
        env.freeze()
        for relative, key in ((V1.STRESS_RECORDS, "stress_sha256"), (V1.STRESS_LOG, "stress_log_sha256")):
            path = env.v1 / relative
            original = path.read_bytes()
            path.write_bytes(original[:-2] + b"X" + original[-1:])
            with self.subTest(file=str(relative)):
                for step in (V2.requests_step, V2.generate_step):
                    with patch.object(V1, "_whole_batch", _no_model), \
                            self.assertRaisesRegex(RuntimeError, f"frozen {key} mismatch"):
                        step(env.root, env.out, "stress", v1_output_root=env.v1)
            path.write_bytes(original)
        self.assertEqual(list((env.out / "llm").glob("*stress*")), [])
        self.assertFalse((env.out / "request_hashes.json").exists())

    def test_stress_requests_render_both_arms_from_the_perturbed_records(self):
        from prism.report import prompts_v3_1
        self.env.step("requests")
        llm = self.env.out / "llm"
        facts = V1._jsonl(llm / "requests_stress_facts_only_v2.jsonl")
        full = V1._jsonl(llm / "requests_stress_full_evidence.jsonl")
        ids = [f"stress|{e['perturbed_id']}" for e in self.env.entries]
        self.assertEqual([r["id"] for r in facts], ids)
        self.assertEqual([r["id"] for r in full], ids)
        for entry, f_row, g_row in zip(self.env.entries, facts, full):
            self.assertEqual(f_row["messages"], facts_only_v2.messages(facts_for_arm(entry["record"], FACTS_ONLY)))
            self.assertEqual((f_row["max_tokens"], f_row["schema"]), (V2.MAX_TOKENS, facts_only_v2.FACTS_SCHEMA))
            self.assertEqual(g_row["messages"],
                             prompts_v3_1.grounded_v3_1(facts_for_arm(entry["record"], FULL_EVIDENCE)))
            self.assertEqual((g_row["max_tokens"], g_row["schema"]), (2048, prompts_v3_1.SCHEMA))
            self.assertEqual(list(g_row), ["id", "messages", "max_tokens", "schema"])
        hashes = json.loads((self.env.out / "request_hashes.json").read_text())
        self.assertEqual(hashes, {"stress_full_evidence": V1._digest(llm / "requests_stress_full_evidence.jsonl"),
                                  "stress_facts_only_v2": V1._digest(llm / "requests_stress_facts_only_v2.jsonl")})
        self.env.step("requests")  # identical re-run is allowed
        path = llm / "requests_stress_full_evidence.jsonl"
        path.write_bytes(path.read_bytes() + b"\n")
        with self.assertRaisesRegex(RuntimeError, "frozen stress full-evidence request mismatch"):
            self.env.step("requests")

    def test_stress_hashes_join_the_eval_request_hashes(self):
        hashes = self.env.out / "request_hashes.json"
        hashes.write_text(json.dumps({"full_evidence": "a" * 64, "facts_only_v2": "b" * 64}))
        self.env.step("requests")
        merged = json.loads(hashes.read_text())
        self.assertEqual((merged["full_evidence"], merged["facts_only_v2"]), ("a" * 64, "b" * 64))
        self.assertEqual(set(merged), {"full_evidence", "facts_only_v2", "stress_full_evidence",
                                       "stress_facts_only_v2"})
        merged["stress_facts_only_v2"] = "c" * 64
        hashes.write_text(json.dumps(merged))
        with self.assertRaisesRegex(RuntimeError, "frozen request hash mismatch"):
            self.env.step("requests")
        with self.assertRaisesRegex(RuntimeError, "frozen request hash mismatch: stress_facts_only_v2"):
            self.env.step("generate")

    def test_stress_generation_is_one_whole_batch_per_arm(self):
        calls = []
        self.env.step("requests")
        metas = self.env.step("generate", stress_batch(self.env.entries, calls=calls))
        llm = self.env.out / "llm"
        self.assertEqual(sorted(calls), sorted([llm / "requests_stress_full_evidence.jsonl",
                                                llm / "requests_stress_facts_only_v2.jsonl"]))
        self.assertEqual(set(metas), {"full_evidence", "facts_only_v2"})
        self.assertTrue(all(m["complete"] for m in metas.values()))
        # Existing outputs are never regenerated.
        self.assertEqual(self.env.step("generate"), {"full_evidence": None, "facts_only_v2": None})

    def test_stress_evaluate_requires_generation(self):
        self.env.step("requests")
        with self.assertRaisesRegex(RuntimeError, "run generate --sets stress"):
            self.env.step("evaluate")

    def test_stress_rows_pair_both_arms_by_record(self):
        bad = self.env.entries[1]["perturbed_id"]
        gone = self.env.entries[2]["perturbed_id"]
        self.env.run(bad_full={bad}, missing={gone})
        rows = pd.read_csv(self.env.out / "stress_paired.csv", dtype={"perturbed_id": str})
        n = len(self.env.entries)
        self.assertEqual(len(rows), 2 * n)
        for arm in ("full_evidence", "facts_only_v2"):
            self.assertEqual(sorted(rows[rows.arm == arm].perturbed_id),
                             sorted(e["perturbed_id"] for e in self.env.entries))
        self.assertEqual(set(rows.columns), {
            "perturbed_id", "record_id", "cohort", "patient_id", "kind", "arm", "status", "follows",
            "new_supported", "old_present", "n_old_unique_hits", "n_old_ambiguous_hits", "missing_output",
            "parsed", "truncated", "check_pass", "follows_and_pass", "status_v1_strict", "follows_v1_strict"})
        by = rows.set_index(["perturbed_id", "arm"])
        good = self.env.entries[0]["perturbed_id"]
        for arm in ("full_evidence", "facts_only_v2"):
            row = by.loc[(good, arm)]
            self.assertEqual(row["status"], "follows", arm)
            self.assertTrue(bool(row["check_pass"]) and bool(row["follows_and_pass"]), arm)
        self.assertEqual(by.loc[(good, "facts_only_v2"), "status_v1_strict"], "follows")
        self.assertTrue(pd.isna(by.loc[(good, "full_evidence"), "follows_v1_strict"]))
        self.assertTrue(pd.isna(by.loc[(good, "full_evidence"), "status_v1_strict"]))
        self.assertEqual(by.loc[(bad, "full_evidence"), "status"], "not_follows")
        self.assertFalse(bool(by.loc[(bad, "full_evidence"), "check_pass"]))
        self.assertEqual(by.loc[(bad, "facts_only_v2"), "status"], "follows")
        for arm in ("full_evidence", "facts_only_v2"):
            self.assertEqual(by.loc[(gone, arm), "status"], "failed", arm)
            self.assertTrue(bool(by.loc[(gone, arm), "missing_output"]), arm)
        summary = pd.read_csv(self.env.out / "summary_stress_paired.csv")
        total = summary[summary.kind == "total"].set_index(["arm", "rule"])
        self.assertEqual(len(total), 3)
        full = total.loc[("full_evidence", V2.SHARED_RULE)]
        self.assertEqual((int(full["n"]), int(full["follows"]), int(full["not_follows"]),
                          int(full["failed_output"]), int(full["unscorable"]), int(full["n_scorable"]),
                          int(full["check_pass"]), int(full["follows_and_pass"])), (n, n - 2, 1, 1, 0, n, n - 2,
                                                                                      n - 2))
        facts = total.loc[("facts_only_v2", V2.SHARED_RULE)]
        self.assertEqual((int(facts["n"]), int(facts["follows"]), int(facts["failed_output"])), (n, n - 1, 1))
        strict = total.loc[("facts_only_v2", V2.STRICT_RULE)]
        self.assertEqual((int(strict["n"]), int(strict["follows"])), (n, n - 1))
        for column in ("follows_rate_all", "follows_rate_scorable", "batch_complete", "n_attempts"):
            self.assertIn(column, summary.columns)
        text = (self.env.out / "summary_stress_paired.csv").read_text()
        self.assertTrue("synthetic" not in text, "record ID in summary_stress_paired.csv")
        self.assertFalse((self.env.v1 / "llm").exists())  # nothing is written under the v1 output root


class TestV2Cli(unittest.TestCase):
    def test_main_dispatches_dev_and_preflight(self):
        with patch.object(V2, "dev_step") as dev, patch.object(V2, "preflight_step") as preflight, \
                contextlib.redirect_stdout(io.StringIO()):
            V2.main(["--steps", "dev", "preflight", "--iteration", "1"])
        dev.assert_called_once()
        self.assertEqual(dev.call_args.kwargs["iteration"], 1)
        preflight.assert_called_once()

    def test_main_dispatches_freeze_and_evaluation_steps(self):
        with patch.object(V2, "freeze_step") as freeze, patch.object(V2, "requests_step") as requests, \
                patch.object(V2, "generate_step", return_value=None) as generate, \
                patch.object(V2, "evaluate_step") as evaluate, contextlib.redirect_stdout(io.StringIO()):
            V2.main(["--steps", "freeze", "requests", "generate", "evaluate", "--gpu-hour-price-usd", "2.5"])
        freeze.assert_called_once()
        self.assertEqual(requests.call_args.kwargs["set_name"], "eval")
        self.assertEqual(generate.call_args.kwargs["set_name"], "eval")
        self.assertEqual(evaluate.call_args.kwargs["gpu_hour_price_usd"], 2.5)

    def test_main_dispatches_the_stress_set(self):
        with patch.object(V2, "requests_step") as requests, \
                patch.object(V2, "generate_step", return_value={"full_evidence": None, "facts_only_v2": None}) \
                as generate, patch.object(V2, "evaluate_step") as evaluate, \
                patch.object(V2, "evaluate_stress_step") as stress, contextlib.redirect_stdout(io.StringIO()):
            V2.main(["--steps", "requests", "generate", "evaluate", "--sets", "stress"])
        self.assertEqual(requests.call_args.kwargs["set_name"], "stress")
        self.assertEqual(generate.call_args.kwargs["set_name"], "stress")
        stress.assert_called_once()
        evaluate.assert_not_called()

    def test_main_requires_iteration_for_dev(self):
        with patch.object(V2, "dev_step") as dev, self.assertRaises(SystemExit), \
                contextlib.redirect_stderr(io.StringIO()):
            V2.main(["--steps", "dev"])
        dev.assert_not_called()


if __name__ == "__main__":
    unittest.main()
