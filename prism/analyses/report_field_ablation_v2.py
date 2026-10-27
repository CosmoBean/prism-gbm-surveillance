"""Facts-only v2 report-field ablation (docs/results/REPORT_FIELD_ABLATION_V2_PLAN.md).

Run ``python -m prism.analyses.report_field_ablation_v2 --steps dev --iteration <k>`` for a development iteration on
the 58-record development partition, and ``--steps preflight`` for the one-record synthetic engine check. Then
``--steps freeze``, ``requests``, ``generate`` and ``evaluate`` for the one evaluation on the locked 406 records. The v1
gate (v3.1 artifacts, checker, frozen prism/report sources, writer, the v1 lock) runs before every v2 step; v1 and v3.1
outputs are read only. Summaries hold aggregate counts only: no report text and no record IDs. Per-record files
(checks_*.csv, paired_rows.csv) hold record IDs with booleans and counts only, and stay untracked under outputs/.
"""

from __future__ import annotations

import argparse
import json
import shutil
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

from prism.analyses import report_field_ablation as V1
from prism.config import REPO, RESULTS
from prism.report import checker
from prism.report import facts_only_v2 as S
from prism.report import field_ablation as A

OUT2 = RESULTS / "analyses" / "report_field_ablation_v2"
SPEC = Path("prism/report/facts_only_v2.py")
RUNNER = Path("prism/analyses/report_field_ablation_v2.py")
FROZEN = Path("FROZEN_v2.json")
REQUEST_HASHES = Path("request_hashes.json")
FACTS_V2 = "facts_only_v2"
ARMS = (A.FULL_EVIDENCE, FACTS_V2)
DEV = Path("records/dev.jsonl")
EVAL = Path("records/eval.jsonl")
DEV_LOCK = Path("dev_lock.json")
PREFLIGHT = Path("preflight.json")
PREFLIGHT_DIR = Path("preflight")
# Protocol section 2: at most iterations 0, 1 and 2; the freeze criterion per cohort and overall.
MAX_ITERATIONS = 3
DEV_CRITERION = {"all": 55, "mu": 29, "lumiere": 15, "ucsf": 9}
DEV_COUNTS = {"all": 58, "mu": 32, "lumiere": 16, "ucsf": 10}
DEV_PATIENTS = {"mu": 20, "lumiere": 10, "ucsf": 10}
COHORTS = ("mu", "lumiere", "ucsf")
SETS = ("eval", "stress")
MAX_TOKENS = 2048
# Interpretability gate (protocol, "Outcomes and analysis"): overall >= 386/406 and each cohort >= 0.90.
GATE_OVERALL = 386
GATE_COHORT_NUM, GATE_COHORT_DEN = 9, 10
EVAL_COUNTS = {"all": 406, **V1.EXPECTED_COHORTS}
COMMON_CRITERIA = ("unsupported_number", "invalid_citation", "forbidden", "clinical_inference")


def _dev_records(root: Path) -> list[dict]:
    return V1._jsonl(root / V1.BASE / DEV)


def _patients(rows: list[dict]) -> set[tuple[str, str]]:
    return {(row["cohort"], str(row["patient_id"])) for row in rows}


def guard_v2(root: Path = REPO, output_root: Path = OUT2, v1_output_root: Path = V1.OUT) -> dict:
    """The v1 gate and lock, the development-set lock (recorded at first run), and dev/eval patient disjointness."""
    root, output_root, v1_output_root = Path(root), Path(output_root), Path(v1_output_root)
    manifest = V1._guard(root, v1_output_root)
    dev = _dev_records(root)
    counts = {"all": len(dev), **{c: sum(r["cohort"] == c for r in dev) for c in COHORTS}}
    patients = {c: len({p for cohort, p in _patients(dev) if cohort == c}) for c in COHORTS}
    if counts != DEV_COUNTS or patients != DEV_PATIENTS or len({r["record_id"] for r in dev}) != len(dev):
        raise RuntimeError("development set count mismatch")
    overlap = _patients(dev) & _patients(V1._jsonl(root / V1.BASE / EVAL))
    if overlap:
        raise RuntimeError(f"development/evaluation patient overlap: {len(overlap)} patient(s)")
    current = {"dev_sha256": V1._digest(root / V1.BASE / DEV),
               "v1_provenance_sha256": V1._digest(v1_output_root / "provenance.json")}
    lock = output_root / DEV_LOCK
    if lock.exists():
        try:
            frozen = json.loads(lock.read_text())
        except ValueError as exc:
            raise RuntimeError("development lock metadata mismatch") from exc
        if frozen.get("dev_sha256") != current["dev_sha256"]:
            raise RuntimeError("development set hash mismatch")
        if frozen.get("v1_provenance_sha256") != current["v1_provenance_sha256"]:
            raise RuntimeError("v1 provenance hash mismatch")
    else:
        output_root.mkdir(parents=True, exist_ok=True)
        lock.write_text(json.dumps(current, indent=2) + "\n")
    return manifest


def qualifies(summary: pd.DataFrame) -> bool:
    """The freeze criterion: overall >= 55/58 and each cohort at or above its minimum, on the complete 58."""
    rows = summary.set_index("cohort")
    if any(cohort not in rows.index for cohort in DEV_CRITERION):
        return False
    return all(int(rows.loc[c, "n"]) == DEV_COUNTS[c] and int(rows.loc[c, "pass"]) >= minimum
               for c, minimum in DEV_CRITERION.items())


# ---------------------------------------------------------------- development iterations
def _dev_paths(output_root: Path, k: int) -> dict[str, Path]:
    return {"requests": output_root / "llm" / f"requests_dev_iter{k}.jsonl",
            "outputs": output_root / "llm" / f"outputs_dev_iter{k}.jsonl",
            "checks": output_root / f"checks_dev_iter{k}.csv",
            "summary": output_root / f"summary_dev_iter{k}.csv",
            "words": output_root / f"non_form_word_counts_dev_iter{k}.csv",
            "info": output_root / f"dev_iter{k}.json"}


def _iteration_artifacts(output_root: Path, k: int) -> list[Path]:
    """Every existing artifact of iteration k: the named files plus the batch output's attempts, logs and metas."""
    paths = _dev_paths(output_root, k)
    stem = paths["outputs"].stem
    batch = [p for p in paths["outputs"].parent.glob(f"{stem}*")
             if p.name.startswith((f"{stem}.", f"{stem}_attempt"))] if paths["outputs"].parent.exists() else []
    return sorted({*[p for p in paths.values() if p.exists()], *batch})


def _refuse_iteration(output_root: Path, iteration: int) -> None:
    if not isinstance(iteration, int) or iteration < 0:
        raise RuntimeError(f"invalid development iteration: {iteration}")
    if iteration >= MAX_ITERATIONS:
        raise RuntimeError(f"at most {MAX_ITERATIONS} development iterations (0 to {MAX_ITERATIONS - 1})")
    if _iteration_artifacts(output_root, iteration):
        raise RuntimeError(f"development iteration {iteration} output already exists; it is not re-run without a "
                           "logged deviation")
    for earlier in range(iteration):
        info = _dev_paths(output_root, earlier)["info"]
        if info.exists() and json.loads(info.read_text()).get("qualifies") is True:
            raise RuntimeError(f"development iteration {earlier} already qualified; it is frozen, no further tuning")
    if iteration > 0:
        previous = _dev_paths(output_root, iteration - 1)
        if not previous["summary"].exists() or not previous["info"].exists():
            raise RuntimeError(f"development iteration {iteration - 1} has no summary")


def _require_preflight(output_root: Path) -> None:
    path = output_root / PREFLIGHT
    try:
        state = json.loads(path.read_text()) if path.exists() else {}
    except ValueError:
        state = {}
    if state.get("complete") is not True or state.get("parsed") is not True:
        raise RuntimeError("run a passing preflight (complete and parsed) before a development iteration or the "
                           "evaluation")


def _quarantine(output_root: Path, iteration: int, meta: dict) -> Path:
    """Move every artifact of a failed (incomplete) batch to deviation_dev_iter<k>_<n>/ with its batch metadata, so
    the failure does not use up the iteration."""
    n = 1
    while (output_root / f"deviation_dev_iter{iteration}_{n}").exists():
        n += 1
    directory = output_root / f"deviation_dev_iter{iteration}_{n}"
    directory.mkdir(parents=True)
    for path in _iteration_artifacts(output_root, iteration):
        shutil.move(str(path), str(directory / path.name))
    fields = ("request_sha256", "complete", "attempts", "n_attempts", "total_process_wall_s", "total_batch_wall_s")
    (directory / "infra_failure.json").write_text(
        json.dumps({"iteration": iteration, **{key: meta.get(key) for key in fields}}, indent=2) + "\n")
    return directory


def _consistency(dev: list[dict]) -> None:
    """Task 1 consistency check on every development record's facts; errors are reported as keys and counts only."""
    errors = Counter()
    failing = 0
    for rec in dev:
        found = S.consistency_errors(A.facts_for_arm(rec, A.FACTS_ONLY))
        failing += bool(found)
        errors.update(set(found))
    if failing:
        detail = "; ".join(f"{error} ({n})" for error, n in sorted(errors.items()))
        raise RuntimeError(f"consistency check failed on {failing} of {len(dev)} development records: {detail}")


def _check_row(rec: dict, out: dict | None) -> tuple[dict, list[str]]:
    facts = A.facts_for_arm(rec, A.FACTS_ONLY)
    claims = A.parse_facts_only(out["text"]) if out else None
    result = S.check(claims, facts)
    truncated = bool(out and out.get("finish_reason") == "length")
    words = len(" ".join(c["text"] for c in claims).split()) if result["parsed"] else 0
    row = {"record_id": rec["record_id"], "cohort": rec["cohort"],
           "pass": bool(result["pass"]) and not truncated, "parsed": bool(result["parsed"]),
           "missing_output": out is None, "truncated": truncated, "n_claims": int(result["n_claims"]),
           "words": words,
           "n_missing_keys": len(result["missing"]), "n_non_form_words": len(result["non_form_words"]),
           "n_prompt_tokens": out.get("n_prompt_tokens") if out else None,
           "n_output_tokens": out.get("n_output_tokens") if out else None,
           **{c: bool(result[c]) for c in S.CRITERIA}}
    return row, list(result["non_form_words"])


def summarise_dev(frame: pd.DataFrame, meta: dict | None = None,
                  gpu_hour_price_usd: float | None = None) -> pd.DataFrame:
    """Pass and the sum of each criterion, overall and by cohort; every record counts, missing outputs as failures."""
    rows = []
    for cohort, group in [("all", frame), *list(frame.groupby("cohort", sort=True))]:
        n, passed = len(group), int(group["pass"].sum())
        low, high = V1.R3.wilson(passed, n)
        row = {"cohort": cohort, "n": n, "pass": passed, "failed": n - passed, "pass_rate": passed / n if n else None,
               "pass_ci_low": low, "pass_ci_high": high,
               "parsed": int(group.parsed.sum()), "missing_output": int(group.missing_output.sum()),
               "truncated": int(group.truncated.sum()),
               **{c: int(group[c].sum()) for c in S.CRITERIA},
               "words_median": float(group.words.median()) if n else None,
               "words_mean": float(group.words.mean()) if n else None,
               "prompt_tokens_total": int(pd.to_numeric(group.n_prompt_tokens, errors="coerce").sum()),
               "output_tokens_total": int(pd.to_numeric(group.n_output_tokens, errors="coerce").sum())}
        row.update(V1._batch_fields(meta or {}, gpu_hour_price_usd))
        rows.append(row)
    return pd.DataFrame(rows)


def _word_counts(frame: pd.DataFrame, words: list[list[str]]) -> pd.DataFrame:
    """Aggregate non-form word counts: reports containing each word, and per criterion how many of them fail it."""
    counts: dict[str, dict] = {}
    for (_, row), found in zip(frame.iterrows(), words):
        for word in found:
            entry = counts.setdefault(word, {"word": word, "n_reports": 0, **{c: 0 for c in S.CRITERIA}})
            entry["n_reports"] += 1
            for c in S.CRITERIA:
                entry[c] += int(bool(row[c]))
    columns = ["word", "n_reports", *S.CRITERIA]
    table = pd.DataFrame(list(counts.values()), columns=columns)
    return table.sort_values(["n_reports", "word"], ascending=[False, True], ignore_index=True)


def dev_step(root: Path = REPO, output_root: Path = OUT2, iteration: int = 0, v1_output_root: Path = V1.OUT,
             gpu_hour_price_usd: float | None = None) -> dict:
    """One whole-batch facts-only development iteration on the 58 development records, scored by the v2 checker."""
    root, output_root = Path(root), Path(output_root)
    _refuse_iteration(output_root, iteration)
    guard_v2(root, output_root, v1_output_root)
    _require_preflight(output_root)
    dev = _dev_records(root)
    _consistency(dev)
    paths = _dev_paths(output_root, iteration)
    paths["requests"].parent.mkdir(parents=True, exist_ok=True)
    rows = [{"id": f"dev|{rec['record_id']}", "messages": S.messages(A.facts_for_arm(rec, A.FACTS_ONLY)),
             "max_tokens": MAX_TOKENS, "schema": S.FACTS_SCHEMA} for rec in dev]
    paths["requests"].write_bytes("".join(json.dumps(row) + "\n" for row in rows).encode())
    request_sha256 = V1._digest(paths["requests"])
    spec_blob = V1._git_blob(root / SPEC)

    def guard() -> None:
        guard_v2(root, output_root, v1_output_root)
        if V1._digest(paths["requests"]) != request_sha256:
            raise RuntimeError(f"development iteration {iteration} request hash mismatch")
        if V1._git_blob(root / SPEC) != spec_blob:
            raise RuntimeError(f"specification changed during development iteration {iteration}")
    meta = V1._whole_batch(root, paths["requests"], paths["outputs"], guard)
    if not meta.get("complete"):
        directory = _quarantine(output_root, iteration, meta)
        raise RuntimeError(f"development iteration {iteration} batch failed (incomplete); its artifacts were moved "
                           f"to {directory.name}/. A logged deviation is required before re-running iteration "
                           f"{iteration}.")
    guard()
    outputs = V1._output_map(paths["outputs"], {row["id"] for row in rows})
    checked = [_check_row(rec, outputs.get(f"dev|{rec['record_id']}")) for rec in dev]
    frame = pd.DataFrame([row for row, _ in checked])
    frame.to_csv(paths["checks"], index=False)
    summary = summarise_dev(frame, meta, gpu_hour_price_usd)
    summary.to_csv(paths["summary"], index=False)
    _word_counts(frame, [words for _, words in checked]).to_csv(paths["words"], index=False)
    info = {"iteration": iteration, "spec_version": S.SPEC_VERSION, "spec_blob": spec_blob,
            "qualifies": qualifies(summary), "request_sha256": request_sha256,
            "dev_sha256": V1._digest(root / V1.BASE / DEV)}
    paths["info"].write_text(json.dumps(info, indent=2) + "\n")
    passed = summary.set_index("cohort")["pass"].astype(int).to_dict()
    print(f"dev iteration {iteration}: pass {passed}; qualifies {info['qualifies']}", flush=True)
    return info


# ---------------------------------------------------------------- preflight
def _synthetic_card() -> dict:
    ev = {"cohort": "mu", "tier": "few cases", "n_scans": 11, "n_progression": 3, "n_no_progression": 8}
    return {"situation": {"text": "early post-RT (within 12 weeks of RT end); enhancing tumour increased since the "
                                  "previous scan"}, "own_cohort": "mu", "tier": "few cases", "evidence": {"mu": ev},
            "agreement": {"timeline_side": "below", "images_side": "above", "agree": False,
                          "medians": {"timeline": 0.343, "images": 0.3227},
                          "progression_rate_same_direction": 0.139}}


def synthetic_record() -> dict:
    """The synthetic record of tests.test_report_v3.record(), rebuilt here with obviously synthetic IDs. It is no
    patient record and is used only for the preflight."""
    return {"cohort": "mu", "record_id": "synthetic|preflight", "scan_id": "synthetic-preflight",
            "patient_id": "synthetic-preflight", "phase_of_care": "early_post_rt",
            "scores": {"timeline": 0.0548, "images": 0.3819, "combined": 0.2267},
            "measurements": {"volumes_cc": {"et": 37.248, "snfh": 45.757, "necrosis": 2.81, "cavity": 0.0},
                             "n_earlier_scans": 1,
                             "previous": {"days_before": 56.0, "volumes_cc": {"et": 33.779, "snfh": 44.251}},
                             "change_from_previous_cc": {"et": 3.469, "snfh": 1.506},
                             "earlier_minimum_cc": {"et": 33.779}, "change_from_earlier_minimum_cc": {"et": 3.469}},
            "card": _synthetic_card(),
            "conformal": {"alpha_0.2": {"timeline": "{0}", "images": "{0, 1}", "combined": "{0, 1}"},
                          "alpha_0.1": {"timeline": "{0, 1}", "images": "{0, 1}", "combined": "{0, 1}"}},
            "flags": {"pathways_disagree": True, "out_of_range": True,
                      "out_of_range_reasons": ["MGMT status unknown"], "tier_flag": True,
                      "conformal_uncertain": True},
            "provenance": {"models": {"timeline": "B1 (C2)", "images": "I_pure (volumes)",
                                      "combined": "B1 + I_pure"}}}


def preflight_step(root: Path = REPO, output_root: Path = OUT2, v1_output_root: Path = V1.OUT) -> dict:
    """Run the writer on one synthetic record through the same runner and engine flags. Each run has its own
    directory under preflight/ and is logged; it never counts as an evaluation attempt."""
    root, output_root = Path(root), Path(output_root)
    guard_v2(root, output_root, v1_output_root)
    base = output_root / PREFLIGHT_DIR
    run = 1 + sum(1 for p in base.glob("run*") if p.is_dir()) if base.exists() else 1
    directory = base / f"run{run}"
    directory.mkdir(parents=True, exist_ok=False)
    rec = synthetic_record()
    request = directory / "requests_preflight.jsonl"
    row = {"id": f"preflight|{rec['record_id']}", "messages": S.messages(A.facts_for_arm(rec, A.FACTS_ONLY)),
           "max_tokens": MAX_TOKENS, "schema": S.FACTS_SCHEMA}
    request.write_text(json.dumps(row) + "\n")
    target = directory / "outputs_preflight.jsonl"
    meta = V1._whole_batch(root, request, target, lambda: guard_v2(root, output_root, v1_output_root))
    outputs = V1._output_map(target, {row["id"]}) if target.exists() else {}
    out = outputs.get(row["id"])
    claims = A.parse_facts_only(out["text"]) if out else None
    result = {"complete": bool(meta.get("complete")), "parsed": claims is not None,
              "request_sha256": V1._digest(request), "run": run, "spec_version": S.SPEC_VERSION,
              "n_attempts": meta.get("n_attempts")}
    with (base / "preflight_log.jsonl").open("a") as log:
        log.write(json.dumps(result) + "\n")
    (output_root / PREFLIGHT).write_text(json.dumps(result, indent=2) + "\n")
    print(f"preflight run {run}: complete {result['complete']}, parsed {result['parsed']}", flush=True)
    return result


# ---------------------------------------------------------------- freeze
def _line_hashes(path: Path) -> list[str]:
    return [V1._digest_bytes(line) for line in path.read_bytes().splitlines(keepends=True)]


def _frozen_values(root: Path, v1_output_root: Path) -> dict:
    """Every value FROZEN_v2.json records except the qualifying iteration, recomputed from the current files."""
    for path, name in ((root / SPEC, "specification"), (root / RUNNER, "v2 runner"),
                       (v1_output_root / V1.STRESS_RECORDS, "v1 stress set")):
        if not path.is_file():
            raise RuntimeError(f"{name} missing")
    base = root / V1.BASE
    return {"spec_version": S.SPEC_VERSION,
            "spec_blob": V1._git_blob(root / SPEC), "spec_sha256": V1._digest(root / SPEC),
            "runner_blob": V1._git_blob(root / RUNNER), "runner_sha256": V1._digest(root / RUNNER),
            "writer": V1.EXPECTED_WRITER, "prefixes": list(A.FULL_ONLY_PREFIXES),
            "v1_manifest_sha256": V1._digest(root / V1.MANIFEST),
            "eval_sha256": V1._digest(base / EVAL), "eval_line_sha256": _line_hashes(base / EVAL),
            "dev_sha256": V1._digest(base / DEV), "dev_line_sha256": _line_hashes(base / DEV),
            "stress_sha256": V1._digest(v1_output_root / V1.STRESS_RECORDS)}


def _qualifying_iteration(output_root: Path) -> tuple[int, dict]:
    """The first development iteration whose recorded summary meets the freeze criterion."""
    for k in range(MAX_ITERATIONS):
        paths = _dev_paths(output_root, k)
        if not paths["info"].exists():
            continue
        info = json.loads(paths["info"].read_text())
        if info.get("qualifies") is True:
            if not paths["summary"].exists() or not qualifies(pd.read_csv(paths["summary"])):
                raise RuntimeError(f"development iteration {k} summary does not meet the freeze criterion")
            return k, info
    raise RuntimeError("no qualifying development iteration; nothing is frozen (stop rule after iteration 2)")


def freeze_step(root: Path = REPO, output_root: Path = OUT2, v1_output_root: Path = V1.OUT) -> dict:
    """Record FROZEN_v2.json from the first qualifying development iteration, whose specification must be the current
    one. The consistency check runs again on the development facts. An existing, different freeze is never
    overwritten."""
    root, output_root, v1_output_root = Path(root), Path(output_root), Path(v1_output_root)
    guard_v2(root, output_root, v1_output_root)
    k, info = _qualifying_iteration(output_root)
    if info.get("spec_blob") != V1._git_blob(root / SPEC):
        raise RuntimeError(f"specification changed since development iteration {k}; it cannot be frozen")
    _consistency(_dev_records(root))
    frozen = {**_frozen_values(root, v1_output_root), "qualifying_iteration": k,
              "dev_iter_sha256": V1._digest(_dev_paths(output_root, k)["info"])}
    path = output_root / FROZEN
    if path.exists():
        try:
            existing = json.loads(path.read_text())
        except ValueError:
            existing = None
        if existing != frozen:
            raise RuntimeError("FROZEN_v2.json exists and differs; the freeze is not redone")
        return existing
    path.write_text(json.dumps(frozen, indent=2) + "\n")
    print(f"freeze: development iteration {k}, specification {S.SPEC_VERSION}", flush=True)
    return frozen


def guard_frozen(root: Path = REPO, output_root: Path = OUT2, v1_output_root: Path = V1.OUT) -> dict:
    """guard_v2, then every FROZEN_v2.json value must still match the current files. Returns the v1 manifest."""
    root, output_root, v1_output_root = Path(root), Path(output_root), Path(v1_output_root)
    manifest = guard_v2(root, output_root, v1_output_root)
    path = output_root / FROZEN
    if not path.exists():
        raise RuntimeError("run freeze before the evaluation steps")
    try:
        frozen = json.loads(path.read_text())
    except ValueError as exc:
        raise RuntimeError("frozen v2 metadata mismatch") from exc
    current = _frozen_values(root, v1_output_root)
    for key, value in current.items():
        if frozen.get(key) != value:
            raise RuntimeError(f"frozen {key} mismatch")
    k = frozen.get("qualifying_iteration")
    info = _dev_paths(output_root, k)["info"] if isinstance(k, int) else None
    if info is None or not info.exists() or V1._digest(info) != frozen.get("dev_iter_sha256"):
        raise RuntimeError("frozen qualifying iteration mismatch")
    return manifest


# ---------------------------------------------------------------- one evaluation on the locked 406 records
def _request_path(output_root: Path, arm: str) -> Path:
    return output_root / "llm" / f"requests_{arm}.jsonl"


def _output_path(output_root: Path, arm: str) -> Path:
    return output_root / "llm" / f"outputs_{arm}.jsonl"


def _write_once(path: Path, data: bytes, what: str) -> None:
    if path.exists() and path.read_bytes() != data:
        raise RuntimeError(f"frozen {what} request mismatch")
    path.write_bytes(data)


def requests_step(root: Path = REPO, output_root: Path = OUT2, set_name: str = "eval",
                  v1_output_root: Path = V1.OUT) -> None:
    """The full arm's request is the v3.1 request, byte for byte; the facts-only v2 request is rendered from the
    frozen specification, IDs eval|<record_id> in manifest order. Both hashes go to request_hashes.json."""
    if set_name != "eval":
        raise NotImplementedError(f"{set_name} requests are not implemented in this step")
    root, output_root = Path(root), Path(output_root)
    manifest = guard_frozen(root, output_root, v1_output_root)
    _require_preflight(output_root)
    records = V1._records(root)
    (output_root / "llm").mkdir(parents=True, exist_ok=True)
    full = (root / V1.BASE / "llm/requests_eval.jsonl").read_bytes()
    rows = [{"id": f"eval|{item['record_id']}",
             "messages": S.messages(A.facts_for_arm(records[item["record_id"]], A.FACTS_ONLY)),
             "max_tokens": MAX_TOKENS, "schema": S.FACTS_SCHEMA} for item in manifest["records"]]
    if [json.loads(line)["id"] for line in full.splitlines() if line.strip()] != [row["id"] for row in rows]:
        raise RuntimeError("paired request IDs or order mismatch")
    _write_once(_request_path(output_root, A.FULL_EVIDENCE), full, "full-evidence")
    _write_once(_request_path(output_root, FACTS_V2), "".join(json.dumps(r) + "\n" for r in rows).encode(),
                "facts-only v2")
    hashes = {arm: V1._digest(_request_path(output_root, arm)) for arm in ARMS}
    frozen = output_root / REQUEST_HASHES
    if frozen.exists() and json.loads(frozen.read_text()) != hashes:
        raise RuntimeError("frozen request hash mismatch")
    frozen.write_text(json.dumps(hashes, indent=2) + "\n")


def _guard_requests(root: Path, output_root: Path, v1_output_root: Path) -> dict:
    manifest = guard_frozen(root, output_root, v1_output_root)
    _require_preflight(output_root)
    frozen = output_root / REQUEST_HASHES
    if not frozen.exists():
        raise RuntimeError("run requests before generation or evaluation")
    hashes = json.loads(frozen.read_text())
    for arm in ARMS:
        path = _request_path(output_root, arm)
        if not path.exists() or hashes.get(arm) != V1._digest(path):
            raise RuntimeError(f"frozen request hash mismatch: {arm}")
    return manifest


def _import_full(root: Path, output_root: Path) -> None:
    """Copy the immutable v3.1 output and metadata byte for byte, or verify an earlier copy."""
    baseline = root / V1.BASE / "llm/outputs_eval.jsonl"
    for source, dest, what in ((baseline, _output_path(output_root, A.FULL_EVIDENCE), "output"),
                               (Path(str(baseline) + ".meta.json"),
                                Path(str(_output_path(output_root, A.FULL_EVIDENCE)) + ".meta.json"), "metadata")):
        if dest.exists() and V1._digest(dest) != V1._digest(source):
            raise RuntimeError(f"imported full-arm {what} hash mismatch")
        if not dest.exists():
            shutil.copyfile(source, dest)


def generate_step(root: Path = REPO, output_root: Path = OUT2, set_name: str = "eval",
                  v1_output_root: Path = V1.OUT) -> dict | None:
    """Import the full arm; generate the facts-only v2 arm once, as one whole batch with at most one identical retry.
    An existing facts-only output is never regenerated."""
    if set_name != "eval":
        raise NotImplementedError(f"{set_name} generation is not implemented in this step")
    root, output_root = Path(root), Path(output_root)
    _guard_requests(root, output_root, v1_output_root)
    _import_full(root, output_root)
    target = _output_path(output_root, FACTS_V2)
    if target.exists():
        return None
    meta = V1._whole_batch(root, _request_path(output_root, FACTS_V2), target,
                           lambda: _guard_requests(root, output_root, v1_output_root))
    _guard_requests(root, output_root, v1_output_root)
    return meta


def _full_arm(manifest: dict, records: dict, outputs: dict, baseline: pd.DataFrame) -> tuple[dict, dict, dict]:
    """Per record: the paired-row fields from the v3.1 checks, the parsed claims, and the per-claim check_claim
    results recomputed with the frozen checker. Every imported output v3.1 reported passing must pass again."""
    rows, claims_by, details = {}, {}, {}
    mismatched = 0
    for item in manifest["records"]:
        rid = item["record_id"]
        out = outputs.get(f"eval|{rid}")
        facts = A.facts_for_arm(records[rid], A.FULL_EVIDENCE)
        claims = checker.parse_structured(out["text"]) if out else None
        frozen = baseline.loc[rid]
        if out is not None and bool(frozen["pass"]) and not checker.check(claims, facts, card=True)["pass"]:
            mismatched += 1
        present = out is not None
        rows[rid] = {"pass": bool(frozen["pass"]) and present, "parsed": bool(frozen["parsed"]) and present,
                     "required_content_pass": not bool(frozen["fail_required_missing"]) and present,
                     "missing_output": not present}
        claims_by[rid] = claims
        details[rid] = [checker.check_claim(c, facts) for c in claims] if claims is not None else None
    if mismatched:
        raise RuntimeError(f"full-arm recheck does not reproduce the v3.1 pass on {mismatched} record(s)")
    return rows, claims_by, details


def gate(summary: pd.DataFrame) -> dict:
    """The interpretability gate: facts-only v2 passes >= 386/406 overall and >= 0.90 in each cohort, on the complete
    406 records."""
    rows = summary.set_index("cohort")
    by_cohort = {c: {"n": int(rows.loc[c, "n"]), "pass": int(rows.loc[c, "pass"]),
                     "rate": int(rows.loc[c, "pass"]) / int(rows.loc[c, "n"]) if int(rows.loc[c, "n"]) else None}
                 for c in EVAL_COUNTS if c != "all" and c in rows.index}
    complete = all(c in rows.index and int(rows.loc[c, "n"]) == n for c, n in EVAL_COUNTS.items())
    overall = int(rows.loc["all", "pass"]) if "all" in rows.index else 0
    met = complete and overall >= GATE_OVERALL and all(
        v["pass"] * GATE_COHORT_DEN >= v["n"] * GATE_COHORT_NUM for v in by_cohort.values())
    return {"overall_pass": overall, "by_cohort": by_cohort, "met": bool(met)}


def _groups(frame: pd.DataFrame) -> list[tuple[str, pd.DataFrame]]:
    return [("all", frame), *[(c, frame[frame.cohort == c]) for c in COHORTS]]


def _ci(group: pd.DataFrame, outcome: str) -> tuple[float | None, float | None]:
    return V1._cluster_ci(group, outcome) if len(group) else (None, None)


def information_added(paired: pd.DataFrame, full_details: dict, facts_only_claims: dict) -> pd.DataFrame:
    """Secondary outcome 1 on records where both arms pass. Model-derived keys count only when cited in a full-arm
    claim the frozen checker marks supported with valid citations. Shared keys are the facts-only keys; coverage is
    the number of distinct shared keys each arm cites, paired full minus facts-only with a patient-cluster CI."""
    prefixes = [p.rstrip(".") for p in A.FULL_ONLY_PREFIXES]
    both = paired[paired[f"{A.FULL_EVIDENCE}_pass"].astype(bool) & paired[f"{A.FACTS_ONLY}_pass"].astype(bool)]
    rows = []
    for _, item in both.iterrows():
        rid = item["scan_id"]
        valid = [r for r in (full_details.get(rid) or []) if r["supported"] and not r["invalid_fields"]]
        model = {k for r in valid for k in r["fields"] if k.startswith(A.FULL_ONLY_PREFIXES)}
        full_shared = {k for r in valid for k in r["fields"] if not k.startswith(A.FULL_ONLY_PREFIXES)}
        facts_shared = {k for c in (facts_only_claims.get(rid) or []) for k in c.get("fields", [])
                        if not k.startswith(A.FULL_ONLY_PREFIXES)}
        rows.append({"scan_id": rid, "cohort": item["cohort"], "patient_id": item["patient_id"],
                     "n_model_keys": len(model),
                     **{f"keys_{p}": sum(k.startswith(p + ".") for k in model) for p in prefixes},
                     f"{A.FULL_EVIDENCE}_shared_keys": len(full_shared),
                     f"{A.FACTS_ONLY}_shared_keys": len(facts_shared),
                     "full_not_facts": bool(full_shared - facts_shared),
                     "facts_not_full": bool(facts_shared - full_shared)})
    columns = ["scan_id", "cohort", "patient_id", "n_model_keys", *[f"keys_{p}" for p in prefixes],
               f"{A.FULL_EVIDENCE}_shared_keys", f"{A.FACTS_ONLY}_shared_keys", "full_not_facts", "facts_not_full"]
    per_record = pd.DataFrame(rows, columns=columns)
    out = []
    for cohort, group in _groups(per_record):
        n = len(group)
        keys = group.n_model_keys.astype(float)
        citing = int((group.n_model_keys > 0).sum())
        diff = (group[f"{A.FULL_EVIDENCE}_shared_keys"] - group[f"{A.FACTS_ONLY}_shared_keys"]).astype(float)
        low, high = _ci(group, "shared_keys")
        row = {"cohort": cohort, "n_both_pass": n, "n_full_citing_model_key": citing,
               "share_full_citing_model_key": citing / n if n else None,
               "model_keys_median": float(keys.median()) if n else None,
               "model_keys_q1": float(keys.quantile(0.25)) if n else None,
               "model_keys_q3": float(keys.quantile(0.75)) if n else None}
        for p in prefixes:
            row[f"n_reports_{p}"] = int((group[f"keys_{p}"] > 0).sum())
            row[f"n_keys_{p}"] = int(group[f"keys_{p}"].sum())
        row.update({"shared_keys_full_mean": float(group[f"{A.FULL_EVIDENCE}_shared_keys"].mean()) if n else None,
                    "shared_keys_facts_only_mean": float(group[f"{A.FACTS_ONLY}_shared_keys"].mean()) if n else None,
                    "shared_keys_difference_full_minus_facts_only": float(diff.mean()) if n else None,
                    "shared_keys_difference_ci_low": low, "shared_keys_difference_ci_high": high,
                    "n_full_shared_not_facts_only": int(group.full_not_facts.sum()),
                    "n_facts_only_shared_not_full": int(group.facts_not_full.sum())})
        out.append(row)
    return pd.DataFrame(out)


def common_criteria(full_claims: dict, facts_only_claims: dict, facts: dict) -> pd.DataFrame:
    """Secondary outcome 2, per arm and record: the same arm-agnostic tests on both arms, each against that arm's
    facts (`facts` holds the full facts; the facts-only facts are derived by the field contract). As in the v2
    checker, forbidden wording and clinical inference skip verbatim copies of supplied statements. An unparsed or
    missing output fails every criterion."""
    rows = []
    for rid, full in facts.items():
        shared = {k: v for k, v in full.items() if not k.startswith(A.FULL_ONLY_PREFIXES)}
        for arm, claims, arm_facts in ((A.FULL_EVIDENCE, full_claims.get(rid), full),
                                       (A.FACTS_ONLY, facts_only_claims.get(rid), shared)):
            row = {"record_id": rid, "arm": arm, "unparsed": claims is None}
            if claims is None:
                row.update({"n_claims": 0, "n_unsupported_numbers": None, "n_invalid_citations": None,
                            **{f"fail_{c}": True for c in COMMON_CRITERIA}})
            else:
                checked = [checker.check_claim(c, arm_facts) for c in claims]
                text = " ".join(S._without_statements(c["text"], arm_facts) for c in claims)
                n_numbers = sum(len(r["unsupported_numbers"]) for r in checked)
                n_invalid = sum(len(r["invalid_fields"]) for r in checked)
                row.update({"n_claims": len(claims), "n_unsupported_numbers": n_numbers,
                            "n_invalid_citations": n_invalid,
                            "fail_unsupported_number": bool(n_numbers), "fail_invalid_citation": bool(n_invalid),
                            "fail_forbidden": any(checker.forbidden_v3(text).values()),
                            "fail_clinical_inference": bool(A._CLINICAL_INFERENCE.search(text))})
            rows.append(row)
    return pd.DataFrame(rows)


def _common_summary(per_record: pd.DataFrame, paired: pd.DataFrame) -> pd.DataFrame:
    """Counts by arm and cohort, with the paired full-minus-facts-only difference and its patient-cluster CI."""
    wide = paired[["scan_id", "cohort", "patient_id"]].copy()
    for arm in (A.FULL_EVIDENCE, A.FACTS_ONLY):
        rows = per_record[per_record.arm == arm].set_index("record_id")
        wide[f"{arm}_unparsed"] = wide.scan_id.map(rows.unparsed).astype(bool)
        for c in COMMON_CRITERIA:
            wide[f"{arm}_fail_{c}"] = wide.scan_id.map(rows[f"fail_{c}"]).astype(bool)
    out = []
    for cohort, group in _groups(wide):
        row = {"cohort": cohort, "n": len(group)}
        for arm in (A.FULL_EVIDENCE, A.FACTS_ONLY):
            row[f"{arm}_unparsed"] = int(group[f"{arm}_unparsed"].sum())
        for c in COMMON_CRITERIA:
            full, facts = group[f"{A.FULL_EVIDENCE}_fail_{c}"].astype(int), group[f"{A.FACTS_ONLY}_fail_{c}"].astype(int)
            low, high = _ci(group, f"fail_{c}")
            row.update({f"{A.FULL_EVIDENCE}_fail_{c}": int(full.sum()), f"{A.FACTS_ONLY}_fail_{c}": int(facts.sum()),
                        f"fail_{c}_difference_full_minus_facts_only": float((full - facts).mean()) if len(group)
                        else None, f"fail_{c}_difference_ci_low": low, f"fail_{c}_difference_ci_high": high})
        out.append(row)
    return pd.DataFrame(out)


def _reference_check(manifest: dict, records: dict) -> pd.DataFrame:
    """The deterministic reference report checked on every record's facts, with no model; aggregate counts only."""
    rows = []
    for item in manifest["records"]:
        facts = A.facts_for_arm(records[item["record_id"]], A.FACTS_ONLY)
        result = S.check(S.reference_report(facts), facts)
        rows.append({"cohort": item["cohort"], "pass": bool(result["pass"]),
                     "consistency_error": bool(S.consistency_errors(facts)), **{c: bool(result[c]) for c in S.CRITERIA}})
    frame = pd.DataFrame(rows)
    return pd.DataFrame([{"cohort": cohort, "n": len(group), "pass": int(group["pass"].sum()),
                          "consistency_errors": int(group.consistency_error.sum()),
                          **{c: int(group[c].sum()) for c in S.CRITERIA}} for cohort, group in _groups(frame)])


def evaluate_step(root: Path = REPO, output_root: Path = OUT2, v1_output_root: Path = V1.OUT,
                  gpu_hour_price_usd: float | None = None) -> dict:
    """Score both arms on the 406 records and write the pre-specified summaries. Missing or unparsed facts-only
    outputs are failures everywhere."""
    root, output_root = Path(root), Path(output_root)
    manifest = _guard_requests(root, output_root, v1_output_root)
    records = V1._records(root)
    ordered = {item["record_id"]: records[item["record_id"]] for item in manifest["records"]}
    expected = {f"eval|{rid}" for rid in ordered}
    full_path, facts_path = _output_path(output_root, A.FULL_EVIDENCE), _output_path(output_root, FACTS_V2)
    meta_path = Path(str(facts_path) + ".meta.json")
    if not full_path.exists() or V1._digest(full_path) != V1._digest(root / V1.BASE / "llm/outputs_eval.jsonl"):
        raise RuntimeError("imported full-arm output hash mismatch")
    if not meta_path.exists():
        raise RuntimeError("run generate before evaluate (no facts-only v2 batch metadata)")
    baseline = pd.read_csv(root / V1.BASE / "checks_eval.csv", dtype={"scan_id": str}).set_index("scan_id")
    full_rows, full_claims, full_details = _full_arm(manifest, ordered, V1._output_map(full_path, expected), baseline)
    facts_outputs = V1._output_map(facts_path, expected)
    facts_rows, facts_claims = [], {}
    for rid, rec in ordered.items():
        out = facts_outputs.get(f"eval|{rid}")
        facts_rows.append(_check_row(rec, out)[0])
        facts_claims[rid] = A.parse_facts_only(out["text"]) if out else None
    checks = pd.DataFrame(facts_rows)
    checks.to_csv(output_root / f"checks_{FACTS_V2}.csv", index=False)
    meta = json.loads(meta_path.read_text())
    summary = summarise_dev(checks, meta, gpu_hour_price_usd)
    summary.to_csv(output_root / f"summary_{FACTS_V2}.csv", index=False)
    _reference_check(manifest, ordered).to_csv(output_root / "reference_check.csv", index=False)
    facts_lookup = {row["record_id"]: {"pass": row["pass"], "parsed": row["parsed"],
                                       "required_content_pass": row["parsed"] and not row["fail_required_missing"],
                                       "missing_output": row["missing_output"]} for row in facts_rows}
    paired = V1.paired_rows(ordered, full_rows, facts_lookup)
    paired.to_csv(output_root / "paired_rows.csv", index=False)
    V1.paired_summary(paired).to_csv(output_root / "paired_summary.csv", index=False)
    result = gate(summary)
    (output_root / "gate.json").write_text(json.dumps(result, indent=2) + "\n")
    information_added(paired, full_details, facts_claims).to_csv(output_root / "information_added.csv", index=False)
    common = common_criteria(full_claims, facts_claims,
                             {rid: A.facts_for_arm(rec, A.FULL_EVIDENCE) for rid, rec in ordered.items()})
    common.to_csv(output_root / "checks_common_criteria.csv", index=False)
    _common_summary(common, paired).to_csv(output_root / "common_criteria.csv", index=False)
    print(f"evaluate: facts-only v2 pass {result['overall_pass']}/{len(ordered)}; gate met {result['met']}",
          flush=True)
    return result


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--steps", nargs="+", required=True,
                        choices=("dev", "preflight", "freeze", "requests", "generate", "evaluate"))
    parser.add_argument("--iteration", type=int, default=None, help="development iteration (0, 1 or 2) for dev")
    parser.add_argument("--sets", nargs="+", choices=SETS, default=["eval"],
                        help="sets for the evaluation requests and generation steps")
    parser.add_argument("--gpu-hour-price-usd", type=float, default=None,
                        help="optional local GPU hourly price for cost estimate")
    args = parser.parse_args(argv)
    if "dev" in args.steps and args.iteration is None:
        parser.error("--iteration is required for the dev step")
    for step in args.steps:
        if step == "dev":
            dev_step(iteration=args.iteration, gpu_hour_price_usd=args.gpu_hour_price_usd)
        elif step == "preflight":
            preflight_step()
        elif step == "freeze":
            freeze_step()
        elif step == "requests":
            for set_name in args.sets:
                requests_step(set_name=set_name)
        elif step == "generate":
            for set_name in args.sets:
                final = generate_step(set_name=set_name)
                if final is not None and not final.get("complete"):
                    print(f"generate: facts-only v2 {set_name} batch failed twice; records without output count as "
                          "failures", flush=True)
        else:
            evaluate_step(gpu_hour_price_usd=args.gpu_hour_price_usd)
        print(f"{step}: complete", flush=True)


if __name__ == "__main__":
    main()
