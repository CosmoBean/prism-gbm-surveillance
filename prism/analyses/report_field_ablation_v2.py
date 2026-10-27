"""Facts-only v2 report-field ablation (docs/results/REPORT_FIELD_ABLATION_V2_PLAN.md).

Run ``python -m prism.analyses.report_field_ablation_v2 --steps dev --iteration <k>`` for a development iteration on
the 58-record development partition, and ``--steps preflight`` for the one-record synthetic engine check. The v1 gate
(v3.1 artifacts, checker, frozen prism/report sources, writer, the v1 lock) runs before every v2 step; v1 and v3.1
outputs are read only. Summaries hold aggregate counts only: no report text and no record IDs.
"""

from __future__ import annotations

import argparse
import json
import shutil
from collections import Counter
from pathlib import Path

import pandas as pd

from prism.analyses import report_field_ablation as V1
from prism.config import REPO, RESULTS
from prism.report import facts_only_v2 as S
from prism.report import field_ablation as A

OUT2 = RESULTS / "analyses" / "report_field_ablation_v2"
SPEC = Path("prism/report/facts_only_v2.py")
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
        raise RuntimeError("run a passing preflight (complete and parsed) before a development iteration")


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
    row = {"record_id": rec["record_id"], "cohort": rec["cohort"],
           "pass": bool(result["pass"]) and not truncated, "parsed": bool(result["parsed"]),
           "missing_output": out is None, "truncated": truncated, "n_claims": int(result["n_claims"]),
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
        row = {"cohort": cohort, "n": n, "pass": passed, "failed": n - passed, "pass_rate": passed / n if n else None,
               "parsed": int(group.parsed.sum()), "missing_output": int(group.missing_output.sum()),
               "truncated": int(group.truncated.sum()),
               **{c: int(group[c].sum()) for c in S.CRITERIA},
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


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--steps", nargs="+", required=True, choices=("dev", "preflight"))
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
        else:
            preflight_step()
        print(f"{step}: complete", flush=True)


if __name__ == "__main__":
    main()
