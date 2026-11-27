# Retrained / fine-tuned PRISM and the Christodoulou held-out split (2026-11-27, exploratory)

Asked by the PI (marked copy 2026-11-27: "show values with retraining or fine-tuning, compared to the literature";
"did you get a better result than this literature?"). PRISM's segmenter, 22 measurements (`PRISM_MASKS=brats24_22`).

## 1. External centres fitted three ways (`scripts/prism_retrained.py`)

Same ridge pipeline as the paper (`system._fit`). Trained = 5 x 5 patient-grouped, label-stratified CV within the
centre. Fine-tuned = all MU training scans + the centre's 4 training folds, scored on the held-out fold (same folds).
Mean AUC over repeats; 95% CI and paired difference vs the unchanged fit from 2,000 patient bootstrap samples.

UCSF-ALPTDG (69 scans, 29 progression, 69 patients):

| model | unchanged from MU | fine-tuned | trained at UCSF |
|---|---|---|---|
| combined | 0.81 (0.70-0.90) | 0.82 (0.71-0.91); +0.01 (-0.02 to +0.04) | 0.87 (0.78-0.94); +0.06 (-0.02 to +0.14) |
| imaging | 0.80 (0.68-0.89) | 0.82 (0.71-0.91); +0.03 (-0.00 to +0.06) | 0.85 (0.75-0.93); +0.05 (-0.03 to +0.14) |
| clinical history | 0.56 (0.42-0.69) | 0.55 (0.42-0.69) | 0.43 (0.33-0.54) |

Check: the unchanged combined fit reproduces the paper (0.81, 0.70-0.90).
LUMIERE (178 scans, 73 progression, 79 patients; data restored 2026-11-27, see /project/community/sbandred/lumiere/PROVENANCE.txt:
the pipeline reproduces all 178 saved LUMIERE scores exactly):

| model | unchanged from MU | fine-tuned | trained at LUMIERE |
|---|---|---|---|
| combined | 0.79 (0.71-0.86) | 0.80 (0.71-0.87); +0.005 (-0.03 to +0.04) | 0.76 (0.68-0.84); -0.03 (-0.10 to +0.04) |
| imaging | 0.69 (0.61-0.77) | 0.69 (0.61-0.77) | 0.68 (0.60-0.77) |
| clinical history | 0.69 (0.60-0.79) | 0.70 (0.62-0.79) | 0.66 (0.59-0.75) |

Literature: pooled AUC 0.91 at the developing institution, 0.81 at another (zhang2026meta).

## 2. The held-out set of Christodoulou et al. 2026 (`scripts/prism_christodoulou_split.py`)

Their split re-created from their public code (commit 643c888, `rank_and_split__4.py`: default_rng(42), 30 of the 203
patients of `dataset__2.xlsx`): 96 scans, 53 positive, as in their committed test set. Patient list:
`outputs/results/analyses/single_splits/christodoulou_test_patients.json`. 13 of the 30 are grade 4 patients with
evaluation scans here: 29 intended-use scans, 8 progression. Models fitted on the grade 4 training rows of the other
patients; our scan-level label (theirs is patient-level, so their 0.80 is on a different label).

| model | AUC (95% CI) |
|---|---|
| PRISM combined | 0.85 (0.69-0.98) |
| PRISM clinical history | 0.87 (0.76-1.00) |
| PRISM imaging | 0.83 (0.70-0.95) |
| published radiomics model, their code (400 Optuna trials), supplied masks | 0.59 (0.29-0.87) |

Reported by Christodoulou et al. on this set with their label: 0.80.
