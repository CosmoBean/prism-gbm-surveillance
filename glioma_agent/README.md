# Glioma Post-Treatment Surveillance AI Agent Pipeline

## Quick Start

```bash
# 1. Install dependencies
pip install torch shap openai pandas matplotlib python-docx gdown

# 2. Set your OpenAI API key
export OPENAI_API_KEY="your-key-here"

# 3. Prepare your data
#    - Place LightGBM predictions CSV at: data/train_predictions.csv
#    - Place SWIN embeddings (.pt files) at: data/embeddings_all/
#    - Place model weights at: models/MLPFusion/best_fusion_model.pth
#    - Place fusion_mlp.py at: models/MLPFusion/fusion_mlp.py

# 4. Run the agent for a specific patient-timepoint
python src/agent_pipeline.py

# 5. (Optional) Convert report to DOCX for Google Docs
python src/md_to_docx.py
```

## Project Structure

```
glioma_agent/
├── src/
│   ├── agent_pipeline.py     # Main Agent Pipeline (all 7 steps)
│   └── md_to_docx.py         # Markdown → DOCX converter for Google Docs
├── models/
│   └── MLPFusion/
│       ├── best_fusion_model.pth   # Model weights (download from Drive)
│       └── fusion_mlp.py           # Model architecture
├── data/
│   ├── train_predictions.csv       # LightGBM upstream results
│   └── embeddings_all/             # SWIN .pt embedding files
├── reports/                        # Generated reports (Markdown + DOCX + plots)
└── README.md
```

## Report Structure (5 Sections)

| Section | Content | Key Feature |
|---|---|---|
| 1 | Fixed Metrics + Longitudinal Delta Table | Δ from Prior, Δ from Nadir, Trend Plot |
| 2 | RANO 2.0 Rule Engine | BD% change, New Lesion detection |
| 3 | Weighted Confounder Score | MGMT-aware pseudoprogression risk (0–5.5) |
| 4 | AI Interpretation (SHAP) | Clinically Validated vs Novel Signal labels |
| 5 | LLM Clinical Summary | Confidence-tiered language + RANO-AI concordance switch |

## Key Parameters

- **Fusion threshold**: `0.48` (set by model team, locked)
- **Confidence tiers**: `>0.75` = High, `0.48–0.75` = Moderate, `<0.48` = No Alert
- **Confounder max score**: `5.5` (≥3.0 = High pseudoprogression risk)
- **LLM model**: `gpt-4.1-mini`

## Calling the Agent

```python
from src.agent_pipeline import run_agent

report_path = run_agent(
    patient_id="PatientID_0019",
    timepoint="Timepoint_6",
    mgmt_status=1,               # 0=unmethylated, 1=methylated, None=unknown
    steroid_change_pct=0.0,      # % change in steroid dose
    rc_adjacent_enhancement=False
)
```
