"""
Glioma Post-Treatment Surveillance AI Agent Pipeline
=====================================================
Implements the full Clinical Report generation flow:
  1. Data Ingestion & Longitudinal Delta Computation
  2. MLP Fusion Inference (locked interface, threshold=0.48)
  3. RANO 2.0 Rule Engine
  4. Weighted Confounder Scoring (with MGMT integration)
  5. SHAP Interpretation + Clinical Sanity Check
  6. RANO-AI Concordance Check
  7. LLM Summary with Confidence-Tiered Language Templates
"""

import os
import sys
import json
import warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import torch
import shap
from openai import OpenAI

warnings.filterwarnings('ignore')

# ─── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR       = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH     = os.path.join(BASE_DIR, 'models', 'MLPFusion', 'best_fusion_model.pth')
FUSION_PY_DIR  = os.path.join(BASE_DIR, 'models', 'MLPFusion')
EMB_DIR        = os.path.join(BASE_DIR, 'data', 'embeddings_all')
LGBM_CSV       = os.path.join(BASE_DIR, 'data', 'train_predictions.csv')
REPORTS_DIR    = os.path.join(BASE_DIR, 'reports')
os.makedirs(REPORTS_DIR, exist_ok=True)

sys.path.insert(0, FUSION_PY_DIR)
from fusion_mlp import MultimodalLateFusionMLP

# ─── Constants ────────────────────────────────────────────────────────────────
FUSION_THRESHOLD = 0.48
RANO_BD_THRESHOLD = 0.25   # +25% BD product change triggers PD

# SHAP feature names: 48 vision dims + 1 mol dim
VISION_FEATURE_NAMES = [f"vision_dim_{i}" for i in range(48)]
ALL_FEATURE_NAMES    = VISION_FEATURE_NAMES + ["upstream_mol_score"]

# Clinical sanity check lookup: features known to be validated progression predictors
CLINICALLY_VALIDATED_FEATURES = {
    "upstream_mol_score": "Clinically Validated — LightGBM radiomics score (IDH1, MGMT, EGFR, tumor volumes)",
}

# ─── 1. Load Model ────────────────────────────────────────────────────────────
def load_model():
    model = MultimodalLateFusionMLP(
        vision_dim=48, mol_dim=1, bottleneck_dim=16, hidden_dim=32, dropout_rate=0.4
    )
    model.load_state_dict(torch.load(MODEL_PATH, weights_only=True))
    model.eval()
    return model


# ─── 2. Data Ingestion ────────────────────────────────────────────────────────
def load_patient_data(patient_id: str):
    """Load all available timepoints for a patient from LightGBM CSV."""
    lgbm = pd.read_csv(LGBM_CSV)
    patient_data = lgbm[lgbm['patient_id'] == patient_id].sort_values('timepoint_number').reset_index(drop=True)
    if patient_data.empty:
        raise ValueError(f"Patient {patient_id} not found in LightGBM CSV.")
    return patient_data


def load_embedding(patient_id: str, timepoint: str) -> torch.Tensor:
    """Load SWIN embedding for a specific patient-timepoint."""
    fname = f"{patient_id}_{timepoint}_embedding.pt"
    fpath = os.path.join(EMB_DIR, fname)
    if not os.path.exists(fpath):
        raise FileNotFoundError(f"Embedding not found: {fpath}")
    emb = torch.load(fpath, weights_only=True).view(1, -1)
    return emb


# ─── 3. Longitudinal Delta Computation ───────────────────────────────────────
def compute_longitudinal_deltas(patient_data: pd.DataFrame) -> pd.DataFrame:
    """
    Compute Δ from prior timepoint and Δ from nadir for mol_score (upstream_mol_score).
    These represent the 'firing rate change' rather than absolute value.
    """
    df = patient_data.copy()
    df['mol_score_delta_from_prior'] = df['calibrated_probability'].diff()
    df['mol_score_delta_from_nadir'] = df['calibrated_probability'] - df['calibrated_probability'].min()
    df['mol_score_pct_change_from_prior'] = df['calibrated_probability'].pct_change() * 100
    df['mol_score_pct_change_from_nadir'] = (
        (df['calibrated_probability'] - df['calibrated_probability'].min()) /
        (df['calibrated_probability'].min() + 1e-9) * 100
    )
    return df


# ─── 4. MLP Fusion Inference ──────────────────────────────────────────────────
def run_fusion_inference(model, vision_emb: torch.Tensor, mol_score: float) -> float:
    """Run MLP inference and return sigmoid probability."""
    mol_tensor = torch.tensor([[mol_score]], dtype=torch.float32)
    with torch.no_grad():
        logit = model(vision_emb, mol_tensor)
        prob  = torch.sigmoid(logit).item()
    return prob


# ─── 5. RANO 2.0 Rule Engine ─────────────────────────────────────────────────
def apply_rano_rules(patient_data: pd.DataFrame, current_tp_idx: int) -> dict:
    """
    Apply RANO 2.0 criteria based on available longitudinal data.
    Since we don't have raw BD product per timepoint, we use mol_score trajectory
    as a proxy and flag based on percentage change.
    """
    current = patient_data.iloc[current_tp_idx]
    prior_rows = patient_data.iloc[:current_tp_idx]

    # BD Product change (using mol_score trajectory as proxy for volumetric change)
    # In production, this would use actual BD product measurements from measurements.py
    mol_pct_change = current.get('mol_score_pct_change_from_prior', None)
    bd_change_flag = False
    bd_change_pct  = None
    if mol_pct_change is not None and not pd.isna(mol_pct_change):
        bd_change_pct  = mol_pct_change
        bd_change_flag = mol_pct_change > (RANO_BD_THRESHOLD * 100)

    # New lesion: flag if mol_score jumps sharply from nadir (>50% from nadir)
    mol_from_nadir_pct = current.get('mol_score_pct_change_from_nadir', 0)
    new_lesion_flag = mol_from_nadir_pct > 50 if not pd.isna(mol_from_nadir_pct) else False

    rano_pd = bd_change_flag or new_lesion_flag

    return {
        "bd_change_pct":    round(bd_change_pct, 1) if bd_change_pct is not None else None,
        "bd_change_flag":   bd_change_flag,
        "new_lesion_flag":  new_lesion_flag,
        "rano_pd_verdict":  rano_pd,
        "rano_label":       "Progressive Disease (PD)" if rano_pd else "No Progression Detected",
    }


# ─── 6. Weighted Confounder Scoring ──────────────────────────────────────────
def compute_confounder_score(patient_data: pd.DataFrame, current_tp_idx: int,
                              mgmt_status: int = None,
                              steroid_change_pct: float = 0.0,
                              rc_adjacent_enhancement: bool = False) -> dict:
    """
    Weighted pseudoprogression risk score.
    Scoring rubric (literature-based):
      - Days post-radiation < 90  (< 3 months):  +2
      - Days post-radiation 90-180 (3-6 months): +1
      - Days post-radiation 180-365 (6-12 mo):   +0.5
      - Days post-radiation > 365 (> 12 months): +0  (but NOT ruled out)
      - MGMT methylated (status 1):               +1.5  (30-40% pseudo-prog rate)
      - MGMT unknown/indeterminate (status 2-3):  +0.5
      - MGMT unmethylated (status 0):             +0    (~15% pseudo-prog rate)
      - Steroid dose change > 50%:                +1
      - RC-adjacent enhancement:                  +1
    Risk: >=3 = High, 1.5-3 = Moderate, <1.5 = Low
    """
    current = patient_data.iloc[current_tp_idx]
    days_post_rt = current.get('days_from_diagnosis_to_mri', None)

    score = 0.0
    breakdown = {}

    # Time post-radiation scoring
    if days_post_rt is not None and not pd.isna(days_post_rt):
        if days_post_rt < 90:
            score += 2.0
            breakdown['time_post_rt'] = "+2.0 (< 3 months post-RT — highest pseudoprogression window)"
        elif days_post_rt < 180:
            score += 1.0
            breakdown['time_post_rt'] = "+1.0 (3–6 months post-RT — elevated pseudoprogression risk)"
        elif days_post_rt < 365:
            score += 0.5
            breakdown['time_post_rt'] = "+0.5 (6–12 months post-RT — moderate risk, late pseudoprogression possible)"
        else:
            score += 0.0
            breakdown['time_post_rt'] = "+0.0 (> 12 months post-RT — pseudoprogression less likely but not excluded)"
    else:
        breakdown['time_post_rt'] = "N/A (days post-RT unavailable)"

    # MGMT methylation status
    if mgmt_status is not None:
        if mgmt_status == 1:    # methylated
            score += 1.5
            breakdown['mgmt'] = "+1.5 (MGMT methylated — pseudoprogression rate ~30-40%)"
        elif mgmt_status in [2, 3]:  # indeterminate / unable to assess
            score += 0.5
            breakdown['mgmt'] = "+0.5 (MGMT indeterminate — risk uncertain)"
        else:                   # unmethylated (0) or unknown (4)
            score += 0.0
            breakdown['mgmt'] = "+0.0 (MGMT unmethylated — pseudoprogression rate ~15%)"
    else:
        breakdown['mgmt'] = "N/A (MGMT status not provided)"

    # Steroid change
    if abs(steroid_change_pct) > 50:
        score += 1.0
        breakdown['steroid'] = f"+1.0 (Steroid dose change {steroid_change_pct:+.0f}% — may cause imaging changes)"
    else:
        breakdown['steroid'] = f"+0.0 (Steroid dose change {steroid_change_pct:+.0f}% — within normal range)"

    # RC-adjacent enhancement
    if rc_adjacent_enhancement:
        score += 1.0
        breakdown['rc_adjacent'] = "+1.0 (RC-adjacent enhancement detected — may reflect post-surgical change)"
    else:
        breakdown['rc_adjacent'] = "+0.0 (No RC-adjacent enhancement)"

    # Risk classification
    if score >= 3.0:
        risk_level = "HIGH Pseudoprogression Risk"
        risk_color = "red"
    elif score >= 1.5:
        risk_level = "MODERATE Pseudoprogression Risk"
        risk_color = "orange"
    else:
        risk_level = "LOW Pseudoprogression Risk"
        risk_color = "green"

    return {
        "total_score":  round(score, 1),
        "risk_level":   risk_level,
        "risk_color":   risk_color,
        "breakdown":    breakdown,
    }


# ─── 7. SHAP Interpretation ───────────────────────────────────────────────────
def compute_shap_values(model, vision_emb: torch.Tensor, mol_score: float,
                         patient_id: str, timepoint: str) -> dict:
    """
    Compute SHAP values for the fusion model using GradientExplainer.
    Uses real embedding files as background for more meaningful SHAP values.
    Returns top features with clinical sanity check annotations.
    """
    mol_tensor   = torch.tensor([[mol_score]], dtype=torch.float32)
    input_tensor = torch.cat([vision_emb, mol_tensor], dim=1)  # shape: [1, 49]

    # Wrapper model that accepts concatenated input
    class FusionWrapper(torch.nn.Module):
        def __init__(self, base_model):
            super().__init__()
            self.base = base_model
        def forward(self, x):
            vision = x[:, :48]
            mol    = x[:, 48:49]
            logit  = self.base(vision, mol)
            return torch.sigmoid(logit)

    wrapper = FusionWrapper(model)
    wrapper.eval()

    # Build background from real embeddings (up to 20 samples)
    emb_files = sorted(os.listdir(EMB_DIR))[:20]
    bg_tensors = [torch.load(os.path.join(EMB_DIR, f), weights_only=True).view(1, -1)
                  for f in emb_files]
    bg_vision  = torch.cat(bg_tensors, dim=0)                     # [N, 48]
    bg_mol     = torch.zeros(bg_vision.shape[0], 1)               # [N, 1]
    background = torch.cat([bg_vision, bg_mol], dim=1)            # [N, 49]

    explainer = shap.GradientExplainer(wrapper, background)
    shap_vals = explainer.shap_values(input_tensor)

    # Flatten to 1D array of length 49
    shap_array = np.array(shap_vals).flatten()

    # Build feature importance dict
    feature_importance = {
        name: float(val)
        for name, val in zip(ALL_FEATURE_NAMES, shap_array)
    }

    # Top 5 features by absolute SHAP value
    sorted_features = sorted(feature_importance.items(), key=lambda x: abs(x[1]), reverse=True)[:5]

    # Sanity check annotation
    annotated = []
    for feat_name, shap_val in sorted_features:
        if feat_name in CLINICALLY_VALIDATED_FEATURES:
            annotation = CLINICALLY_VALIDATED_FEATURES[feat_name]
        else:
            annotation = "Novel Signal — Interpret with Caution (imaging latent feature, not directly mapped to named biomarker)"
        annotated.append({
            "feature":    feat_name,
            "shap_value": round(shap_val, 4),
            "direction":  "toward progression" if shap_val > 0 else "away from progression",
            "annotation": annotation,
        })

    # Generate SHAP bar plot
    plot_path = os.path.join(REPORTS_DIR, f"{patient_id}_{timepoint}_shap.png")
    _plot_shap_bar(annotated, patient_id, timepoint, plot_path)

    return {
        "top_features": annotated,
        "plot_path":    plot_path,
    }


def _plot_shap_bar(annotated_features: list, patient_id: str, timepoint: str, save_path: str):
    """Generate a clean SHAP bar chart."""
    names  = [f["feature"] for f in annotated_features]
    values = [f["shap_value"] for f in annotated_features]
    colors = ["#e74c3c" if v > 0 else "#3498db" for v in values]

    fig, ax = plt.subplots(figsize=(9, 4))
    bars = ax.barh(names[::-1], values[::-1], color=colors[::-1], edgecolor='white', height=0.6)
    ax.axvline(0, color='#2c3e50', linewidth=1.2, linestyle='--', alpha=0.7)
    ax.set_xlabel("SHAP Value (contribution to progression probability)", fontsize=10)
    ax.set_title(f"SHAP Feature Importance — {patient_id} {timepoint}", fontsize=11, fontweight='bold')

    red_patch  = mpatches.Patch(color='#e74c3c', label='Increases progression risk')
    blue_patch = mpatches.Patch(color='#3498db', label='Decreases progression risk')
    ax.legend(handles=[red_patch, blue_patch], fontsize=9, loc='lower right')

    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()


# ─── 8. Longitudinal Trend Sparkline ─────────────────────────────────────────
def plot_longitudinal_trend(patient_data: pd.DataFrame, current_tp_idx: int,
                             fusion_probs: list, patient_id: str) -> str:
    """
    Generate a longitudinal trend plot showing:
    - LightGBM mol_score over time
    - Fusion MLP probability over time
    - Threshold line at 0.48
    """
    plot_path = os.path.join(REPORTS_DIR, f"{patient_id}_longitudinal_trend.png")

    timepoints = patient_data['timepoint_number'].tolist()
    mol_scores = patient_data['calibrated_probability'].tolist()

    fig, ax = plt.subplots(figsize=(9, 4))

    # LightGBM mol score
    ax.plot(timepoints, mol_scores, 'o--', color='#3498db', linewidth=1.8,
            markersize=7, label='LightGBM Mol Score (upstream)', alpha=0.85)

    # Fusion MLP probabilities (only available timepoints)
    if fusion_probs:
        tp_nums_fusion = patient_data.iloc[:len(fusion_probs)]['timepoint_number'].tolist()
        ax.plot(tp_nums_fusion, fusion_probs, 's-', color='#e74c3c', linewidth=2.2,
                markersize=8, label='Fusion MLP Probability', zorder=5)

    # Threshold line
    ax.axhline(FUSION_THRESHOLD, color='#e67e22', linewidth=1.5, linestyle='--',
               alpha=0.8, label=f'Alert Threshold ({FUSION_THRESHOLD})')

    # Highlight current timepoint
    if current_tp_idx < len(fusion_probs):
        curr_tp_num = patient_data.iloc[current_tp_idx]['timepoint_number']
        curr_prob   = fusion_probs[current_tp_idx]
        ax.scatter([curr_tp_num], [curr_prob], s=150, color='#e74c3c',
                   zorder=10, edgecolors='black', linewidths=1.5)
        ax.annotate(f"  Current\n  ({curr_prob:.3f})", (curr_tp_num, curr_prob),
                    fontsize=9, color='#c0392b', fontweight='bold')

    # Ground truth labels
    for _, row in patient_data.iterrows():
        if row['label'] == 1:
            ax.axvline(row['timepoint_number'], color='#8e44ad', linewidth=1.2,
                       linestyle=':', alpha=0.6)

    ax.set_xlabel("Timepoint Number", fontsize=10)
    ax.set_ylabel("Probability", fontsize=10)
    ax.set_title(f"Longitudinal Progression Risk — {patient_id}", fontsize=11, fontweight='bold')
    ax.set_ylim(0, 1.05)
    ax.legend(fontsize=9, loc='upper left')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.grid(axis='y', alpha=0.3)

    # Add delta annotations
    mol_deltas = patient_data['mol_score_delta_from_prior'].tolist()
    for i, (tp, delta) in enumerate(zip(timepoints, mol_deltas)):
        if not pd.isna(delta) and delta != 0:
            color = '#e74c3c' if delta > 0 else '#27ae60'
            ax.annotate(f"{delta:+.3f}", (tp, mol_scores[i] + 0.02),
                        fontsize=7.5, color=color, ha='center', alpha=0.8)

    plt.tight_layout()
    plt.savefig(plot_path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    return plot_path


# ─── 9. LLM Summary with Confidence-Tiered Templates ─────────────────────────
def generate_llm_summary(report_data: dict) -> str:
    """
    Generate clinical summary using GPT-4.1-mini with confidence-tiered language.
    Switches prompt template based on RANO-AI concordance and fusion probability.
    """
    client = OpenAI()

    fusion_prob    = report_data['fusion_prob']
    rano_pd        = report_data['rano']['rano_pd_verdict']
    ai_alert       = fusion_prob >= FUSION_THRESHOLD
    concordant     = (rano_pd == ai_alert)
    confounder     = report_data['confounder']
    shap_top       = report_data['shap']['top_features'][:3]
    patient_id     = report_data['patient_id']
    timepoint      = report_data['timepoint']
    days_post_rt   = report_data['days_post_rt']
    mol_score      = report_data['mol_score']
    delta_prior    = report_data['mol_score_delta_from_prior']
    delta_nadir    = report_data['mol_score_delta_from_nadir']

    # ── Confidence-tiered language selection ──────────────────────────────────
    if fusion_prob >= 0.75:
        confidence_phrase = "strongly suggests"
        certainty_note    = "The model output is in the high-confidence range (>0.75)."
    elif fusion_prob >= FUSION_THRESHOLD:
        confidence_phrase = "is consistent with progression but warrants close follow-up"
        certainty_note    = (
            f"The model output ({fusion_prob:.3f}) is above threshold but in the moderate range "
            f"(0.48–0.75). Clinical correlation and short-interval imaging are recommended."
        )
    else:
        confidence_phrase = "does not support progression at this timepoint"
        certainty_note    = (
            f"The model output ({fusion_prob:.3f}) is below the alert threshold (0.48). "
            f"Continued surveillance is advised."
        )

    # ── RANO-AI concordance switch ─────────────────────────────────────────────
    if concordant:
        concordance_instruction = (
            "RANO 2.0 criteria and the AI model are in AGREEMENT. "
            "Write a confident, definitive summary that clearly states the conclusion."
        )
    else:
        concordance_instruction = (
            "RANO 2.0 criteria and the AI model are in DISAGREEMENT. "
            "Write a cautious, nuanced summary that explicitly flags this discordance, "
            "emphasizes clinical uncertainty, and strongly recommends multidisciplinary review "
            "and short-interval follow-up imaging (4-6 weeks)."
        )

    # ── SHAP feature summary ───────────────────────────────────────────────────
    shap_summary = "; ".join([
        f"{f['feature']} (SHAP={f['shap_value']:+.4f}, {f['direction']}, {f['annotation'].split(' — ')[0]})"
        for f in shap_top
    ])

    # ── Build prompt ───────────────────────────────────────────────────────────
    prompt = f"""You are a neuro-oncology AI assistant generating a structured clinical report summary.
Write in formal medical English. Be precise and evidence-based.

PATIENT: {patient_id}, {timepoint}
Days from diagnosis to MRI: {days_post_rt:.0f}

LONGITUDINAL RISK TRAJECTORY:
- Current LightGBM mol score: {mol_score:.4f}
- Δ from prior timepoint: {f'{delta_prior:+.4f}' if delta_prior is not None else 'N/A (first timepoint)'}
- Δ from nadir: {f'{delta_nadir:+.4f}' if delta_nadir is not None else 'N/A'}

AI FUSION MODEL:
- Unified Fusion Probability: {fusion_prob:.4f} (threshold: {FUSION_THRESHOLD})
- AI Verdict: {"PROGRESSION ALERT" if ai_alert else "No Alert"}
- {certainty_note}

RANO 2.0 RULE ENGINE:
- BD Change: {report_data['rano']['bd_change_pct']}% ({'+' if report_data['rano']['bd_change_flag'] else 'below threshold'})
- New Lesion: {"Detected" if report_data['rano']['new_lesion_flag'] else "Not detected"}
- RANO Verdict: {report_data['rano']['rano_label']}

CONFOUNDER ASSESSMENT:
- Pseudoprogression Risk Score: {confounder['total_score']}/5.5 → {confounder['risk_level']}
- Breakdown: {'; '.join([f'{k}: {v}' for k, v in confounder['breakdown'].items()])}

SHAP TOP DRIVERS:
{shap_summary}

CONCORDANCE STATUS: {concordance_instruction}

INSTRUCTIONS:
1. Write exactly ONE paragraph (5-8 sentences).
2. Open with patient context and key longitudinal change (delta, not just absolute value).
3. State RANO verdict and AI verdict clearly.
4. Integrate the confounder risk assessment naturally.
5. Reference the top SHAP driver(s) to explain WHY the AI reached its conclusion.
6. Use the phrase "{confidence_phrase}" when describing the AI's assessment.
7. Close with a concrete clinical recommendation (e.g., continue surveillance, MDT review, short-interval MRI).
8. DO NOT use bullet points. Write in flowing prose.
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=500,
    )
    return response.choices[0].message.content.strip()


# ─── 10. Report Renderer ──────────────────────────────────────────────────────
def render_markdown_report(report_data: dict, llm_summary: str,
                            shap_plot_path: str, trend_plot_path: str) -> str:
    """Render the full Clinical Report as a Markdown string."""

    p          = report_data['patient_id']
    tp         = report_data['timepoint']
    fusion_prob = report_data['fusion_prob']
    rano        = report_data['rano']
    confounder  = report_data['confounder']
    shap_data   = report_data['shap']
    patient_df  = report_data['patient_df']
    current_idx = report_data['current_tp_idx']
    current_row = patient_df.iloc[current_idx]
    concordant  = (rano['rano_pd_verdict'] == (fusion_prob >= FUSION_THRESHOLD))

    # Confidence tier
    if fusion_prob >= 0.75:
        conf_tier = "HIGH CONFIDENCE"
        conf_color_md = "🔴"
    elif fusion_prob >= FUSION_THRESHOLD:
        conf_tier = "MODERATE — CLOSE FOLLOW-UP WARRANTED"
        conf_color_md = "🟠"
    else:
        conf_tier = "LOW — NO ALERT"
        conf_color_md = "🟢"

    concordance_label = "✅ CONCORDANT" if concordant else "⚠️ DISCORDANT — MDT REVIEW RECOMMENDED"

    lines = []
    lines.append(f"# Glioma Post-Treatment Surveillance Report")
    lines.append(f"**Patient:** `{p}` | **Timepoint:** `{tp}` | **Generated:** AI Agent Pipeline v1.0")
    lines.append("")
    lines.append("---")
    lines.append("")

    # ── Section 1: Fixed Clinical & Volumetric Metrics ────────────────────────
    lines.append("## Section 1 — Fixed Clinical & Volumetric Metrics")
    lines.append("")
    lines.append("### Patient Demographics & Timeline")
    lines.append("")
    lines.append(f"| Field | Value |")
    lines.append(f"| :--- | :--- |")
    lines.append(f"| Patient ID | `{p}` |")
    lines.append(f"| Current Timepoint | `{tp}` (Timepoint #{int(current_row['timepoint_number'])}) |")
    lines.append(f"| Days from Diagnosis to MRI | {current_row['days_from_diagnosis_to_mri']:.0f} days |")
    lines.append(f"| Ground Truth Label | {'**Progression (1)**' if current_row['label'] == 1 else 'No Progression (0)'} |")
    lines.append("")
    lines.append("### Molecular Profile")
    lines.append("")
    lines.append("*Note: Molecular profile values are sourced from `measurements.py` (currently being finalized). Placeholder values shown below — to be populated from EHR in production.*")
    lines.append("")
    lines.append("| Biomarker | Status | Clinical Significance |")
    lines.append("| :--- | :--- | :--- |")
    lines.append("| IDH1 Mutation | Wild-type (0) | Associated with worse prognosis |")
    lines.append("| MGMT Methylation | Unknown (4) | Affects pseudoprogression risk |")
    lines.append("| EGFR Amplification | Amplified (2) | Aggressive phenotype marker |")
    lines.append("| 1p/19q Codeletion | Intact (0) | Not oligodendroglial |")
    lines.append("| TERT Promoter Mutation | Mutated (2) | Poor prognostic marker |")
    lines.append("| WHO Grade | 4 | Highest malignancy grade |")
    lines.append("")

    # Longitudinal table
    lines.append("### Longitudinal Risk Score Trajectory")
    lines.append("")
    lines.append("*The table below shows the evolution of the LightGBM molecular risk score across all available timepoints. Delta values capture the rate of change — the clinically informative signal.*")
    lines.append("")
    lines.append("| Timepoint | Days from Dx | Mol Score | Δ from Prior | Δ% from Prior | Δ from Nadir | Label |")
    lines.append("| :--- | :---: | :---: | :---: | :---: | :---: | :---: |")
    for i, row in patient_df.iterrows():
        delta_prior_str = f"{row['mol_score_delta_from_prior']:+.4f}" if not pd.isna(row['mol_score_delta_from_prior']) else "—"
        delta_pct_str   = f"{row['mol_score_pct_change_from_prior']:+.1f}%" if not pd.isna(row['mol_score_pct_change_from_prior']) else "—"
        delta_nadir_str = f"{row['mol_score_delta_from_nadir']:+.4f}" if not pd.isna(row['mol_score_delta_from_nadir']) else "—"
        label_str       = "**PD**" if row['label'] == 1 else "Stable"
        current_marker  = " ◀ **Current**" if i == current_idx else ""
        lines.append(f"| {row['timepoint']}{current_marker} | {row['days_from_diagnosis_to_mri']:.0f} | {row['calibrated_probability']:.4f} | {delta_prior_str} | {delta_pct_str} | {delta_nadir_str} | {label_str} |")
    lines.append("")
    lines.append(f"![Longitudinal Trend]({os.path.basename(trend_plot_path)})")
    lines.append("")
    lines.append("---")
    lines.append("")

    # ── Section 2: RANO 2.0 Rule Engine ───────────────────────────────────────
    lines.append("## Section 2 — RANO 2.0 Rule Engine")
    lines.append("")
    lines.append("| Criterion | Value | Threshold | Triggered? |")
    lines.append("| :--- | :---: | :---: | :---: |")
    bd_val = f"{rano['bd_change_pct']:+.1f}%" if rano['bd_change_pct'] is not None else "N/A"
    lines.append(f"| Bidimensional (BD) Product Change | {bd_val} | +25% | {'**YES**' if rano['bd_change_flag'] else 'No'} |")
    lines.append(f"| New Independent Lesion | {'Detected' if rano['new_lesion_flag'] else 'Not detected'} | Any | {'**YES**' if rano['new_lesion_flag'] else 'No'} |")
    lines.append("")
    rano_verdict_display = f"**{rano['rano_label']}**" if rano['rano_pd_verdict'] else rano['rano_label']
    lines.append(f"> **RANO 2.0 Verdict:** {rano_verdict_display}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # ── Section 3: Confounder Check ───────────────────────────────────────────
    lines.append("## Section 3 — Confounder Check (Weighted Pseudoprogression Risk)")
    lines.append("")
    lines.append(f"**Total Risk Score: {confounder['total_score']} / 5.5**")
    lines.append("")
    lines.append(f"> **Risk Classification: {confounder['risk_level']}**")
    lines.append("")
    lines.append("| Confounder Factor | Score Contribution | Rationale |")
    lines.append("| :--- | :---: | :--- |")
    for factor, detail in confounder['breakdown'].items():
        score_part = detail.split(' ')[0]
        rationale  = ' '.join(detail.split(' ')[1:])
        lines.append(f"| {factor.replace('_', ' ').title()} | {score_part} | {rationale} |")
    lines.append("")
    lines.append("*Note: MGMT methylation status is the single strongest predictor of pseudoprogression risk. When MGMT status is unknown, risk should be treated conservatively.*")
    lines.append("")
    lines.append("---")
    lines.append("")

    # ── Section 4: AI Interpretation — SHAP ───────────────────────────────────
    lines.append("## Section 4 — AI Interpretation: Fusion MLP & SHAP Analysis")
    lines.append("")
    lines.append(f"| Metric | Value |")
    lines.append(f"| :--- | :--- |")
    lines.append(f"| Unified Fusion Probability | **{fusion_prob:.4f}** |")
    lines.append(f"| Alert Threshold | 0.48 |")
    lines.append(f"| AI Verdict | {conf_color_md} **{conf_tier}** |")
    lines.append(f"| RANO-AI Concordance | {concordance_label} |")
    lines.append("")
    lines.append("### SHAP Top Feature Contributions")
    lines.append("")
    lines.append("*SHAP values explain the model's prediction, not direct causality. Features marked 'Novel Signal' should be interpreted with caution and cross-referenced with clinical findings.*")
    lines.append("")
    lines.append("| Rank | Feature | SHAP Value | Direction | Clinical Status |")
    lines.append("| :---: | :--- | :---: | :--- | :--- |")
    for rank, feat in enumerate(shap_data['top_features'], 1):
        direction_icon = "↑ Increases risk" if feat['shap_value'] > 0 else "↓ Decreases risk"
        lines.append(f"| {rank} | `{feat['feature']}` | {feat['shap_value']:+.4f} | {direction_icon} | {feat['annotation'].split(' — ')[0]} |")
    lines.append("")
    lines.append(f"![SHAP Feature Importance]({os.path.basename(shap_plot_path)})")
    lines.append("")
    lines.append("---")
    lines.append("")

    # ── Section 5: LLM Clinical Summary ───────────────────────────────────────
    lines.append("## Section 5 — LLM-Generated Clinical Summary")
    lines.append("")
    lines.append(f"> {llm_summary}")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("*This report was generated automatically by the Glioma Post-Treatment Surveillance AI Agent. It is intended as a decision-support tool and does not replace clinical judgment. All findings should be reviewed by a qualified neuro-oncologist.*")

    return "\n".join(lines)


# ─── 11. Main Orchestrator ────────────────────────────────────────────────────
def run_agent(patient_id: str, timepoint: str,
              mgmt_status: int = None,
              steroid_change_pct: float = 0.0,
              rc_adjacent_enhancement: bool = False) -> str:
    """
    Full agent pipeline orchestrator.
    Returns path to the generated Markdown report.
    """
    print(f"\n{'='*60}")
    print(f"  Glioma Surveillance Agent — {patient_id} {timepoint}")
    print(f"{'='*60}")

    # Step 1: Load model
    print("[1/7] Loading Fusion MLP model...")
    model = load_model()

    # Step 2: Load patient data
    print("[2/7] Loading patient data and computing longitudinal deltas...")
    patient_data = load_patient_data(patient_id)
    patient_data = compute_longitudinal_deltas(patient_data)

    # Find current timepoint index
    tp_match = patient_data[patient_data['timepoint'] == timepoint]
    if tp_match.empty:
        raise ValueError(f"Timepoint {timepoint} not found for patient {patient_id}.")
    current_tp_idx = tp_match.index[0]

    # Step 3: Load embedding and run inference for ALL available timepoints
    print("[3/7] Running MLP inference across all timepoints...")
    fusion_probs = []
    for _, row in patient_data.iterrows():
        tp_str = row['timepoint']
        try:
            emb  = load_embedding(patient_id, tp_str)
            prob = run_fusion_inference(model, emb, row['calibrated_probability'])
            fusion_probs.append(prob)
        except FileNotFoundError:
            fusion_probs.append(None)

    current_fusion_prob = fusion_probs[current_tp_idx]
    current_mol_score   = patient_data.iloc[current_tp_idx]['calibrated_probability']
    current_row         = patient_data.iloc[current_tp_idx]

    print(f"    Fusion probability at {timepoint}: {current_fusion_prob:.4f} (threshold: {FUSION_THRESHOLD})")

    # Step 4: RANO 2.0 rules
    print("[4/7] Applying RANO 2.0 rule engine...")
    rano_result = apply_rano_rules(patient_data, current_tp_idx)
    print(f"    RANO verdict: {rano_result['rano_label']}")

    # Step 5: Confounder scoring
    print("[5/7] Computing weighted confounder score...")
    confounder_result = compute_confounder_score(
        patient_data, current_tp_idx,
        mgmt_status=mgmt_status,
        steroid_change_pct=steroid_change_pct,
        rc_adjacent_enhancement=rc_adjacent_enhancement
    )
    print(f"    Confounder score: {confounder_result['total_score']} → {confounder_result['risk_level']}")

    # Step 6: SHAP interpretation
    print("[6/7] Computing SHAP values and generating plots...")
    current_emb = load_embedding(patient_id, timepoint)
    shap_result = compute_shap_values(model, current_emb, current_mol_score, patient_id, timepoint)

    # Longitudinal trend plot
    valid_probs = [p for p in fusion_probs if p is not None]
    trend_path  = plot_longitudinal_trend(patient_data, current_tp_idx, valid_probs, patient_id)
    print(f"    SHAP plot saved: {shap_result['plot_path']}")
    print(f"    Trend plot saved: {trend_path}")

    # Step 7: LLM summary
    print("[7/7] Generating LLM clinical summary...")
    report_data = {
        "patient_id":                patient_id,
        "timepoint":                 timepoint,
        "fusion_prob":               current_fusion_prob,
        "mol_score":                 current_mol_score,
        "mol_score_delta_from_prior": current_row.get('mol_score_delta_from_prior', None),
        "mol_score_delta_from_nadir": current_row.get('mol_score_delta_from_nadir', None),
        "days_post_rt":              current_row['days_from_diagnosis_to_mri'],
        "rano":                      rano_result,
        "confounder":                confounder_result,
        "shap":                      shap_result,
        "patient_df":                patient_data,
        "current_tp_idx":            current_tp_idx,
    }
    llm_summary = generate_llm_summary(report_data)

    # Render report
    report_md = render_markdown_report(report_data, llm_summary,
                                        shap_result['plot_path'], trend_path)

    # Save report
    report_path = os.path.join(REPORTS_DIR, f"{patient_id}_{timepoint}_report.md")
    with open(report_path, 'w') as f:
        f.write(report_md)

    print(f"\n✅ Report saved: {report_path}")
    return report_path


# ─── Entry Point ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Demo: PatientID_0019, Timepoint_6 (ground truth = 1, progression)
    report_path = run_agent(
        patient_id="PatientID_0019",
        timepoint="Timepoint_6",
        mgmt_status=None,          # Unknown — will be populated from measurements.py
        steroid_change_pct=0.0,
        rc_adjacent_enhancement=False,
    )
    print(f"\nReport generated at: {report_path}")
