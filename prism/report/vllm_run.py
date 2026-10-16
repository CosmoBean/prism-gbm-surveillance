"""Generic local vLLM runner for report_usefulness.py (offline; patient data stays on the node).

Like prism.report.llm (which stays as it is for the v1 run), but each request row carries its own JSON schema, so the
v1 and v2 report prompts and the judge rubric run through one code path. Runs in the separate LLM env:

    PYTHONPATH=<repo> $LLM_ENV/bin/python -m prism.report.vllm_run --model <id> --revision <sha> \
        --requests requests.jsonl --out outputs.jsonl [--tp 1] [--chat-kwargs '{"enable_thinking": false}']

requests.jsonl rows: {"id", "messages", "schema": dict | null, "max_tokens", optional "compact_json": bool (no free
whitespace in the constrained JSON), optional "regex": str (output constrained to a regular expression instead)}. Greedy decoding (temperature 0), seed 0.
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
    ap.add_argument("--max-model-len", type=int, default=8192)
    ap.add_argument("--gpu-mem", type=float, default=0.90)
    ap.add_argument("--max-num-seqs", type=int, default=256, help="<= hybrid-attention state blocks on one GPU")
    ap.add_argument("--chat-kwargs", default="{}")
    ap.add_argument("--mm-limit", default='{"image": 0, "video": 0}', help="multimodal inputs per prompt (text only)")
    a = ap.parse_args(argv)
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    import vllm
    from vllm import LLM, SamplingParams
    from vllm.sampling_params import StructuredOutputsParams

    rows = [json.loads(l) for l in open(a.requests)]
    llm = LLM(model=a.model, revision=a.revision, tensor_parallel_size=a.tp, seed=0, dtype="bfloat16",
              max_model_len=a.max_model_len, gpu_memory_utilization=a.gpu_mem, max_num_seqs=a.max_num_seqs,
              limit_mm_per_prompt=json.loads(a.mm_limit), enable_prefix_caching=False)

    def params(r):
        kw = {"temperature": 0.0, "max_tokens": r["max_tokens"], "seed": 0}
        if r.get("regex"):
            kw["structured_outputs"] = StructuredOutputsParams(regex=r["regex"])
        elif r.get("schema"):
            kw["structured_outputs"] = StructuredOutputsParams(json=r["schema"],
                                                               disable_any_whitespace=bool(r.get("compact_json")))
        return SamplingParams(**kw)

    ck = json.loads(a.chat_kwargs)
    t0 = time.time()
    outs = llm.chat([r["messages"] for r in rows], [params(r) for r in rows], chat_template_kwargs=ck, use_tqdm=False)
    wall = time.time() - t0
    with open(a.out, "w") as f:
        for r, o in zip(rows, outs):
            c = o.outputs[0]
            f.write(json.dumps({"id": r["id"], "text": c.text, "finish_reason": c.finish_reason,
                                "n_prompt_tokens": len(o.prompt_token_ids), "n_output_tokens": len(c.token_ids)}) + "\n")
    meta = {"model": a.model, "revision": a.revision, "vllm": vllm.__version__, "tp": a.tp, "max_num_seqs": a.max_num_seqs, "n": len(rows),
            "batch_wall_s": wall, "batch_s_per_request": wall / max(len(rows), 1), "chat_kwargs": ck,
            "decoding": "greedy (temperature 0), seed 0", "gpus": os.environ.get("CUDA_VISIBLE_DEVICES")}
    import torch
    meta["gpu_name"] = torch.cuda.get_device_name(0)
    json.dump(meta, open(a.out + ".meta.json", "w"), indent=1)
    print(json.dumps(meta), flush=True)


if __name__ == "__main__":
    main()
