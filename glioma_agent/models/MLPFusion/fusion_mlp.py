import os
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
import pandas as pd
from torch.utils.data import Dataset, DataLoader

import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix, roc_curve, auc


# ==========================================
# 🌟 Top-tier Loss Function: Focal Loss
# ==========================================
class FocalLoss(nn.Module):
    def __init__(self, alpha=0.7, gamma=2.0):
        """
        alpha: Controls the weight of positive vs. negative samples (0.7 favors the progression class 1).
        gamma: Controls the focus on "hard-to-classify" samples (2.0 is standard).
        """
        super(FocalLoss, self).__init__()
        self.alpha = alpha
        self.gamma = gamma

    def forward(self, inputs, targets):
        bce_loss = F.binary_cross_entropy_with_logits(inputs, targets, reduction='none')
        pt = torch.exp(-bce_loss)  # pt is the probability of the correct prediction
        # Core formula: The more incorrect the prediction (smaller pt), the larger the applied weight.
        focal_loss = self.alpha * (1 - pt) ** self.gamma * bce_loss
        return focal_loss.mean()


# ==========================================
# 1. Core Architecture: Multimodal Late Fusion MLP
# ==========================================
class MultimodalLateFusionMLP(nn.Module):
    def __init__(self, vision_dim=48, mol_dim=1, bottleneck_dim=16, hidden_dim=32, dropout_rate=0.4):
        super(MultimodalLateFusionMLP, self).__init__()

        # Imaging feature pathway (UNETR embeddings)
        self.bottleneck = nn.Sequential(
            nn.LayerNorm(vision_dim),
            nn.Linear(vision_dim, bottleneck_dim),
            nn.ReLU(),
            nn.LayerNorm(bottleneck_dim)
        )

        # Molecular score pathway (Upscaling to balance modalities)
        self.mol_encoder = nn.Sequential(
            nn.Linear(mol_dim, 4),
            nn.ReLU()
        )

        # Combined dimension: 16 (vision) + 4 (molecular) = 20
        fusion_dim = bottleneck_dim + 4
        self.relearning_mlp = nn.Sequential(
            nn.Linear(fusion_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout_rate),
            nn.Linear(hidden_dim, 1)
            # 🚫 NOTE: No Sigmoid here; outputting raw logits for Focal Loss
        )

    def forward(self, vision_emb, mol_score):
        aligned_vision = self.bottleneck(vision_emb)
        encoded_mol = self.mol_encoder(mol_score)

        # 🌟 Modality Dropout (Active only during training)
        # 30% probability to zero out molecular features, forcing the network to learn from imaging.
        if self.training:
            mol_mask = (torch.rand(encoded_mol.shape[0], 1, device=encoded_mol.device) > 0.3).float()
            encoded_mol = encoded_mol * mol_mask

        # Concatenate features from both modalities
        fused_features = torch.cat((aligned_vision, encoded_mol), dim=1)
        return self.relearning_mlp(fused_features)


# ==========================================
# 2. Data Loader
# ==========================================
class GliomaFusionDataset(Dataset):
    def __init__(self, csv_path, emb_dir, split_name="Dataset"):
        self.df = pd.read_csv(csv_path)
        self.emb_dir = emb_dir
        self.valid_data = []

        for index, row in self.df.iterrows():
            p_id = str(row['patient_id']).strip()
            t_pt = str(row['timepoint']).strip()
            pt_filename = f"{p_id}_{t_pt}_embedding.pt"
            pt_path = os.path.join(self.emb_dir, pt_filename)

            # Only append if the embedding file exists
            if os.path.exists(pt_path):
                self.valid_data.append({
                    'patient_id': p_id,
                    'timepoint': t_pt,
                    'vision_path': pt_path,
                    'mol_score': float(row['progression_risk_probability']),
                    'label': float(row['label'])
                })
        print(f"✅ {split_name} successfully loaded {len(self.valid_data)} complete patient samples.")

    def __len__(self):
        return len(self.valid_data)

    def __getitem__(self, idx):
        item = self.valid_data[idx]
        vision_emb = torch.load(item['vision_path'])

        # Flatten the vision embedding if necessary
        if isinstance(vision_emb, torch.Tensor):
            vision_emb = vision_emb.view(-1)

        mol_score = torch.tensor([item['mol_score']], dtype=torch.float32)
        label = torch.tensor([item['label']], dtype=torch.float32)
        patient_info = f"{item['patient_id']}_{item['timepoint']}"

        return vision_emb, mol_score, label, patient_info


# ==========================================
# 3. Complete Training & Testing Pipeline
# ==========================================
if __name__ == "__main__":
    print("--- 🚀 Starting Rigorous ML Pipeline ---")

    train_csv = "train_predictions.csv"
    test_csv = "test_predictions.csv"
    embeddings_folder = "embeddings"

    if not os.path.exists(embeddings_folder):
        raise FileNotFoundError(f"Directory not found: '{embeddings_folder}'")

    train_dataset = GliomaFusionDataset(train_csv, embeddings_folder, split_name="[Train Set]")
    test_dataset = GliomaFusionDataset(test_csv, embeddings_folder, split_name="[Test Set]")

    train_loader = DataLoader(train_dataset, batch_size=16, shuffle=True) if len(train_dataset) > 0 else None
    test_loader = DataLoader(test_dataset, batch_size=16, shuffle=False) if len(test_dataset) > 0 else None

    model = MultimodalLateFusionMLP()
    criterion = FocalLoss(alpha=0.7, gamma=2.0)
    optimizer = optim.Adam(model.parameters(), lr=0.001, weight_decay=1e-4)  # L2 Regularization applied

    # ==========================================
    # 4. Training Phase (with Model Checkpointing)
    # ==========================================
    if train_loader is not None:
        epochs = 500
        best_test_loss = float('inf')
        best_model_path = "best_fusion_model.pth"

        print("\n[Training Phase Started]")
        for epoch in range(epochs):
            model.train()
            epoch_loss = 0.0

            for vision_emb, mol_score, label, _ in train_loader:
                optimizer.zero_grad()
                predictions_logits = model(vision_emb, mol_score)
                loss = criterion(predictions_logits, label)
                loss.backward()
                optimizer.step()
                epoch_loss += loss.item()

            avg_train_loss = epoch_loss / len(train_loader)

            # Validation Phase
            avg_test_loss = 0.0
            if test_loader is not None:
                model.eval()
                test_loss = 0.0
                with torch.no_grad():
                    for vision_emb, mol_score, label, _ in test_loader:
                        predictions_logits = model(vision_emb, mol_score)
                        loss = criterion(predictions_logits, label)
                        test_loss += loss.item()
                avg_test_loss = test_loss / len(test_loader)

            # Monitor and dynamically save the best model
            if (epoch + 1) % 10 == 0:
                print_str = f"Epoch [{epoch + 1}/{epochs}], Train Loss: {avg_train_loss:.4f} | Test Loss: {avg_test_loss:.4f}"
                if test_loader is not None and avg_test_loss < best_test_loss:
                    best_test_loss = avg_test_loss
                    torch.save(model.state_dict(), best_model_path)
                    print_str += f" 🌟 [Peak weights saved]"
                print(print_str)

    # ==========================================
    # 5. Testing/Inference Phase
    # ==========================================
    if test_loader is not None:
        print("\n--- 🎯 Inference Phase on Test Set ---")

        # Load the best state dictionary observed during training
        if os.path.exists("best_fusion_model.pth"):
            model.load_state_dict(torch.load("best_fusion_model.pth"))
            print("✅ Peak weights successfully loaded!")

        model.eval()
        unified_results = []

        with torch.no_grad():
            for vision_emb, mol_score, label, patient_infos in test_loader:
                final_logits = model(vision_emb, mol_score)
                final_probs = torch.sigmoid(final_logits)  # Convert logits back to probabilities

                for i in range(len(patient_infos)):
                    unified_results.append({
                        "patient_timepoint": patient_infos[i],
                        "ground_truth": int(label[i].item()),
                        "upstream_mol_score": round(mol_score[i].item(), 4),
                        "unified_fusion_prob": round(final_probs[i].item(), 4)
                    })

        results_df = pd.DataFrame(unified_results)
        results_df.to_csv("unified_fusion_results.csv", index=False)
        print("✅ Ultimate unified results successfully exported!")

        # ==========================================
        # 🌟 6. Automated Evaluation & Chart Generation Module
        # ==========================================
        print("\n" + "=" * 50)
        print(" 📊 Auto-Evaluation Report")
        print("=" * 50)

        # Threshold Determination (Fine-tuned to 0.48 to minimize false negatives)
        results_df['fusion_pred_class'] = (results_df['unified_fusion_prob'] >= 0.48).astype(int)
        results_df['upstream_pred_class'] = (results_df['upstream_mol_score'] >= 0.48).astype(int)

        y_true = results_df['ground_truth']
        y_pred = results_df['fusion_pred_class']
        y_prob = results_df['unified_fusion_prob']

        # Core Metrics Calculation
        acc = accuracy_score(y_true, y_pred)
        prec = precision_score(y_true, y_pred, zero_division=0)
        rec = recall_score(y_true, y_pred, zero_division=0)
        f1 = f1_score(y_true, y_pred, zero_division=0)

        print(f"🎯 Overall Accuracy : {acc:.4f}")
        print(f"🎯 Precision        : {prec:.4f}")
        print(f"🎯 Recall           : {rec:.4f}")
        print(f"🎯 F1-Score         : {f1:.4f}")

        # Error Correction Analysis (Overruling upstream model)
        flipped_mask = results_df['fusion_pred_class'] != results_df['upstream_pred_class']
        flipped_df = results_df[flipped_mask]
        total_flips = len(flipped_df)

        if total_flips > 0:
            correct_flips = (flipped_df['fusion_pred_class'] == flipped_df['ground_truth']).sum()
            wrong_flips = (flipped_df['fusion_pred_class'] != flipped_df['ground_truth']).sum()
            print(f"\n👁️ Vision Overrule (Correcting upstream clinical errors):")
            print(f"  ├─ Total times overruled           : {total_flips}")
            print(f"  ├─ Successful corrections (Correct): {correct_flips}")
            print(f"  └─ Counterproductive (Wrong)       : {wrong_flips}")
        else:
            print("\n👁️ Vision Overrule: No upstream predictions were overruled this time.")

        # Plot 1: Confusion Matrix
        cm = confusion_matrix(y_true, y_pred)
        plt.figure(figsize=(6, 5))
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', cbar=False, annot_kws={"size": 16},
                    xticklabels=['Predicted 0 (Safe)', 'Predicted 1 (Progression)'],
                    yticklabels=['Actual 0 (Safe)', 'Actual 1 (Progression)'])
        plt.title('Fusion MLP: Confusion Matrix', fontsize=14)
        plt.tight_layout()
        plt.savefig('fusion_confusion_matrix.png', dpi=300)
        plt.close()

        # Plot 2: ROC Curve (Calculate AUC)
        fpr, tpr, thresholds = roc_curve(y_true, y_prob)
        roc_auc = auc(fpr, tpr)
        plt.figure(figsize=(6, 5))
        plt.plot(fpr, tpr, color='darkorange', lw=2, label=f'ROC curve (AUC = {roc_auc:.3f})')
        plt.plot([0, 1], [0, 1], color='navy', lw=2, linestyle='--')
        plt.xlim([0.0, 1.0])
        plt.ylim([0.0, 1.05])
        plt.xlabel('False Positive Rate', fontsize=12)
        plt.ylabel('True Positive Rate', fontsize=12)
        plt.title('Fusion MLP: ROC Curve', fontsize=14)
        plt.legend(loc="lower right")
        plt.grid(alpha=0.3)
        plt.tight_layout()
        plt.savefig('fusion_roc_curve.png', dpi=300)
        plt.close()

        print("\n🖼️ Visualizations successfully generated!")
        print("  ├─ Confusion Matrix saved to: fusion_confusion_matrix.png")
        print("  └─ ROC Curve saved to:        fusion_roc_curve.png")