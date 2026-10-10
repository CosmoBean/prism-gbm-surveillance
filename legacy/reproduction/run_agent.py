#!/usr/bin/env python3
"""Run glioma_agent/src/agent_pipeline.py (unmodified) with configurable inputs, then md_to_docx.

The agent hardcodes its input paths and always calls OpenAI; this overrides the paths and
skips the LLM summary when OPENAI_API_KEY is not set.
"""
from __future__ import annotations

import argparse
import os
import sys
import warnings
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "glioma_agent" / "src"))
warnings.filterwarnings("ignore")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--predictions-csv", default=str(REPO / "reproduction" / "fusion_inputs" / "train_predictions.csv"))
    parser.add_argument("--embeddings-dir", default=str(REPO / "SWIN UNetR" / "embeddings_all"))
    parser.add_argument("--fusion-model", default=str(REPO / "MLPFusion" / "best_fusion_model.pth"))
    parser.add_argument("--reports-dir", default=str(REPO / "reproduction" / "agent_reports"))
    parser.add_argument("--patient", default="PatientID_0019")
    # Shipped reports: Timepoint_5 used mgmt_status=1 (README example), Timepoint_6 used None (__main__).
    parser.add_argument("--runs", nargs="+", default=["Timepoint_5:1", "Timepoint_6:none"],
                        help="timepoint:mgmt_status pairs (mgmt_status 'none' = unknown)")
    parser.add_argument("--seed", type=int, default=0, help="Seeds SHAP sampling so reruns are repeatable")
    args = parser.parse_args()

    import numpy as np
    import torch
    import agent_pipeline as ap
    from md_to_docx import md_to_docx

    ap.LGBM_CSV = args.predictions_csv
    ap.EMB_DIR = args.embeddings_dir
    ap.MODEL_PATH = args.fusion_model
    ap.REPORTS_DIR = args.reports_dir
    os.makedirs(args.reports_dir, exist_ok=True)
    if not os.environ.get("OPENAI_API_KEY"):
        ap.generate_llm_summary = lambda report_data: "_LLM summary skipped: OPENAI_API_KEY not set._"

    for run in args.runs:
        timepoint, mgmt = run.split(":")
        np.random.seed(args.seed)
        torch.manual_seed(args.seed)
        ap.run_agent(args.patient, timepoint, mgmt_status=None if mgmt == "none" else int(mgmt))
        stem = os.path.join(args.reports_dir, f"{args.patient}_{timepoint}_report")
        md_to_docx(stem + ".md", stem + ".docx", images_dir=args.reports_dir)


if __name__ == "__main__":
    main()
