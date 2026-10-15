"""Local LLM runner (vLLM, offline; no network calls at inference, patient data stays on the node).

Runs in the separate LLM environment (/project/community/sbandred/envs/prism-llm), not the project .venv:

    PYTHONPATH=<repo> $LLM_ENV/bin/python -m prism.report.llm --model Qwen/Qwen3.8-27B --revision <sha> \
        --requests requests.jsonl --out outputs.jsonl [--tp 4] [--latency 10]

requests.jsonl rows: {"id", "messages", "json_schema": bool, "max_tokens"}. Greedy decoding (temperature 0), seed 0,
non-thinking mode (enable_thinking=False). Rows with json_schema=true use vLLM structured outputs with
prompts.SCHEMA, which fixes the JSON shape only (field keys are free text and checked afterwards).
--latency n: additionally time n requests one at a time (single-report latency).
"""

from __future__ import annotations

import argparse
import json
import os
import time


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--revision", required=True)
    ap.add_argument("--requests", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--tp", type=int, default=1)
    ap.add_argument("--latency", type=int, default=0)
    ap.add_argument("--max-model-len", type=int, default=8192)
    a = ap.parse_args(argv)
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    import vllm
    from vllm import LLM, SamplingParams
    from vllm.sampling_params import StructuredOutputsParams
    from prism.report.prompts import SCHEMA

    rows = [json.loads(l) for l in open(a.requests)]
    llm = LLM(model=a.model, revision=a.revision, tensor_parallel_size=a.tp, seed=0, dtype="bfloat16",
              max_model_len=a.max_model_len, gpu_memory_utilization=0.85, limit_mm_per_prompt={"image": 0, "video": 0},
              enable_prefix_caching=False)

    def params(r):
        kw = {"temperature": 0.0, "max_tokens": r["max_tokens"], "seed": 0}
        if r.get("json_schema"):
            kw["structured_outputs"] = StructuredOutputsParams(json=SCHEMA)
        return SamplingParams(**kw)

    ck = {"enable_thinking": False}
    t0 = time.time()
    outs = llm.chat([r["messages"] for r in rows], [params(r) for r in rows], chat_template_kwargs=ck, use_tqdm=False)
    wall = time.time() - t0
    lat = {}
    for r in rows[:a.latency]:
        t = time.time()
        llm.chat([r["messages"]], [params(r)], chat_template_kwargs=ck, use_tqdm=False)
        lat[r["id"]] = time.time() - t
    with open(a.out, "w") as f:
        for r, o in zip(rows, outs):
            c = o.outputs[0]
            f.write(json.dumps({"id": r["id"], "text": c.text, "finish_reason": c.finish_reason,
                                "n_prompt_tokens": len(o.prompt_token_ids), "n_output_tokens": len(c.token_ids),
                                "latency_s": lat.get(r["id"])}) + "\n")
    meta = {"model": a.model, "revision": a.revision, "vllm": vllm.__version__, "tp": a.tp, "n": len(rows),
            "batch_wall_s": wall, "batch_s_per_report": wall / max(len(rows), 1),
            "single_latency_s": lat, "decoding": "greedy (temperature 0), seed 0, enable_thinking=False",
            "gpus": os.environ.get("CUDA_VISIBLE_DEVICES")}
    import torch
    meta["gpu_name"] = torch.cuda.get_device_name(0)
    json.dump(meta, open(a.out + ".meta.json", "w"), indent=1)
    print(json.dumps(meta), flush=True)


if __name__ == "__main__":
    main()
