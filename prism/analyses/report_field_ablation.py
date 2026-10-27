"""Local paired report-field ablation on the immutable v3.1 evaluation set.

Run ``python -m prism.analyses.report_field_ablation --steps freeze stress requests generate evaluate
evaluate-stress render --sets eval stress``. The full arm imports v3.1 output (and its immutable 30-record
perturbation result); only the facts-only arm invokes the local writer, on the eval set and on its own fixed
shared-fact stress set.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import time
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
SETS = ("eval", "stress")
# Perturbation contract (docs/results/REPORT_FIELD_ABLATION_PLAN.md, "Perturbation contract").
STRESS_KIND = "enhancing_volume_change"
V31_SHARED_KIND = "et_change"  # the same shared-field change, as named in the immutable v3.1 set
STRESS_SEED = 20261026
STRESS_N = 6
STRESS_RECORDS = Path("records/stress_shared.jsonl")
STRESS_LOG = Path("stress_log.csv")
STRESS_HASHES = Path("stress_hashes.json")
STRESS_REQUEST_HASHES = Path("stress_request_hashes.json")
STATEMENT_KEY = "meas.enhancing_change_since_previous_statement"
CHANGED_PREFIX = "meas.enhancing_change_since_previous_"
V31_RULE = "v3 S7 follows rule; immutable v3.1 formal result, not regenerated"
FACTS_RULE = "facts-only shared-field follows; ambiguous old value unscorable"


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


def _request_path(output_root: Path, arm: str, set_name: str = "eval") -> Path:
    return output_root / "llm" / f"requests_{'' if set_name == 'eval' else set_name + '_'}{arm}.jsonl"


def _output_path(output_root: Path, arm: str, set_name: str = "eval") -> Path:
    return output_root / "llm" / f"outputs_{'' if set_name == 'eval' else set_name + '_'}{arm}.jsonl"


# ---------------------------------------------------------------- perturbation contract
def eligible_kinds(arm: str) -> tuple[str, ...]:
    """Perturbation kinds reported per arm: model-only v3.1 kinds exist only for the full arm."""
    if arm == A.FULL_EVIDENCE:
        return tuple(R3.KINDS)
    if arm == A.FACTS_ONLY:
        return (STRESS_KIND,)
    raise ValueError(f"unknown report field arm: {arm}")


def _shared_updates(old: dict, new: dict) -> dict:
    return {key: [old.get(key), new.get(key)] for key in sorted(set(old) | set(new)) if old.get(key) != new.get(key)}


def shared_stress_records(records: list[dict], seed: int = STRESS_SEED, n: int = STRESS_N) -> list[dict]:
    """The fixed facts-only shared-fact perturbation set, sampled in source order with ``seed``.

    Each perturbation is the v3 ``et_change`` edit (the previous scan's enhancing volume moves so the change becomes
    -5 cc, or +5 cc when it was negative). A record is eligible when it has a previous scan and an enhancing volume
    and the edit changes the shared enhancing change statement; the expected shared-fact updates are recorded."""
    pool = []
    for rec in records:
        if not (rec.get("measurements") or {}).get("previous") or not R3._eligible(V31_SHARED_KIND, rec):
            continue
        perturbed, log = R3.perturb_one(V31_SHARED_KIND, rec)
        old, new = A.facts_for_arm(rec, A.FACTS_ONLY), A.facts_for_arm(perturbed, A.FACTS_ONLY)
        updates = _shared_updates(old, new)
        if STATEMENT_KEY not in updates:
            continue
        if any(not key.startswith(CHANGED_PREFIX) for key in updates):
            raise RuntimeError(f"perturbation changed an unexpected shared field: {rec['record_id']}")
        perturbed["record_id"] = f"{rec['record_id']}|perturbed:{STRESS_KIND}"
        pool.append({"record_id": rec["record_id"], "perturbed_id": perturbed["record_id"], "kind": STRESS_KIND,
                     "cohort": rec["cohort"], "patient_id": rec.get("patient_id"), "old": log["old"],
                     "new": log["new"], "old_statement": old[STATEMENT_KEY], "new_statement": new[STATEMENT_KEY],
                     "expected_updates": updates, "seed": seed, "record": perturbed})
    rng = np.random.default_rng(seed)
    return [pool[i] for i in sorted(rng.choice(len(pool), min(n, len(pool)), replace=False))]


def _numeric_values(facts: dict) -> list[float]:
    return [x for value in facts.values() for x in A.checker._field_numbers(value)]


def facts_only_follows(entry: dict, old: dict, new: dict, claims: list[dict] | None) -> dict:
    """Facts-only follows: the new shared statement is supported, the old statement is absent, and no written number
    equals an old changed value unless that number is also a legitimate value of the perturbed facts (unscorable)."""
    if claims is None:
        return {"status": "failed", "follows": False, "new_supported": False, "old_present": False,
                "old_unique_hits": [], "old_ambiguous_hits": []}
    text = " ".join(c["text"] for c in claims)
    new_supported = any(STATEMENT_KEY in c.get("fields", []) and A._contains_field_value(c, STATEMENT_KEY, new)
                        for c in claims)
    old_present = old[STATEMENT_KEY].casefold().strip().rstrip(".") in text.casefold()
    old_values = [abs(float(before)) for key, (before, _after) in entry["expected_updates"].items()
                  if isinstance(before, (int, float)) and not isinstance(before, bool)]
    new_values = _numeric_values(new)
    hits = [n for n in A.checker.numbers(text) if A.checker.matches(n, old_values, False)]
    ambiguous = [n for n in hits if A.checker.matches(n, new_values, False)]
    unique = [n for n in hits if n not in ambiguous]
    if not new_supported or old_present or unique:
        status, follows = "not_follows", False
    elif ambiguous:
        status, follows = "unscorable", None
    else:
        status, follows = "follows", True
    return {"status": status, "follows": follows, "new_supported": new_supported, "old_present": old_present,
            "old_unique_hits": unique, "old_ambiguous_hits": ambiguous}


def summarise_stress(frame: pd.DataFrame, rule: str) -> pd.DataFrame:
    """Per kind and total, with unscorable and failed rows kept in every denominator."""
    rows = []
    for kind, group in [*list(frame.groupby("kind", sort=True)), ("total", frame)]:
        n = len(group)
        follows = int((group.status == "follows").sum())
        unscorable = int((group.status == "unscorable").sum())
        rows.append({"kind": kind, "n": n, "follows": follows,
                     "not_follows": int((group.status == "not_follows").sum()), "unscorable": unscorable,
                     "failed_output": int((group.status == "failed").sum()), "n_scorable": n - unscorable,
                     "follows_rate_all": follows / n if n else None,
                     "follows_rate_scorable": follows / (n - unscorable) if n - unscorable else None,
                     "check_pass": int(group.check_pass.astype(bool).sum()),
                     "follows_and_pass": int(group.follows_and_pass.astype(bool).sum()), "rule": rule})
    return pd.DataFrame(rows)


def _stress_paths(output_root: Path) -> tuple[Path, Path, Path]:
    return output_root / STRESS_RECORDS, output_root / STRESS_LOG, output_root / STRESS_HASHES


def stress_step(root: Path = REPO, output_root: Path = OUT) -> list[dict] | None:
    """Write the fixed facts-only stress set once; an existing set is never resampled or overwritten."""
    _guard(root, output_root)
    records_path, log_path, hashes_path = _stress_paths(output_root)
    if records_path.exists() and log_path.exists():
        _guard_stress(root, output_root)
        print(f"{records_path} exists; the perturbation set is fixed, not redone", flush=True)
        return None
    if records_path.exists() or log_path.exists() or hashes_path.exists():
        raise RuntimeError("partial stress set present; refusing to overwrite the fixed perturbation set")
    entries = shared_stress_records(list(_records(root).values()))
    records_path.parent.mkdir(parents=True, exist_ok=True)
    records_path.write_text("".join(json.dumps(e["record"]) + "\n" for e in entries))
    log = pd.DataFrame([{**{k: v for k, v in e.items() if k != "record"},
                         "expected_updates": json.dumps(e["expected_updates"])} for e in entries])
    log.to_csv(log_path, index=False)
    hashes_path.write_text(json.dumps({str(STRESS_RECORDS): _digest(records_path),
                                       str(STRESS_LOG): _digest(log_path)}, indent=2) + "\n")
    print(f"stress: {len(entries)} {STRESS_KIND} perturbations (seed {STRESS_SEED})", flush=True)
    return entries


def _guard_stress(root: Path, output_root: Path) -> None:
    _guard(root, output_root)
    records_path, log_path, hashes_path = _stress_paths(output_root)
    if not hashes_path.exists():
        raise RuntimeError("run stress before stress requests, generation or evaluation")
    hashes = json.loads(hashes_path.read_text())
    for relative, path in ((STRESS_RECORDS, records_path), (STRESS_LOG, log_path)):
        if not path.exists() or hashes.get(str(relative)) != _digest(path):
            raise RuntimeError(f"frozen stress set hash mismatch: {relative}")


def _stress_entries(root: Path, output_root: Path) -> list[dict]:
    """Stress log rows with their perturbed records; expected updates are re-derived and must match exactly."""
    records_path, log_path, _ = _stress_paths(output_root)
    perturbed = {r["record_id"]: r for r in _jsonl(records_path)}
    log = pd.read_csv(log_path, dtype={"record_id": str, "perturbed_id": str})
    if sorted(log.perturbed_id) != sorted(perturbed):
        raise RuntimeError("stress log and stress records mismatch")
    source = _records(root)
    entries = []
    for row in log.to_dict("records"):
        row["expected_updates"] = json.loads(row["expected_updates"])
        rec = perturbed[row["perturbed_id"]]
        old = A.facts_for_arm(source[row["record_id"]], A.FACTS_ONLY)
        new = A.facts_for_arm(rec, A.FACTS_ONLY)
        if _shared_updates(old, new) != row["expected_updates"]:
            raise RuntimeError(f"stress expected field updates mismatch: {row['perturbed_id']}")
        entries.append({**row, "record": rec, "old_facts": old, "new_facts": new})
    return entries


def _stress_requests(root: Path, output_root: Path) -> None:
    _guard_stress(root, output_root)
    (output_root / "llm").mkdir(parents=True, exist_ok=True)
    rows = [{"id": f"stress|{e['perturbed_id']}", "messages": A.facts_only_messages(e["new_facts"]),
             "max_tokens": 2048, "schema": A.FACTS_SCHEMA} for e in _stress_entries(root, output_root)]
    path = _request_path(output_root, A.FACTS_ONLY, "stress")
    data = "".join(json.dumps(row) + "\n" for row in rows).encode()
    if path.exists() and path.read_bytes() != data:
        raise RuntimeError("frozen facts-only stress request mismatch")
    path.write_bytes(data)
    frozen = output_root / STRESS_REQUEST_HASHES
    hashes = {A.FACTS_ONLY: _digest(path)}
    if frozen.exists() and json.loads(frozen.read_text()) != hashes:
        raise RuntimeError("frozen stress request hash mismatch")
    frozen.write_text(json.dumps(hashes, indent=2) + "\n")


def _guard_stress_requests(root: Path, output_root: Path) -> None:
    _guard_stress(root, output_root)
    frozen = output_root / STRESS_REQUEST_HASHES
    path = _request_path(output_root, A.FACTS_ONLY, "stress")
    if not frozen.exists():
        raise RuntimeError("run requests --sets stress before stress generation or evaluation")
    if not path.exists() or json.loads(frozen.read_text()).get(A.FACTS_ONLY) != _digest(path):
        raise RuntimeError("frozen stress request hash mismatch: facts_only")


def requests_step(root: Path = REPO, output_root: Path = OUT, set_name: str = "eval") -> None:
    if set_name == "stress":
        return _stress_requests(root, output_root)
    if set_name != "eval":
        raise ValueError(f"unknown set: {set_name}")
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


def generate_step(root: Path = REPO, output_root: Path = OUT, set_name: str = "eval") -> dict | None:
    if set_name == "stress":
        # Only the facts-only arm is generated for its stress set; the full arm keeps the v3.1 result.
        _guard_stress_requests(root, output_root)
        target = _output_path(output_root, A.FACTS_ONLY, "stress")
        if target.exists():
            return None
        return _whole_batch(root, _request_path(output_root, A.FACTS_ONLY, "stress"), target,
                            lambda: _guard_stress_requests(root, output_root))
    if set_name != "eval":
        raise ValueError(f"unknown set: {set_name}")
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
        return None
    return _whole_batch(root, _request_path(output_root, A.FACTS_ONLY), target,
                        lambda: _guard_requests(root, output_root))


def _whole_batch(root: Path, request: Path, target: Path, guard) -> dict:
    """One local whole-batch run of the facts-only writer, with at most one identical whole-batch retry."""
    mid, revision, chat_kwargs, extra = R31.MODELS[R31.PRIMARY]
    request_sha256 = _digest(request)
    attempts = []
    for attempt in (1, 2):
        guard()
        attempt_path = target.with_name(f"{target.stem}_attempt{attempt}{target.suffix}")
        if attempt_path.exists() or attempt_path.with_suffix(".log").exists():
            raise RuntimeError(f"attempt artifact already exists: {attempt_path}")
        cmd = [str(Path(R3.LLM_ENV) / "bin/python"), "-m", "prism.report.vllm_run",
               "--model", mid, "--revision", revision,
               "--requests", str(request),
               "--out", str(attempt_path), "--tp", "1", "--chat-kwargs", json.dumps(chat_kwargs),
               "--max-model-len", "8192", "--gpu-mem", "0.90", *extra]
        env = {**os.environ, "PYTHONPATH": str(root), "HF_HUB_OFFLINE": "1",
               "TRANSFORMERS_OFFLINE": "1", "VLLM_NO_USAGE_STATS": "1", "DO_NOT_TRACK": "1"}
        log = attempt_path.with_suffix(".log")
        with log.open("w") as stdout:
            started = time.monotonic()
            try:
                returncode = subprocess.run(cmd, cwd=root, env=env, stdout=stdout,
                                            stderr=subprocess.STDOUT, check=False).returncode
            except OSError as exc:
                stdout.write(f"Runner could not start: {exc}\n")
                returncode = None
            process_wall_s = time.monotonic() - started
        meta_path = Path(str(attempt_path) + ".meta.json")
        complete = returncode == 0 and attempt_path.exists() and meta_path.exists()
        # The runner's meta covers only its generation call; the process wall time includes model load.
        try:
            meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
        except ValueError:
            meta = {}
        meta.update({"attempt": attempt, "returncode": returncode, "request_sha256": request_sha256,
                     "complete": complete, "process_wall_s": process_wall_s})
        meta_path.write_text(json.dumps(meta, indent=2) + "\n")
        attempts.append({key: meta.get(key) for key in
                         ("attempt", "returncode", "complete", "process_wall_s", "batch_wall_s")})
        if complete:
            shutil.copyfile(attempt_path, target)
            break
    final = dict(meta) if attempts[-1]["complete"] else {"request_sha256": request_sha256, "complete": False}
    for key in ("attempt", "returncode", "process_wall_s"):
        final.pop(key, None)
    final.update({"attempts": attempts, "n_attempts": len(attempts),
                  "total_process_wall_s": sum(a["process_wall_s"] for a in attempts),
                  "total_batch_wall_s": sum(a["batch_wall_s"] or 0 for a in attempts)})
    if not final["complete"]:
        # A failed whole batch has no final output: every record is counted as a failure by evaluate.
        target.write_text("")
    Path(str(target) + ".meta.json").write_text(json.dumps(final, indent=2) + "\n")
    return final


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
        attempts = meta.get("attempts") or []
        # Runtime and cost sum every whole-batch attempt, including a failed first attempt.
        wall = meta.get("total_process_wall_s", meta.get("batch_wall_s"))
        row["batch_complete"] = meta.get("complete", bool(meta))
        row["n_attempts"] = meta.get("n_attempts", 1 if meta else 0)
        row["batch_wall_s"] = meta.get("batch_wall_s")
        row["total_batch_wall_s"] = meta.get("total_batch_wall_s", meta.get("batch_wall_s"))
        row["total_process_wall_s"] = meta.get("total_process_wall_s")
        row["attempt_process_wall_s"] = json.dumps([a.get("process_wall_s") for a in attempts])
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


def evaluate_stress_step(root: Path = REPO, output_root: Path = OUT) -> None:
    """Score the facts-only stress set; report the immutable v3.1 full-arm result separately (read only)."""
    _guard_stress_requests(root, output_root)
    full = pd.read_csv(root / BASE / "stress.csv")
    full["status"] = np.where(full.follows.astype(bool), "follows", "not_follows")
    full["rule"] = V31_RULE
    full.to_csv(output_root / f"stress_{A.FULL_EVIDENCE}.csv", index=False)
    summarise_stress(full, V31_RULE).to_csv(output_root / f"summary_stress_{A.FULL_EVIDENCE}.csv", index=False)
    entries = _stress_entries(root, output_root)
    outputs = _output_map(_output_path(output_root, A.FACTS_ONLY, "stress"),
                          {f"stress|{e['perturbed_id']}" for e in entries})
    rows = []
    for entry in entries:
        out = outputs.get(f"stress|{entry['perturbed_id']}")
        claims = A.parse_facts_only(out["text"]) if out else None
        check = A.check_facts_only(claims, entry["new_facts"])
        truncated = bool(out and out.get("finish_reason") == "length")
        result = facts_only_follows(entry, entry["old_facts"], entry["new_facts"], claims)
        check_pass = bool(check["pass"]) and not truncated
        rows.append({"perturbed_id": entry["perturbed_id"], "record_id": entry["record_id"],
                     "cohort": entry["cohort"], "patient_id": entry["patient_id"], "kind": entry["kind"],
                     "old": entry["old"], "new": entry["new"], "status": result["status"],
                     "follows": result["follows"], "new_supported": result["new_supported"],
                     "old_present": result["old_present"],
                     "old_unique_hits": json.dumps(result["old_unique_hits"]),
                     "old_ambiguous_hits": json.dumps(result["old_ambiguous_hits"]),
                     "missing_output": out is None, "parsed": bool(check["parsed"]),
                     "finish_reason": out.get("finish_reason") if out else None, "check_pass": check_pass,
                     "follows_and_pass": result["follows"] is True and check_pass, "rule": FACTS_RULE})
    frame = pd.DataFrame(rows)
    frame.to_csv(output_root / f"stress_{A.FACTS_ONLY}.csv", index=False)
    summarise_stress(frame, FACTS_RULE).to_csv(output_root / f"summary_stress_{A.FACTS_ONLY}.csv", index=False)


def render_report(arm: str, rec: dict, output: dict | None, passed: bool) -> str:
    """Markdown for one record: the full arm uses the v3.1 canonical renderer unchanged; facts-only prose is shown
    only when its checker passed, and the facts-only renderer has no model-derived sections or tables."""
    from prism.report import prompts_v3_1, sections_v3

    facts = A.facts_for_arm(rec, arm)
    if arm == A.FULL_EVIDENCE:
        prose = prompts_v3_1.sectioned(output["text"]) if output else None
        return sections_v3.render_md(rec["scan_id"], facts, prose)
    claims = A.parse_facts_only(output["text"]) if output and passed else None
    return A.render_facts_only(rec["scan_id"], facts, claims)


def render_step(root: Path = REPO, output_root: Path = OUT) -> None:
    _guard_requests(root, output_root)
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
            report = render_report(arm, rec, outputs.get(f"eval|{rid}"), bool(checks.loc[rid, "pass"]))
            (directory / f"{rid.replace('|', '__')}.md").write_text(report)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--steps", nargs="+", required=True,
                        choices=("freeze", "stress", "requests", "generate", "evaluate", "evaluate-stress", "render"))
    parser.add_argument("--sets", nargs="+", choices=SETS, default=["eval"],
                        help="sets for requests and generate (stress: facts-only shared-fact perturbations)")
    parser.add_argument("--gpu-hour-price-usd", type=float, default=None,
                        help="optional local GPU hourly price for cost estimate")
    args = parser.parse_args(argv)
    for step in args.steps:
        if step == "freeze":
            freeze_step()
        elif step == "stress":
            stress_step()
        elif step == "requests":
            for set_name in args.sets:
                requests_step(set_name=set_name)
        elif step == "generate":
            for set_name in args.sets:
                final = generate_step(set_name=set_name)
                if final is not None and not final["complete"]:
                    print(f"generate: facts-only {set_name} batch failed twice; records without output count as "
                          "failures", flush=True)
        elif step == "evaluate":
            evaluate_step(gpu_hour_price_usd=args.gpu_hour_price_usd)
        elif step == "evaluate-stress":
            evaluate_stress_step()
        else:
            render_step()
        print(f"{step}: complete", flush=True)


if __name__ == "__main__":
    main()
