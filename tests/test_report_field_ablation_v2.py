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
from tests.test_report_v3 import record
from tests.test_report_v3_1 import lumiere
from tests.test_report_field_ablation import SUBJECT_ID, _copy_gated_root
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
        (self.root / SPEC).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO_ROOT / SPEC, self.root / SPEC)
        self.v1 = self.root / "v1"
        V1.freeze_step(self.root, self.v1)
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


class TestV2Cli(unittest.TestCase):
    def test_main_dispatches_dev_and_preflight(self):
        with patch.object(V2, "dev_step") as dev, patch.object(V2, "preflight_step") as preflight, \
                contextlib.redirect_stdout(io.StringIO()):
            V2.main(["--steps", "dev", "preflight", "--iteration", "1"])
        dev.assert_called_once()
        self.assertEqual(dev.call_args.kwargs["iteration"], 1)
        preflight.assert_called_once()

    def test_main_requires_iteration_for_dev(self):
        with patch.object(V2, "dev_step") as dev, self.assertRaises(SystemExit), \
                contextlib.redirect_stderr(io.StringIO()):
            V2.main(["--steps", "dev"])
        dev.assert_not_called()


if __name__ == "__main__":
    unittest.main()
