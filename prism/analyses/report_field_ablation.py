"""Local paired report-field ablation on the immutable v3.1 evaluation set.

Run ``python -m prism.analyses.report_field_ablation --steps freeze requests generate evaluate render``.
The full arm imports v3.1 output; only the facts-only arm invokes the local writer.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd

from prism.analyses import report_v3 as R3, report_v3_1 as R31
from prism.config import REPO, RESULTS
from prism.report import field_ablation as A

OUT = RESULTS / "analyses" / "report_field_ablation"
BASE = Path("outputs/results/analyses/report_v3_1")
MANIFEST = Path("docs/results/REPORT_FIELD_ABLATION_PLAN.md")
ARMS = (A.FULL_EVIDENCE, A.FACTS_ONLY)
BASE_FILES = (
    "records/eval.jsonl", "FROZEN_hashes.txt", "llm/requests_eval.jsonl",
    "llm/outputs_eval.jsonl", "llm/outputs_eval.jsonl.meta.json",
    "checks_eval.csv", "summary_eval.csv", "stress.csv", "summary_stress.csv",
)
BASE_SHA256 = dict(zip(BASE_FILES, (
    "d5057aec85da38523c0d515165cc9dcb476811c1889b4543137792e9229abb1e",
    "d9dc2ca6c256a80d98395db0f191d0b475b48e863dce3e7fbf996e9d80c58b3b",
    "f3eb64b1cf92a6376344211c1447e731a0ce169faa0e7cc90b02fccc7f62e85f",
    "669ae9ffcde0c8e0da0b7fe4b3c22134745dd5370bc2b13a9b57d5bc51baa924",
    "1b2793f5ad48ab418af6bf8990cfa6d0752e884bab467a53c7630930ecb30c81",
    "096333141f2b44327957922b9a6b1adaaa9af48dfc9b6f53dea67adc8a5257ea",
    "281af6baea2ce242a8ac98121aa19e688e01cdc4f1d0d5f807d664cdbeddfeb0",
    "d3f52a82c0150058c192ab3bd7c132f454e8d8f903e1dbf108ba03789f95c78a",
    "b979a32f79fb59ea61cca5d4056b045f0865a18f2678662580e27d6ec295dee8",
)))
EXPECTED_COHORTS = {"mu": 114, "lumiere": 162, "ucsf": 130}
EXPECTED_WRITER = {"key": "qwen3.8-27b", "id": "Qwen/Qwen3.8-27B",
                   "revision": "1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0"}
CHECKER_SHA256 = "83665b34998406d2390f7d5ad12f8893df3ebf2ab69c78a2f6490181c34e657e"


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _manifest(root: Path) -> dict:
    path = root / MANIFEST
    text = (path if path.exists() else REPO / MANIFEST).read_text()
    return json.loads(text.split("```json\n", 1)[1].split("\n```", 1)[0])


def verify_v31_baseline(root: Path = REPO, output_root: Path | None = None) -> dict:
    """Refuse any changed canonical input, writer, or frozen full-arm result."""
    root = Path(root)
    manifest = _manifest(root)
    base = root / BASE
    if manifest["record_count"] != 406 or manifest["counts_by_cohort"] != EXPECTED_COHORTS:
        raise RuntimeError("canonical 406-record manifest count mismatch")
    if manifest["primary_writer"] != EXPECTED_WRITER:
        raise RuntimeError("primary writer revision mismatch")
    source = base / "records/eval.jsonl"
    lines = source.read_bytes().splitlines(keepends=True)
    if len(lines) != 406 or len(manifest["records"]) != 406:
        raise RuntimeError("record hash manifest length mismatch")
    for line, frozen in zip(lines, manifest["records"]):
        rec = json.loads(line)
        if rec["record_id"] != frozen["record_id"] or _digest_bytes(line) != frozen["sha256"]:
            raise RuntimeError(f"record hash mismatch: {frozen['record_id']}")
    if _digest_bytes(source.read_bytes()) != manifest["source_sha256"]:
        raise RuntimeError("record hash source mismatch")
    if (base / "FROZEN_hashes.txt").read_text() != manifest["frozen_hashes_txt"]:
        raise RuntimeError("original frozen hashes mismatch")
    # FROZEN_hashes.txt records Git blob SHA-1 IDs; also pin the checker's raw SHA-256.
    checker = (root / "prism/report/checker.py").read_bytes()
    frozen_checker = [line.split()[1] for line in manifest["frozen_hashes_txt"].splitlines()
                      if line.startswith("prism/report/checker.py ")]
    blob = hashlib.sha1(f"blob {len(checker)}\0".encode() + checker).hexdigest()
    if len(frozen_checker) != 1 or blob != frozen_checker[0] or _digest_bytes(checker) != CHECKER_SHA256:
        raise RuntimeError("checker frozen hash mismatch")
    for relative, expected_hash in BASE_SHA256.items():
        if _digest(base / relative) != expected_hash:
            raise RuntimeError(f"baseline artifact hash mismatch: {relative}")
    actual_writer = {"key": R31.PRIMARY, "id": R31.MODELS[R31.PRIMARY][0],
                     "revision": R31.MODELS[R31.PRIMARY][1]}
    meta = json.loads((base / "llm/outputs_eval.jsonl.meta.json").read_text())
    if actual_writer != EXPECTED_WRITER or (meta.get("model"), meta.get("revision"), meta.get("n")) != (
            EXPECTED_WRITER["id"], EXPECTED_WRITER["revision"], 406):
        raise RuntimeError("baseline writer revision or batch count mismatch")
    ids = [entry["record_id"] for entry in manifest["records"]]
    outputs = _jsonl(base / "llm/outputs_eval.jsonl")
    if len(outputs) != 406 or [o["id"] for o in outputs] != [f"eval|{rid}" for rid in ids]:
        raise RuntimeError("baseline full-arm output IDs mismatch")
    checks = pd.read_csv(base / "checks_eval.csv")
    if len(checks) != 406 or checks.scan_id.tolist() != ids or not checks["pass"].all() or not checks.parsed.all():
        raise RuntimeError("baseline full-arm 406/406 parsed/pass mismatch")
    if int(checks.card_tier_required.sum()) != 220 or int(
            (checks.card_tier_required & checks.card_tier_stated).sum()) != 220:
        raise RuntimeError("baseline required tiers 220/220 mismatch")
    summary = pd.read_csv(base / "summary_eval.csv").set_index("cohort")
    if any(int(summary.loc[c, "n"]) != n or int(summary.loc[c, "pass"]) != n
           for c, n in {"all": 406, **EXPECTED_COHORTS}.items()):
        raise RuntimeError("baseline full-arm summary mismatch")
    stress = pd.read_csv(base / "stress.csv")
    stress_summary = pd.read_csv(base / "summary_stress.csv")
    total = stress_summary.set_index("kind").loc["total"]
    if len(stress) != 30 or int(stress.follows.sum()) != 28 or int(stress.check_pass.sum()) != 30 or (
            int(total["n"]), int(total["follows"]), int(total["check_pass"])) != (30, 28, 30):
        raise RuntimeError("baseline formal perturbation follows 28/30 mismatch")
    lock = (Path(output_root) if output_root is not None else root / OUT.relative_to(REPO)) / "provenance.json"
    if lock.exists():
        try:
            hashes = json.loads(lock.read_text())["baseline_sha256"]
        except (ValueError, KeyError, TypeError) as exc:
            raise RuntimeError("frozen provenance metadata mismatch") from exc
        for relative in BASE_FILES:
            if hashes.get(relative) != _digest(base / relative):
                raise RuntimeError(f"frozen baseline artifact hash mismatch: {relative}")
    return manifest


def _digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def freeze_step(root: Path = REPO, output_root: Path = OUT) -> dict:
    manifest = verify_v31_baseline(root, output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    lock = output_root / "provenance.json"
    if not lock.exists():
        payload = {"manifest_sha256": _digest(root / MANIFEST),
                   "baseline_sha256": {p: _digest(root / BASE / p) for p in BASE_FILES},
                   "writer": EXPECTED_WRITER, "n_records": 406}
        lock.write_text(json.dumps(payload, indent=2) + "\n")
    else:
        existing = json.loads(lock.read_text())
        if existing.get("manifest_sha256") != _digest(root / MANIFEST) or existing.get("writer") != EXPECTED_WRITER:
            raise RuntimeError("frozen manifest or writer mismatch")
    return manifest


def _guard(root: Path, output_root: Path) -> dict:
    if not (output_root / "provenance.json").exists():
        raise RuntimeError("run freeze before later ablation steps")
    manifest = verify_v31_baseline(root, output_root)
    lock = json.loads((output_root / "provenance.json").read_text())
    if lock.get("manifest_sha256") != _digest(root / MANIFEST) or lock.get("writer") != EXPECTED_WRITER:
        raise RuntimeError("frozen manifest or writer mismatch")
    return manifest


def _records(root: Path) -> dict[str, dict]:
    rows = _jsonl(root / BASE / "records/eval.jsonl")
    return {row["record_id"]: row for row in rows}


def _request_path(output_root: Path, arm: str) -> Path:
    return output_root / "llm" / f"requests_{arm}.jsonl"


def _output_path(output_root: Path, arm: str) -> Path:
    return output_root / "llm" / f"outputs_{arm}.jsonl"


def requests_step(root: Path = REPO, output_root: Path = OUT) -> None:
    manifest = _guard(root, output_root)
    (output_root / "llm").mkdir(parents=True, exist_ok=True)
    full = (root / BASE / "llm/requests_eval.jsonl").read_bytes()
    full_path = _request_path(output_root, A.FULL_EVIDENCE)
    if full_path.exists() and full_path.read_bytes() != full:
        raise RuntimeError("frozen full-evidence request mismatch")
    full_path.write_bytes(full)
    records = _records(root)
    facts_rows = []
    for item in manifest["records"]:
        rid = item["record_id"]
        facts = A.facts_for_arm(records[rid], A.FACTS_ONLY)
        facts_rows.append({"id": f"eval|{rid}", "messages": A.facts_only_messages(facts),
                           "max_tokens": 2048, "schema": A.FACTS_SCHEMA})
    # Full arm requests are the immutable v3.1 requests, whose prompt schema is deliberately different.
    if [r["id"] for r in _jsonl(full_path)] != [r["id"] for r in facts_rows]:
        raise RuntimeError("paired request IDs or order mismatch")
    path = _request_path(output_root, A.FACTS_ONLY)
    data = "".join(json.dumps(row) + "\n" for row in facts_rows).encode()
    if path.exists() and path.read_bytes() != data:
        raise RuntimeError("frozen facts-only request mismatch")
    path.write_bytes(data)
    hashes = {arm: _digest(_request_path(output_root, arm)) for arm in ARMS}
    frozen = output_root / "request_hashes.json"
    if frozen.exists() and json.loads(frozen.read_text()) != hashes:
        raise RuntimeError("frozen request hash mismatch")
    frozen.write_text(json.dumps(hashes, indent=2) + "\n")


def _guard_requests(root: Path, output_root: Path) -> None:
    _guard(root, output_root)
    frozen = output_root / "request_hashes.json"
    if not frozen.exists():
        raise RuntimeError("run requests before generation or evaluation")
    hashes = json.loads(frozen.read_text())
    for arm in ARMS:
        path = _request_path(output_root, arm)
        if not path.exists() or hashes.get(arm) != _digest(path):
            raise RuntimeError(f"frozen request hash mismatch: {arm}")


def generate_step(root: Path = REPO, output_root: Path = OUT) -> None:
    _guard_requests(root, output_root)
    baseline = root / BASE / "llm/outputs_eval.jsonl"
    full = _output_path(output_root, A.FULL_EVIDENCE)
    if full.exists() and _digest(full) != _digest(baseline):
        raise RuntimeError("imported full-arm output hash mismatch")
    if not full.exists():
        shutil.copyfile(baseline, full)
    source_meta = Path(str(baseline) + ".meta.json")
    dest_meta = Path(str(full) + ".meta.json")
    if dest_meta.exists() and _digest(dest_meta) != _digest(source_meta):
        raise RuntimeError("imported full-arm metadata hash mismatch")
    if not dest_meta.exists():
        shutil.copyfile(source_meta, dest_meta)
    target = _output_path(output_root, A.FACTS_ONLY)
    if target.exists():
        return
    mid, revision, chat_kwargs, extra = R31.MODELS[R31.PRIMARY]
    for attempt in (1, 2):
        _guard_requests(root, output_root)
        attempt_path = target.with_name(f"{target.stem}_attempt{attempt}{target.suffix}")
        if attempt_path.exists() or attempt_path.with_suffix(".log").exists():
            raise RuntimeError(f"attempt artifact already exists: {attempt_path}")
        cmd = [str(Path(R3.LLM_ENV) / "bin/python"), "-m", "prism.report.vllm_run",
               "--model", mid, "--revision", revision,
               "--requests", str(_request_path(output_root, A.FACTS_ONLY)),
               "--out", str(attempt_path), "--tp", "1", "--chat-kwargs", json.dumps(chat_kwargs),
               "--max-model-len", "8192", "--gpu-mem", "0.90", *extra]
        env = {**os.environ, "PYTHONPATH": str(root), "HF_HUB_OFFLINE": "1",
               "TRANSFORMERS_OFFLINE": "1", "VLLM_NO_USAGE_STATS": "1", "DO_NOT_TRACK": "1"}
        log = attempt_path.with_suffix(".log")
        with log.open("w") as stdout:
            try:
                returncode = subprocess.run(cmd, cwd=root, env=env, stdout=stdout,
                                            stderr=subprocess.STDOUT, check=False).returncode
            except OSError as exc:
                stdout.write(f"Runner could not start: {exc}\n")
                returncode = None
        meta = Path(str(attempt_path) + ".meta.json")
        if returncode == 0 and attempt_path.exists() and meta.exists():
            shutil.copyfile(attempt_path, target)
            shutil.copyfile(meta, Path(str(target) + ".meta.json"))
            return
        if not meta.exists():
            meta.write_text(json.dumps({"attempt": attempt, "returncode": returncode,
                                        "request_sha256": _digest(_request_path(output_root, A.FACTS_ONLY)),
                                        "complete": False}, indent=2) + "\n")
    raise RuntimeError("facts-only whole-batch generation failed twice; attempt artifacts retained")


def _output_map(path: Path, expected: set[str]) -> dict[str, dict]:
    if not path.exists():
        return {}
    rows = _jsonl(path)
    ids = [r["id"] for r in rows]
    if len(ids) != len(set(ids)) or not set(ids) <= expected:
        raise RuntimeError(f"duplicate or unexpected output ID in {path}")
    return dict(zip(ids, rows))


def _facts_row(rid: str, rec: dict, out: dict | None) -> dict:
    facts = A.facts_for_arm(rec, A.FACTS_ONLY)
    claims = A.parse_facts_only(out["text"]) if out else None
    result = A.check_facts_only(claims, facts)
    parsed = bool(result["parsed"])
    truncated = bool(out and out.get("finish_reason") == "length")
    model_leak = bool(result.get("banned_terms") or result.get("clinical_inference") or
                      (out and A._BANNED.search(out.get("text", ""))))
    word_text = " ".join(c["text"] for c in claims) if claims else (out.get("text", "") if out else "")
    return {"scan_id": rid, "cohort": rec["cohort"], "patient_id": rec["patient_id"],
            "pass": bool(result["pass"]) and not truncated, "parsed": parsed,
            "missing_output": out is None, "finish_reason": out.get("finish_reason") if out else None,
            "required_content_pass": bool(result.get("required", {}).get("required_pass")),
            "model_leak": model_leak, "words": len(word_text.split()),
            "n_prompt_tokens": out.get("n_prompt_tokens") if out else None,
            "n_output_tokens": out.get("n_output_tokens") if out else None,
            "fail_invalid_citation": bool(result.get("n_invalid_citations")),
            "fail_unsupported": bool(result.get("unsupported") or result.get("semantic_mismatch")),
            "fail_forbidden": bool(result.get("forbidden") and any(result["forbidden"].values())),
            "fail_required_missing": not bool(result.get("required", {}).get("required_pass")),
            "fail_model_leak": model_leak}


def summarise_arm(rows: list[dict] | pd.DataFrame, meta: dict | None = None,
                  gpu_hour_price_usd: float | None = None) -> pd.DataFrame:
    frame = pd.DataFrame(rows)
    meta = meta or {}
    groups = [("all", frame), *list(frame.groupby("cohort", sort=True))]
    result = []
    for cohort, group in groups:
        n = len(group)
        passed = int(group["pass"].sum())
        low, high = R3.wilson(passed, n)
        row = {"cohort": cohort, "n": n, "pass": passed, "failed": n - passed,
               "pass_rate": passed / n,
               "pass_ci_low": low, "pass_ci_high": high,
               "parsed": int(group.parsed.sum()), "unparsed": n - int(group.parsed.sum()),
               "missing_output": int(group.missing_output.sum()),
               "truncated": int((group.finish_reason == "length").sum()),
               "required_content_pass": int(group.required_content_pass.sum()),
               "model_leak": int(group.model_leak.sum()),
               "words_median": float(group.words.median()), "words_mean": float(group.words.mean()),
               "prompt_tokens_total": int(pd.to_numeric(group.n_prompt_tokens, errors="coerce").sum()),
               "output_tokens_total": int(pd.to_numeric(group.n_output_tokens, errors="coerce").sum())}
        for col in group.columns:
            if col.startswith("fail_"):
                row[col] = int(group[col].sum())
        wall = meta.get("batch_wall_s")
        row["batch_wall_s"] = wall
        row["batch_s_per_request"] = meta.get("batch_s_per_request")
        row["gpu_name"] = meta.get("gpu_name")
        row["gpu_hour_price_usd"] = gpu_hour_price_usd
        row["estimated_batch_cost_usd"] = (wall / 3600 * gpu_hour_price_usd
                                            if wall is not None and gpu_hour_price_usd is not None else None)
        result.append(row)
    return pd.DataFrame(result)


def paired_rows(records: dict[str, dict], full: dict[str, dict], facts_only: dict[str, dict]) -> pd.DataFrame:
    rows = []
    for rid, rec in records.items():
        row = {"scan_id": rid, "cohort": rec["cohort"], "patient_id": rec["patient_id"]}
        for arm, lookup in ((A.FULL_EVIDENCE, full), (A.FACTS_ONLY, facts_only)):
            item = lookup.get(rid) or {}
            row[f"{arm}_missing_output"] = bool(item.get("missing_output", not bool(item)))
            for key in ("pass", "parsed", "required_content_pass"):
                row[f"{arm}_{key}"] = bool(item.get(key, False)) and not row[f"{arm}_missing_output"]
        rows.append(row)
    return pd.DataFrame(rows)


def _cluster_ci(frame: pd.DataFrame, outcome: str, seed: int = 20261026, draws: int = 2000) -> tuple[float, float]:
    delta = (frame[f"{A.FULL_EVIDENCE}_{outcome}"].astype(int) -
             frame[f"{A.FACTS_ONLY}_{outcome}"].astype(int)).to_numpy()
    patients = (frame.cohort.astype(str) + "|" + frame.patient_id.astype(str)).to_numpy()
    clusters = [np.flatnonzero(patients == pid) for pid in sorted(set(patients))]
    rng = np.random.default_rng(seed)
    sampled = np.empty(draws)
    for i in range(draws):
        indices = np.concatenate([clusters[j] for j in rng.integers(0, len(clusters), len(clusters))])
        sampled[i] = delta[indices].mean()
    return tuple(np.quantile(sampled, [0.025, 0.975]))


def paired_summary(paired: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for cohort, group in [("all", paired), *list(paired.groupby("cohort", sort=True))]:
        row = {"cohort": cohort, "n": len(group),
               "n_patients": (group.cohort.astype(str) + "|" + group.patient_id.astype(str)).nunique()}
        for outcome in ("pass", "parsed", "required_content_pass"):
            full = group[f"{A.FULL_EVIDENCE}_{outcome}"].astype(int)
            facts = group[f"{A.FACTS_ONLY}_{outcome}"].astype(int)
            low, high = _cluster_ci(group, outcome)
            row.update({f"{outcome}_full": int(full.sum()), f"{outcome}_facts_only": int(facts.sum()),
                        f"{outcome}_difference_full_minus_facts_only": float((full - facts).mean()),
                        f"{outcome}_difference_ci_low": low, f"{outcome}_difference_ci_high": high})
        rows.append(row)
    return pd.DataFrame(rows)


def evaluate_step(root: Path = REPO, output_root: Path = OUT,
                  gpu_hour_price_usd: float | None = None) -> None:
    _guard_requests(root, output_root)
    records = _records(root)
    expected = {f"eval|{rid}" for rid in records}
    full_path = _output_path(output_root, A.FULL_EVIDENCE)
    if not full_path.exists() or _digest(full_path) != _digest(root / BASE / "llm/outputs_eval.jsonl"):
        raise RuntimeError("imported full-arm output hash mismatch")
    full_outputs = _output_map(full_path, expected)
    facts_outputs = _output_map(_output_path(output_root, A.FACTS_ONLY), expected)
    baseline_checks = pd.read_csv(root / BASE / "checks_eval.csv").set_index("scan_id")
    full_rows, facts_rows = [], []
    for rid, rec in records.items():
        output = full_outputs.get(f"eval|{rid}")
        row = baseline_checks.loc[rid].to_dict()
        row.update({"scan_id": rid, "patient_id": rec["patient_id"], "missing_output": output is None,
                    "required_content_pass": not bool(row["fail_required_missing"]), "model_leak": False,
                    "n_prompt_tokens": output.get("n_prompt_tokens") if output else None})
        if output is None:
            row.update({"pass": False, "parsed": False, "required_content_pass": False})
        full_rows.append(row)
        facts_rows.append(_facts_row(rid, rec, facts_outputs.get(f"eval|{rid}")))
    frames = {A.FULL_EVIDENCE: pd.DataFrame(full_rows), A.FACTS_ONLY: pd.DataFrame(facts_rows)}
    for arm, frame in frames.items():
        frame.to_csv(output_root / f"checks_{arm}.csv", index=False)
        meta_path = Path(str(_output_path(output_root, arm)) + ".meta.json")
        meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
        summarise_arm(frame, meta, gpu_hour_price_usd).to_csv(output_root / f"summary_{arm}.csv", index=False)
    paired = paired_rows(records, {r["scan_id"]: r for r in full_rows},
                         {r["scan_id"]: r for r in facts_rows})
    paired.to_csv(output_root / "paired_rows.csv", index=False)
    paired_summary(paired).to_csv(output_root / "paired_summary.csv", index=False)


def render_step(root: Path = REPO, output_root: Path = OUT) -> None:
    _guard_requests(root, output_root)
    from prism.report import prompts_v3_1, sections_v3

    records = _records(root)
    expected = {f"eval|{rid}" for rid in records}
    for arm in ARMS:
        checks_path = output_root / f"checks_{arm}.csv"
        if not checks_path.exists():
            raise RuntimeError("run evaluate before render")
        checks = pd.read_csv(checks_path).set_index("scan_id")
        outputs = _output_map(_output_path(output_root, arm), expected)
        directory = output_root / "reports" / arm
        directory.mkdir(parents=True, exist_ok=True)
        for rid, rec in records.items():
            facts = A.facts_for_arm(rec, arm)
            output = outputs.get(f"eval|{rid}")
            if arm == A.FULL_EVIDENCE:
                prose = prompts_v3_1.sectioned(output["text"]) if output else None
                report = sections_v3.render_md(rec["scan_id"], facts, prose)
            else:
                claims = A.parse_facts_only(output["text"]) if output and bool(checks.loc[rid, "pass"]) else None
                report = A.render_facts_only(rec["scan_id"], facts, claims)
            (directory / f"{rid.replace('|', '__')}.md").write_text(report)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--steps", nargs="+", choices=("freeze", "requests", "generate", "evaluate", "render"),
                        required=True)
    parser.add_argument("--gpu-hour-price-usd", type=float, default=None,
                        help="optional local GPU hourly price for cost estimate")
    args = parser.parse_args(argv)
    for step in args.steps:
        if step == "freeze":
            freeze_step()
        elif step == "requests":
            requests_step()
        elif step == "generate":
            generate_step()
        elif step == "evaluate":
            evaluate_step(gpu_hour_price_usd=args.gpu_hour_price_usd)
        else:
            render_step()
        print(f"{step}: complete", flush=True)


if __name__ == "__main__":
    main()
