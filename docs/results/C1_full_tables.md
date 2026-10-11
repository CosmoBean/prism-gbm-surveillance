# C1 — outcome formulation results (final)

> **Final numbers.** Copy of `outputs/results/c1/c1_summary.md` from the final full re-run (2026-10-11 05:32, label-fixed cohort:
> 308 scans / 155 patients, grade 4 249 / 126). Supersedes the earlier tables (253 grade-4 scans, repeat-averaged estimator).

5×5 repeated patient-grouped CV; every metric is the mean over the 5 repeats of the metric of that repeat's pooled out-of-fold predictions. 95% CIs from a patient-cluster bootstrap of that mean; ΔAUC (point estimate, paired bootstrap CI) vs the naive formulation. Last column: AUC of the repeat-averaged prediction (earlier headline, optimistic).

## grade4 · volumes_clinical · H = 90 d  (scans 249, patients 126, positives 62, censored 35)

| Formulation | AUC(H) IPCW | ΔAUC vs naive | Brier(H) IPCW | AUC verified | AUC naive label | O/E | Cal. slope | AUC of averaged |
|---|---|---|---|---|---|---|---|---|
| naive | 0.688 [0.601, 0.769] | — | 0.184 [0.154, 0.221] | 0.689 | 0.675 | 1.12 | 0.99 | 0.697 |
| verified | 0.694 [0.606, 0.774] | +0.006 [-0.010, +0.024] | 0.184 [0.156, 0.216] | 0.695 | 0.679 | 0.95 | 0.89 | 0.700 |
| ipcw | 0.694 [0.606, 0.773] | +0.006 [-0.011, +0.024] | 0.184 [0.156, 0.216] | 0.695 | 0.679 | 0.96 | 0.89 | 0.699 |
| hazard | 0.700 [0.615, 0.775] | +0.012 [-0.008, +0.033] | 0.189 [0.159, 0.221] | 0.700 | 0.686 | 0.85 | 0.66 | 0.705 |

## grade4 · volumes_clinical · H = 120 d  (scans 249, patients 126, positives 93, censored 39)

| Formulation | AUC(H) IPCW | ΔAUC vs naive | Brier(H) IPCW | AUC verified | AUC naive label | O/E | Cal. slope | AUC of averaged |
|---|---|---|---|---|---|---|---|---|
| naive | 0.651 [0.567, 0.727] | — | 0.230 [0.207, 0.256] | 0.652 | 0.631 | 1.14 | 0.95 | 0.656 |
| verified | 0.657 [0.577, 0.732] | +0.006 [-0.020, +0.030] | 0.227 [0.208, 0.247] | 0.657 | 0.634 | 0.95 | 0.91 | 0.662 |
| ipcw | 0.656 [0.578, 0.731] | +0.005 [-0.021, +0.029] | 0.227 [0.208, 0.247] | 0.657 | 0.634 | 0.97 | 0.92 | 0.662 |
| hazard | 0.653 [0.574, 0.726] | +0.002 [-0.018, +0.022] | 0.242 [0.211, 0.272] | 0.654 | 0.634 | 0.87 | 0.50 | 0.663 |

## grade4 · volumes_clinical · H = 180 d  (scans 249, patients 126, positives 131, censored 43)

| Formulation | AUC(H) IPCW | ΔAUC vs naive | Brier(H) IPCW | AUC verified | AUC naive label | O/E | Cal. slope | AUC of averaged |
|---|---|---|---|---|---|---|---|---|
| naive | 0.610 [0.506, 0.710] | — | 0.236 [0.215, 0.257] | 0.612 | 0.590 | 1.16 | 0.63 | 0.616 |
| verified | 0.619 [0.524, 0.710] | +0.008 [-0.037, +0.053] | 0.231 [0.197, 0.262] | 0.620 | 0.592 | 0.96 | 0.58 | 0.629 |
| ipcw | 0.619 [0.524, 0.711] | +0.009 [-0.036, +0.053] | 0.230 [0.198, 0.260] | 0.621 | 0.592 | 0.98 | 0.59 | 0.629 |
| hazard | 0.643 [0.545, 0.736] | +0.033 [-0.011, +0.077] | 0.232 [0.188, 0.278] | 0.645 | 0.610 | 0.93 | 0.40 | 0.651 |

## grade4 · radiomics_clinical · H = 90 d  (scans 249, patients 126, positives 62, censored 35)

| Formulation | AUC(H) IPCW | ΔAUC vs naive | Brier(H) IPCW | AUC verified | AUC naive label | O/E | Cal. slope | AUC of averaged |
|---|---|---|---|---|---|---|---|---|
| naive | 0.684 [0.593, 0.766] | — | 0.193 [0.158, 0.230] | 0.684 | 0.676 | 1.13 | 0.56 | 0.692 |
| verified | 0.690 [0.612, 0.768] | +0.007 [-0.011, +0.027] | 0.193 [0.160, 0.228] | 0.691 | 0.680 | 0.97 | 0.56 | 0.692 |
| ipcw | 0.691 [0.612, 0.768] | +0.007 [-0.011, +0.026] | 0.192 [0.160, 0.227] | 0.691 | 0.680 | 0.98 | 0.56 | 0.693 |
| hazard | 0.690 [0.605, 0.767] | +0.006 [-0.035, +0.049] | 0.209 [0.176, 0.248] | 0.690 | 0.686 | 0.86 | 0.35 | 0.695 |

## grade4 · radiomics_clinical · H = 120 d  (scans 249, patients 126, positives 93, censored 39)

| Formulation | AUC(H) IPCW | ΔAUC vs naive | Brier(H) IPCW | AUC verified | AUC naive label | O/E | Cal. slope | AUC of averaged |
|---|---|---|---|---|---|---|---|---|
| naive | 0.648 [0.553, 0.736] | — | 0.239 [0.208, 0.271] | 0.647 | 0.643 | 1.13 | 0.52 | 0.652 |
| verified | 0.655 [0.575, 0.730] | +0.007 [-0.021, +0.038] | 0.237 [0.210, 0.266] | 0.655 | 0.643 | 0.96 | 0.51 | 0.658 |
| ipcw | 0.654 [0.575, 0.730] | +0.006 [-0.022, +0.036] | 0.237 [0.209, 0.265] | 0.654 | 0.642 | 0.98 | 0.51 | 0.659 |
| hazard | 0.669 [0.583, 0.746] | +0.021 [-0.027, +0.068] | 0.250 [0.211, 0.289] | 0.670 | 0.665 | 0.90 | 0.33 | 0.681 |

## grade4 · radiomics_clinical · H = 180 d  (scans 249, patients 126, positives 131, censored 43)

| Formulation | AUC(H) IPCW | ΔAUC vs naive | Brier(H) IPCW | AUC verified | AUC naive label | O/E | Cal. slope | AUC of averaged |
|---|---|---|---|---|---|---|---|---|
| naive | 0.660 [0.553, 0.762] | — | 0.231 [0.197, 0.267] | 0.662 | 0.639 | 1.16 | 0.52 | 0.669 |
| verified | 0.672 [0.585, 0.752] | +0.011 [-0.046, +0.078] | 0.224 [0.185, 0.262] | 0.673 | 0.643 | 0.97 | 0.42 | 0.683 |
| ipcw | 0.671 [0.585, 0.752] | +0.011 [-0.048, +0.078] | 0.224 [0.186, 0.261] | 0.672 | 0.643 | 0.98 | 0.42 | 0.683 |
| hazard | 0.684 [0.591, 0.770] | +0.024 [-0.044, +0.078] | 0.228 [0.178, 0.275] | 0.686 | 0.669 | 0.95 | 0.30 | 0.700 |

## all_glioma · volumes_clinical · H = 90 d  (scans 308, patients 155, positives 65, censored 48)

| Formulation | AUC(H) IPCW | ΔAUC vs naive | Brier(H) IPCW | AUC verified | AUC naive label | O/E | Cal. slope | AUC of averaged |
|---|---|---|---|---|---|---|---|---|
| naive | 0.732 [0.657, 0.801] | — | 0.163 [0.132, 0.194] | 0.733 | 0.717 | 1.13 | 1.00 | 0.737 |
| verified | 0.732 [0.657, 0.805] | +0.000 [-0.013, +0.014] | 0.162 [0.135, 0.189] | 0.733 | 0.717 | 0.95 | 0.90 | 0.735 |
| ipcw | 0.732 [0.657, 0.805] | +0.000 [-0.013, +0.014] | 0.161 [0.134, 0.189] | 0.733 | 0.717 | 0.97 | 0.91 | 0.735 |
| hazard | 0.735 [0.660, 0.809] | +0.003 [-0.012, +0.018] | 0.164 [0.137, 0.194] | 0.735 | 0.723 | 0.89 | 0.71 | 0.739 |

## all_glioma · volumes_clinical · H = 120 d  (scans 308, patients 155, positives 100, censored 52)

| Formulation | AUC(H) IPCW | ΔAUC vs naive | Brier(H) IPCW | AUC verified | AUC naive label | O/E | Cal. slope | AUC of averaged |
|---|---|---|---|---|---|---|---|---|
| naive | 0.689 [0.611, 0.756] | — | 0.214 [0.189, 0.242] | 0.689 | 0.665 | 1.15 | 0.97 | 0.697 |
| verified | 0.690 [0.612, 0.758] | +0.002 [-0.016, +0.018] | 0.212 [0.189, 0.235] | 0.691 | 0.670 | 0.96 | 0.90 | 0.696 |
| ipcw | 0.690 [0.612, 0.758] | +0.002 [-0.016, +0.019] | 0.211 [0.189, 0.236] | 0.691 | 0.669 | 0.97 | 0.91 | 0.695 |
| hazard | 0.698 [0.619, 0.767] | +0.009 [-0.003, +0.020] | 0.216 [0.189, 0.246] | 0.698 | 0.683 | 0.91 | 0.62 | 0.703 |

## all_glioma · volumes_clinical · H = 180 d  (scans 308, patients 155, positives 144, censored 59)

| Formulation | AUC(H) IPCW | ΔAUC vs naive | Brier(H) IPCW | AUC verified | AUC naive label | O/E | Cal. slope | AUC of averaged |
|---|---|---|---|---|---|---|---|---|
| naive | 0.702 [0.613, 0.776] | — | 0.223 [0.204, 0.243] | 0.703 | 0.664 | 1.18 | 1.11 | 0.705 |
| verified | 0.691 [0.601, 0.767] | -0.011 [-0.037, +0.016] | 0.219 [0.190, 0.250] | 0.693 | 0.660 | 0.96 | 0.80 | 0.693 |
| ipcw | 0.692 [0.601, 0.769] | -0.010 [-0.036, +0.017] | 0.218 [0.191, 0.248] | 0.693 | 0.660 | 0.99 | 0.81 | 0.695 |
| hazard | 0.708 [0.620, 0.782] | +0.006 [-0.012, +0.027] | 0.219 [0.184, 0.257] | 0.710 | 0.676 | 0.95 | 0.57 | 0.712 |

## all_glioma · radiomics_clinical · H = 90 d  (scans 308, patients 155, positives 65, censored 48)

| Formulation | AUC(H) IPCW | ΔAUC vs naive | Brier(H) IPCW | AUC verified | AUC naive label | O/E | Cal. slope | AUC of averaged |
|---|---|---|---|---|---|---|---|---|
| naive | 0.736 [0.666, 0.800] | — | 0.167 [0.134, 0.198] | 0.736 | 0.723 | 1.16 | 0.74 | 0.743 |
| verified | 0.737 [0.668, 0.800] | +0.001 [-0.013, +0.017] | 0.168 [0.138, 0.197] | 0.738 | 0.724 | 0.97 | 0.69 | 0.744 |
| ipcw | 0.737 [0.668, 0.800] | +0.002 [-0.013, +0.017] | 0.167 [0.138, 0.196] | 0.738 | 0.724 | 0.99 | 0.69 | 0.744 |
| hazard | 0.736 [0.671, 0.802] | +0.000 [-0.036, +0.035] | 0.174 [0.144, 0.208] | 0.737 | 0.736 | 0.91 | 0.52 | 0.746 |

## all_glioma · radiomics_clinical · H = 120 d  (scans 308, patients 155, positives 100, censored 52)

| Formulation | AUC(H) IPCW | ΔAUC vs naive | Brier(H) IPCW | AUC verified | AUC naive label | O/E | Cal. slope | AUC of averaged |
|---|---|---|---|---|---|---|---|---|
| naive | 0.721 [0.658, 0.780] | — | 0.209 [0.182, 0.239] | 0.721 | 0.709 | 1.17 | 0.78 | 0.725 |
| verified | 0.727 [0.667, 0.786] | +0.006 [-0.011, +0.022] | 0.207 [0.181, 0.232] | 0.727 | 0.708 | 0.98 | 0.70 | 0.729 |
| ipcw | 0.726 [0.666, 0.785] | +0.005 [-0.011, +0.021] | 0.207 [0.181, 0.233] | 0.726 | 0.708 | 0.99 | 0.71 | 0.729 |
| hazard | 0.724 [0.656, 0.787] | +0.004 [-0.027, +0.034] | 0.215 [0.185, 0.247] | 0.724 | 0.724 | 0.95 | 0.50 | 0.731 |

## all_glioma · radiomics_clinical · H = 180 d  (scans 308, patients 155, positives 144, censored 59)

| Formulation | AUC(H) IPCW | ΔAUC vs naive | Brier(H) IPCW | AUC verified | AUC naive label | O/E | Cal. slope | AUC of averaged |
|---|---|---|---|---|---|---|---|---|
| naive | 0.741 [0.663, 0.809] | — | 0.211 [0.186, 0.240] | 0.743 | 0.711 | 1.19 | 0.83 | 0.752 |
| verified | 0.744 [0.669, 0.803] | +0.003 [-0.020, +0.027] | 0.205 [0.176, 0.240] | 0.746 | 0.708 | 0.97 | 0.70 | 0.751 |
| ipcw | 0.743 [0.669, 0.802] | +0.002 [-0.021, +0.027] | 0.205 [0.177, 0.239] | 0.745 | 0.708 | 0.99 | 0.71 | 0.750 |
| hazard | 0.750 [0.676, 0.814] | +0.009 [-0.028, +0.043] | 0.206 [0.170, 0.246] | 0.752 | 0.733 | 0.98 | 0.52 | 0.761 |
