# Detection at the scan: does this MRI show progression? (overnight study, 2026-10-21/22)

**Status: plan only.** Written and committed before any model in this study saw a real label. Code and results are
added below by the run, with any deviation labelled. Background: the forward 120-day task reaches 0.60 in the
intended use and is NO-GO for triage on MU alone ([TRIAGE_FEASIBILITY.md](TRIAGE_FEASIBILITY.md)); the published
0.80 on MU-Glioma-Post (Christodoulou 2026) and 0.81 on LUMIERE (Tikhonov 2025) address detection of progression at
the scan, not forward prediction ([COMPARABLE_RESULTS.md](../literature/COMPARABLE_RESULTS.md)).

## Plan (pre-specified)

**Unit and label (MU-Glioma-Post).** Scans from `diagnostics_imaging.scan_table` with complete sequences and a mask.
- Positive: the progression scan (`is_progression_scan`: first MRI with a mask on or after the documented
  progression date).
- Negative (primary): index scans whose 120-day label is a verified non-event (`label_120 == 0`), i.e. stable for at
  least 120 days afterwards. Secondary negative set: all index scans before progression whatever their follow-up.
- Population: grade 4 (primary); all gliomas secondary.
- **Primary evaluation set: the intended use**, scans on or after the documented RT start (as-of the scan day; as in
  [INTENDED_USE.md](INTENDED_USE.md)). Models are trained on all detection scans and evaluated on intended-use scans
  (primary) and on all scans (secondary). Within-phase AUCs are reported.
- Folds: the shared 5 × 5 folds (`outputs/data/folds.csv`); every scan inherits its patient's fold in each repeat.
  Patients absent from `folds.csv` (no index scan) are excluded and counted.
- No censoring: plain AUC with a paired patient-cluster bootstrap (1,000 draws), mean over repeats of pooled
  held-out AUC.

**Predictors (all as of the scan day; previous scans only from the past).**
- B0: clinical (age, sex, IDH, MGMT, with the C2 rules: no unknown indicators, markers masked before diagnosis).
- B1: B0 + timing and treatment as in C2 (the corrected core model's inputs). **Baseline.**
- **P (PRIMARY model): B1 + imaging measurements**: compartment volumes and morphology at the scan, change from the
  previous scan (log ratios, days between), and ratio to the smallest ET and lesion volume since RT end (nadir), with
  a has-previous flag. Ridge, every fitted step inside the training fold.
- P+R (secondary): P + radiomics, nested over the existing configurations.
- I (secondary): imaging measurements alone.

**Deep arms (GPU; fine-tuned SwinUNETR, hyperparameters and cross-fit stacking exactly as in
[FINETUNE_DEEP.md](FINETUNE_DEEP.md); score stacked onto B1).**
- G1: current scan. G2: siamese current + previous scan. G3: current scan plus subtraction channels (current minus
  previous, each sequence z-scored within the brain; images are SRI24-registered; zeros and a has-previous flag
  when there is no previous scan). G4: G1 with labels permuted within each outer training set (control).
- G5 (triage retest): G3's network on the forward 120-day label (index scans only), stacked onto C2, evaluated in the
  intended use exactly as in TRIAGE_FEASIBILITY.md.
- Priority if time runs short: G1, G4, G3, G5, G2; all gliomas last.

**External test (LUMIERE).** Locked transportable version of P trained on all MU detection scans (clinical, days since
surgery, the rater's "within 3 months after RT" flag, volumes and change; no treatment dates). Positive: first scan
rated progressive disease; negative: scans before it rated stable, partial or complete response. Plain AUC with a
patient bootstrap. Deep arms external only if time allows (secondary).

**Decision rules.**
1. **GO for a detection study** if, in grade 4 intended use, P reaches AUC ≥ 0.75 with lower 95% bound ≥ 0.65,
   **and** P − B1 ≥ +0.03 with CI excluding 0 (imaging adds beyond timing). Otherwise NO-GO for detection on MU
   alone. LUMIERE is reported as secondary; an external AUC below 0.65 is flagged as a transport failure.
2. Deep arms (secondary): an arm "adds" if its stack beats P by ≥ 0.03 with CI excluding 0.
3. G5 (triage): succeeds if C2 + G5 score − C2 ≥ +0.03 with CI excluding 0 in the intended use.
4. Validity: G4 image-only AUC CI covers 0.5; otherwise the deep arms are flagged.
5. Leakage: previous-scan features and subtraction channels use only scans dated before the scan; asserted in code.

**Known risk stated in advance.** Progression scans come later in the treatment course than most stable scans, so
timing alone may separate them (the phase-of-care problem again). That is why B1 is the baseline, P − B1 is part of
the GO rule, and the primary set is restricted to the intended use with within-phase AUCs reported.

## Results

Not run yet.
