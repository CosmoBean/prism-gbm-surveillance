# UCSF-ALPTDG: analysis plan (pre-specified)

**Written 2026-10-25, before any outcome model was fitted on UCSF.** Committed before the first run that reads UCSF
labels together with model scores. Anything added later is marked *exploratory* in the results files. Data
preparation is in [UCSF_DATA.md](UCSF_DATA.md) and [UCSF_IMAGING.md](UCSF_IMAGING.md). The labels were chosen by
Claude while the author was away (the author asked for all models to be run overnight). The author may change the
primary choice; every alternative below is computed anyway.

## Why the evaluation is restricted to scan 2

Every UCSF patient has one pair of consecutive scans. Under the primary label, positives can only be scan 2.
Anything that tells scan 1 from scan 2 would separate them by design, not biology:
- a has-previous flag;
- days since the previous scan;
- change features (zero at scan 1).

So the **primary evaluation set is scan 2 only**. Every scan there has exactly one previous scan, the change features
mean the same thing for every row, and has-previous is constant. All-scan analyses use only inputs that do not
encode the timepoint (single-scan images and clinical data), and they are secondary.

## Populations and labels

- **Population.**
  - Primary: grade 4, which matches MU's "grade4" population.
  - Sensitivity: WHO 2021 GBM.
  - Secondary: all gliomas, with the MU all-glioma-trained models.
- **Primary label** (`pos_s2_pm30` vs primary negatives):
  - positive = scan 2 with progression dated within ±30 d of it, and nearer scan 2 than scan 1;
  - negative = a scan with a progression ≥ 120 d later, or with ≥ 120 d of dated follow-up and no progression;
  - grade 4, scan 2: 29 positives and 40 negatives.
- **Sensitivity labels:**
  - `pos_s2_between`: progression between the scans or ≤ 30 d after scan 2;
  - verified-only negatives;
  - all scans with `pos_s2_pm30` + `pos_s1_at`, single-scan inputs only.
- **Imaging-defined reference:** `et_increased` on scan 2. This is circular for an image model. It is reported
  separately as an upper reference, never as the result.
- **120-day risk from scan 1** (secondary, the origin task):
  - positive = progression 1–120 d after scan 1;
  - negative = progression > 120 d after scan 1, or ≥ 120 d follow-up without progression;
  - scans with progression at scan 1 excluded.

## Metrics

Plain AUC with a patient-cluster bootstrap (1,000 draws, seed 20261025) and paired contrasts on the same draws.
Calibration slope and O/E are reported for the locked models only, as secondary. The transport-failure flag is AUC
< 0.65, as for LUMIERE. Within phase: almost all UCSF scans are later post-RT (plausible phase from the RT start
only), so the later-post-RT subset is the within-phase analogue.

## Part A. Locked MU models (external test, no refit on UCSF)

Each model is fitted once on the MU detection training rows (positives + primary negatives, all phases) with the
verified ridge pipeline of `prism.analyses.detection`, and applied once to UCSF:

| arm | inputs | applies to UCSF |
|---|---|---|
| A-B0 | clinical: age, sex, IDH, MGMT (C2 rules) | exactly |
| A-Iscan | volumes + morphology / relative intensity at the scan | exactly |
| A-Ipure | A-Iscan + log volume ratios to the previous scan + ratio to the smallest volume over the history | history truncated to one previous scan |
| A-B0+Iscan, A-B0+Ipure | clinical + images, no timeline | as above |
| A-Timg | LUMIERE image set: ET, necrosis + cavity, oedema volumes, ratios to previous | as above |
| A-Tbase, A-T | LUMIERE transportable models: days since surgery and an early post-RT flag (approximate on UCSF, from the RT start + 6 weeks) | approximate; secondary |

- **Primary questions:** A-Ipure and A-Iscan on grade-4 scan 2. A-B0+Ipure − A-B0 tells what images add to
  clinical data, and A-T − A-Tbase tells what images add to the transportable timeline.
- The full MU timeline model (B1) cannot be built: there is no RT end date, dose or visit history.

## Part B. Trained on UCSF (internal)

Same arms and ridge pipeline, trained on UCSF. Repeated patient-grouped, label-stratified cross-validation, 5 × 5,
seeds fixed before the run. Evaluated on the same sets as Part A. Added arm:

- **B-Tl, the UCSF timeline:** clinical + days from diagnosis + days from RT start + chemo started + on treatment +
  surgeries before the scan + days since the previous scan.
- **B-Tl+Ipure.**

Also reported: UCSF's own TRAIN / TEST split as a single-split result, beside the repeated-CV distribution. This
repeats on new data the split-variance point made on MU.

## Part C. Deep networks (one GPU, in this order of priority)

The networks and hyperparameters are `prism.analyses.finetune_detection` / `finetune_deep` (SwinUNETR, BraTS21
weights, frozen stages 1–2), unchanged unless they cannot run on UCSF.

1. **C-locked:** the MU-trained detection networks (G1 current scan; G2 siamese; G3 difference input), applied
   unchanged to UCSF scan 2. Ensemble of the saved MU networks.
2. **C-ucsf:** trained on UCSF only from the BraTS21 weights: G1 and G3, and G4 (G1 with permuted labels, the
   validity control). Patient-grouped 5-fold cross-fitting, as many repeats as time allows (at least 1).
3. **C-transfer:** fine-tuned on UCSF from the MU-trained G1 network.
4. Image-only AUC, and each score stacked onto A-B0 and B-Tl inside the cross-validation.

- **Validity:** G4's interval must cover 0.5.
- **Sensitivity:** exclude the 60 patients also in UCSF-PDGM (their pre-operative scans may be in BraTS).

## Decisions fixed in advance

- **Q1. Do MU-trained image measurements transport to UCSF?** A-Ipure on grade-4 scan 2, AUC ≥ 0.65 with a lower
  bound above 0.5.
- **Q2. Do images add to clinical data where there is no timeline?** A-B0+Ipure − A-B0, CI excluding 0.
- **Q3. Does training on UCSF beat the locked MU model?** B-Ipure − A-Ipure on the same rows (descriptive; same rows
  but out-of-fold).
- **Q4. Do deep networks learn on UCSF?** C-ucsf G1 or G3 above G4, with G4 covering 0.5.

Results go to `docs/results/UCSF_RESULTS.md` and `outputs/results/analyses/ucsf/`.
