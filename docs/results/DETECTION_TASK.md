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

Stream A (tabular arms, LUMIERE, deep-arm evaluation helper), run 2026-10-21 on CPU. Code:
`prism/analyses/detection.py` (`python -m prism detection [--workers 48] [--n-boot 1000]`, about 3.5 min; a rerun
gave byte-identical tables). Outputs: `outputs/results/analyses/detection/` (auc.csv, contrasts.csv,
within_phase.csv, rule.csv, lumiere*.csv, checks.csv, nested_radiomics_choices.csv, oof_<pop>_<negset>.csv.gz,
PLAN_snapshot.md, run_info.json). The cohort file for both streams is `outputs/data/detection_cohort.csv`, with
definitions and counts in `outputs/data/detection_cohort_README.md`. It was written before any model was fitted.

### Cohort

| population | set | progression scans | primary negatives (label_120 = 0) | secondary negatives (all index scans) | patients |
|---|---|---|---|---|---|
| grade 4 | all scans | 64 | 117 | 249 | 126 |
| grade 4 | intended use | 62 | 84 | 173 | 88 |
| all gliomas | all scans | 73 | 156 | 308 | 155 |
| all gliomas | intended use | 64 | 98 | 193 | 97 |

- There are 120 progression scans with complete sequences and a mask. 47 of them, from 47 patients (42 grade 4),
  belong to patients with no index scan, so those patients are absent from `folds.csv` and were excluded.
- In grade 4, only 2 of 64 positives are pre-RT, so the intended use keeps almost every positive.
- Grade-4 intended-use primary set, by phase (positives / negatives): during RT 2 / 1, early post-RT 4 / 51, later
  post-RT 56 / 32. Positives sit almost entirely in the later post-RT phase and negatives mostly in the early
  post-RT phase. This is the phase-of-care risk stated in advance.

Checks (`checks.csv`):
- For the index-scan rows of the detection frame, the B1 design equals `phase_censoring.arm_design("C2")` on
  mu_cohort exactly (max deviation 0, same missingness), in both populations. So the progression-scan rows are built
  with the same rules.
- Leakage (rule 5): every scan's previous-scan and nadir features were recomputed with all of that patient's later
  scans deleted. The maximum deviation was 0 in both populations, and the code asserts it. The previous scan is
  always strictly earlier (asserted) and equals the cohort file's `prev_scan_id` (asserted).

### Primary: grade 4, trained on all detection scans (primary negatives), evaluated in the intended use

Plain AUC is the mean over 5 repeats of the pooled held-out AUC. The 95% CI comes from a patient-cluster bootstrap
with 1,000 paired draws.

| evaluation set | pos/neg/patients | B0 | B1 (baseline) | **P (primary)** | P+R | I |
|---|---|---|---|---|---|---|
| **grade 4, intended use** | 62/84/80 | 0.530 (0.450–0.606) | 0.822 (0.749–0.902) | **0.837 (0.763–0.904)** | 0.833 (0.765–0.897) | 0.806 (0.747–0.865) |
| grade 4, all scans | 64/117/92 | 0.514 (0.447–0.579) | 0.845 (0.781–0.906) | 0.859 (0.805–0.909) | 0.855 (0.804–0.902) | 0.822 (0.774–0.875) |
| grade 4, intended use, secondary negatives | 62/173/88 | 0.511 (0.468–0.554) | 0.807 (0.759–0.858) | 0.802 (0.759–0.845) | 0.796 (0.754–0.841) | 0.764 (0.715–0.813) |
| grade 4, all scans, secondary negatives | 64/249/126 | 0.480 (0.437–0.523) | 0.836 (0.793–0.881) | 0.837 (0.799–0.874) | 0.832 (0.795–0.869) | 0.793 (0.749–0.835) |
| grade 4, trained + evaluated on secondary negatives, intended use | 62/173/88 | 0.488 (0.452–0.523) | 0.815 (0.767–0.868) | 0.815 (0.766–0.865) | – | 0.777 (0.731–0.827) |
| all gliomas, intended use | 64/98/87 | 0.573 (0.503–0.644) | 0.814 (0.737–0.888) | 0.851 (0.789–0.908) | 0.840 (0.777–0.899) | 0.837 (0.784–0.889) |
| all gliomas, all scans | 73/156/114 | 0.557 (0.495–0.622) | 0.814 (0.754–0.869) | 0.855 (0.804–0.902) | 0.844 (0.794–0.890) | 0.854 (0.809–0.896) |
| all gliomas, intended use, secondary negatives | 64/193/97 | 0.545 (0.499–0.594) | 0.796 (0.749–0.845) | 0.814 (0.769–0.862) | 0.802 (0.757–0.849) | 0.793 (0.748–0.841) |

Paired contrasts (ΔAUC, 95% CI). "Phase-stratified" pools only case-control pairs from the same phase.

| evaluation set | **P − B1** | P − B1 phase-stratified | P+R − P | B1 − B0 | I − B1 |
|---|---|---|---|---|---|
| **grade 4, intended use** | **+0.015 (−0.032 to +0.063)** | +0.019 (−0.079 to +0.124) | −0.004 (−0.017 to +0.012) | +0.292 (+0.200 to +0.398) | −0.016 (−0.095 to +0.061) |
| grade 4, all scans | +0.014 (−0.025 to +0.050) | +0.024 (−0.080 to +0.122) | −0.004 (−0.015 to +0.007) | +0.330 (+0.242 to +0.429) | −0.023 (−0.096 to +0.041) |
| grade 4, intended use, secondary negatives | −0.005 (−0.049 to +0.040) | +0.010 (−0.069 to +0.092) | −0.005 (−0.015 to +0.004) | +0.296 (+0.240 to +0.362) | −0.043 (−0.108 to +0.021) |
| grade 4, trained on secondary, intended use | +0.000 (−0.040 to +0.039) | +0.006 (−0.070 to +0.086) | – | +0.326 (+0.275 to +0.384) | −0.037 (−0.099 to +0.027) |
| all gliomas, intended use | +0.036 (−0.014 to +0.085) | +0.057 (−0.044 to +0.163) | −0.011 (−0.022 to +0.000) | +0.241 (+0.152 to +0.328) | +0.022 (−0.057 to +0.096) |
| all gliomas, all scans | +0.041 (+0.006 to +0.081) | +0.073 (−0.016 to +0.162) | −0.011 (−0.022 to −0.001) | +0.257 (+0.186 to +0.333) | +0.039 (−0.015 to +0.098) |

### Decision rule 1: NO-GO for a detection study on MU alone

- P in grade 4, intended use: **0.837 (0.763–0.904)**. This meets the first condition (≥ 0.75, lower bound ≥ 0.65).
- **P − B1 = +0.015 (−0.032 to +0.063)**. This fails the second condition (≥ +0.03 with a CI excluding 0).
- Imaging adds nothing measurable beyond timing and treatment. Timing and treatment alone (B1) already reach 0.822.
  Clinical inputs alone (B0) give 0.530.
- With secondary negatives, P − B1 is −0.005 to +0.001. In all gliomas (secondary), P − B1 = +0.036 (−0.014 to +0.085)
  in the intended use, still not excluding 0.
- Radiomics adds nothing: P+R − P = −0.004 (−0.017 to +0.012). The nested choice varied across splits; the most
  frequent pick was v2_lesion / pca10 / stack, 6 of 25.

### Within-phase (grade 4, intended use, primary set)

| phase | pos/neg | B0 | B1 | P | P+R | I |
|---|---|---|---|---|---|---|
| during RT | 2/1 | 0.000 (descriptive) | 0.800 (descr.) | 1.000 (descr.) | 1.000 (descr.) | 1.000 (descr.) |
| early post-RT | 4/51 | 0.559 (descr.) | 0.664 (descr.) | 0.975 (descr.) | 0.973 (descr.) | 0.989 (descr.) |
| later post-RT | 56/32 | 0.530 (0.386–0.669) | 0.638 (0.488–0.799) | 0.623 (0.484–0.762) | 0.629 (0.502–0.748) | 0.627 (0.523–0.720) |
| phase-stratified (pooled within-phase pairs) | 62/84 | 0.532 (0.400–0.655) | 0.640 (0.508–0.784) | 0.659 (0.538–0.787) | 0.665 (0.554–0.776) | 0.664 (0.576–0.750) |

- A stratum gets a CI only with ≥ 10 positives and ≥ 10 negatives. Otherwise it is descriptive.
- Inside the only phase large enough to evaluate (later post-RT), every arm is around 0.62–0.64. No arm's lower bound
  clears 0.5 by much.
- All gliomas, later post-RT (58/40): P 0.672 (0.547–0.785), I 0.696 (0.601–0.780), B1 0.644 (0.511–0.784).

### External test (LUMIERE, locked)

- The transportable version of P is called T. Its inputs:
  - age, sex, IDH, MGMT (unknown coded 0, no indicators)
  - log days since surgery
  - the as-of early post-RT flag (on LUMIERE, the rater's "LessThan3Months" flag)
  - harmonised volumes (ET, necrosis + cavity, oedema)
  - log ratios of those volumes to the previous scan, log days since the previous scan, and a has-previous flag
- It was fitted once on the MU grade-4 detection training rows (positives and primary negatives, all phases) and
  applied once to LUMIERE.
- LUMIERE positive: first scan rated PD. Negatives: earlier scans rated SD, PR or CR. That gives 73 positives,
  105 negatives and 79 patients. 24 patients contribute only a positive, 15 scans lack a usable DeepBraTumIA
  segmentation (imputed by the locked pipeline), and 168 of 178 scans have a previous post-operative scan.
- Tbase is the same model without imaging. It is an added reference (see the deviations list).
- Plain AUC with a patient bootstrap (1,000 draws):

| arm | LUMIERE AUC | MU internal (grade 4, intended use) |
|---|---|---|
| **T (grade-4 trained)** | **0.773 (0.679–0.857)** | 0.804 (0.731–0.885) |
| Tbase (no imaging) | 0.689 (0.600–0.805) | 0.757 (0.678–0.846) |
| T − Tbase | +0.084 (−0.006 to +0.164) | +0.046 (−0.011 to +0.106) |
| T (all-glioma trained, sensitivity) | 0.768 (0.670–0.857) | – |
| T, LUMIERE scans with rater flag "< 3 months after RT" = 0 (72/78) | 0.715 (0.597–0.815); T − Tbase +0.125 (+0.007 to +0.232) | – |

There is no transport failure: the external AUC is ≥ 0.65 and the lower bound is 0.679. On LUMIERE, the strongest
single inputs are log ET volume (0.662), log oedema volume (0.657) and the oedema / ET change from the previous scan
(0.646 / 0.628). Log days since surgery gives 0.608.

### Deep arms (stream B): file format and status

- **Not run.** When the tabular part finished, no `outputs/results/analyses/detection/deep/<arm>/scores.csv`
  existed yet.
- To run the evaluation once stream B's files exist: `python -m prism detection --deep-only [--n-boot 1000]`. This
  uses the tabular OOF files written above.
- The helper was tested on synthetic score files:
  - an uninformative score gives an image-only AUC of 0.50 and a stack equal to B1;
  - a label-correlated score raises the stack;
  - for G5, uninformative scores give C2+score ≈ C2.

**File format** (`outputs/results/analyses/detection/deep/<arm>/scores.csv`, one row per scored scan per network):

| column | meaning |
|---|---|
| scan_id | detection_cohort.csv scan_id (for G5: mu_cohort scan_id) |
| repeat | 0–4, repeat of the shared folds (detection_cohort `fold_r<repeat>`) |
| fold | 0–4, outer test fold k |
| inner | 0–3, inner network j within outer split (repeat, fold) |
| is_test | 1 = the scan is in outer fold k (test); 0 = the scan is in inner hold-out fold j of the outer training rows |
| logit | the network's logit for the scan (after TTA) |

Rules the reader asserts:
- A test row must lie in outer fold k. The test logit is the mean over the inner networks.
- Each training row must be scored by exactly one inner network (its inner OOF logit) and lie outside fold k.
- Every outer-training row with a training label (label_det = 1 or neg_primary; for G5, verified label_120) must
  have an inner OOF logit.
- The population is grade 4 if all scan_ids are grade 4, otherwise all gliomas.
- Test rows should cover every detection scan of the outer fold (positives and all index scans) so that the
  secondary-negative sets can be evaluated. Scans without a test logit are dropped from the evaluation sets.

Stacking:
- `finetune_deep.stack_predict` unchanged. The score is z-scored with the mean / SD of its inner-OOF values on the
  outer training rows, appended to BASE_PRE(B1), and the verified ridge is refitted.
- Outputs go to `deep/<arm>/{auc,contrasts,within_phase}.csv` and `deep/summary_contrasts.csv`. They give B1 + score
  vs P (rule 2) and vs B1, and the image-only AUC (`<arm>_image`; rule 4 for G4: the CI must cover 0.5).
- An arm whose name starts with `G5` is the triage retest. It is stacked onto C2 on the grade-4 mu_cohort and
  evaluated with `evaluate_repeated` (IPCW AUC(120 d), reference C2) in the intended use. This is exactly
  TRIAGE_FEASIBILITY.md's estimator (rule 3), written to `deep/G5*/triage_eval.csv`.

### Surprises

1. **Timing alone almost solves the task on MU.**
   - B1, with no image, reaches 0.822 in the intended use.
   - Single inputs: visit index 0.775, days since RT end 0.765, days from diagnosis 0.742. ET log ratio to the nadir
     gives 0.698 and log ET volume 0.622.
   - Positives are late in the course (56 of 62 later post-RT); 51 of 84 verified-stable negatives are early post-RT.
     The verified 120-day non-event also selects scans with ≥ 120 days of follow-up, which by construction are not a
     patient's last scan.
   - The headline AUC of 0.84 is therefore mostly phase of care. Within later post-RT every arm is about 0.62–0.64.
2. **Imaging carries within-phase signal that is not significantly better than timing.**
   - Phase-stratified AUC: I 0.664, P 0.659, B1 0.640.
   - In the 55 early post-RT scans, imaging separates the 4 progressions almost perfectly (P 0.975, descriptive).
     These cases are too few to interpret.
3. **Scans with a previous scan** (grade 4, intended use, 62/46): P 0.707 (0.596–0.807), B1 0.703. Change features do
   not rescue the contrast (P − B1 +0.003).
4. **LUMIERE behaves differently.** LUMIERE has no treatment dates, so the no-imaging reference is weaker
   (Tbase 0.689), and imaging adds more (+0.084, CI just covering 0). Outside the rater's early post-RT window it adds
   +0.125 (+0.007 to +0.232).
   - The locked T transports without loss: 0.773 on LUMIERE vs 0.804 internally.
   - LUMIERE negatives are rating-defined (SD/PR/CR), not 120-day verified, and positives include 24 patients with no
     negative scan. So the external estimate is not the same estimand as the MU primary.
5. Nested radiomics is consistently neutral to slightly negative (−0.004 to −0.014), as in the forward task.

### Deviations and specification details

- **DEVIATION (LUMIERE training population):**
  - The plan says the locked model is "trained on all MU detection scans". The headline uses the grade-4 MU
    detection training rows (positives and primary negatives, all phases), because LUMIERE is grade 4 and the
    primary population is grade 4.
  - The all-glioma-trained model is reported alongside: 0.768 vs 0.773, same verdict.
- **DEVIATION (added reference arms, EXPLORATORY):**
  - Tbase (the transportable model without imaging) and the internal CV of T and Tbase are not in the plan. They
    were added to tell whether imaging adds on LUMIERE.
  - The "intended use with a previous scan" subset is also an addition.
  - Neither enters a decision rule.
- **DEVIATION (P+R scope):** P+R was run only with primary negatives (both populations). It was not refitted on
  the secondary negatives. Its primary-trained OOF predictions are scored on the secondary sets.
- Specification details, all fixed before results were seen and not changes to the plan:
  - **Secondary negative set:** reported two ways. (a) The primary-trained models scored on all index scans.
    (b) Models refitted with all index scans as negatives.
  - **Imaging measurements in P and I:**
    - `measurement_groups` volumes (log cc for ET, NETC, SNFH, RC, tumour, lesion);
    - its "morphology" block, which in this repo also holds the relative T1c / FLAIR intensities;
    - log ratios of the 6 volumes to the previous complete, masked MRI, log days since it, and a has-previous flag
      (0 when there is no previous scan);
    - log ratio of ET and lesion volume to the nadir. The nadir window comes from
      `triage_feasibility.nadir_window_start`: since RT end once RT is completed, since RT start during RT, and the
      whole history before RT.
  - **Ridge:** c3 BASE_PRE with the verified ridge (`c3.fit_predict`), seed = repeat.
  - **Within-phase CIs:** only for strata with ≥ 10 positives and ≥ 10 negatives (`phase_censoring.MIN_STRATUM`).
  - **LUMIERE previous scan:** the most recent strictly earlier study not rated Pre-Op with a usable segmentation.

### EXPLORATORY (post hoc, 2026-10-22): how much of "imaging only" (I) is imaging?

Added after the results, not prespecified. I contains three inputs that encode timing rather than the image: days
since the previous scan, the has-previous flag, and a nadir window that starts at the documented RT start or end. On
their own in the grade-4 intended use: days since previous 0.740, has-previous 0.726. Re-run with pure image inputs
(`scripts/exploratory_pure_imaging_detection.py`; same folds, ridge, bootstrap):
- **I_scan:** volumes + morphology / relative intensities at the scan only.
- **I_pure:** I_scan + log volume ratios to the previous scan (0 if none) + ET / lesion ratio to the smallest volume
  over the whole history (no RT-dependent window). No days, no flags.

Grade 4, intended use, primary negatives (62/84, 80 patients):

| arm | AUC (95% CI) | later post-RT (56/32) | phase-stratified |
|---|---|---|---|
| B1 (timing + treatment + clinical) | 0.822 (0.749–0.902) | 0.638 (0.488–0.799) | 0.640 (0.508–0.784) |
| I (as run) | 0.806 (0.747–0.865) | 0.627 (0.523–0.720) | 0.664 (0.576–0.750) |
| **I_pure** | **0.709 (0.630–0.781)** | 0.650 (0.541–0.742) | **0.677 (0.580–0.767)** |
| I_scan | 0.659 (0.567–0.733) | 0.655 (0.542–0.755) | 0.680 (0.573–0.777) |
| B1 + I_pure | 0.821 (0.744–0.894) | 0.622 (0.477–0.771) | 0.654 (0.527–0.790) |

Contrasts: I − I_pure +0.097 (+0.047 to +0.153) overall but −0.013 (−0.057 to +0.037) within phase, so the extra
0.10 of I was timing. I_pure − B1 −0.113 (−0.227 to −0.012) overall, +0.037 (−0.150 to +0.194) within phase.
B1 + I_pure − B1 −0.001 (−0.052 to +0.046). All scans gives the same picture (I_pure 0.712).

Reading: images alone detect progression at about 0.71 and, compared within a phase of care, at about 0.68, at least
as well as timing within a phase (0.64). Timing wins across phases (0.82) because progression scans come late. The
two views overlap: combining them does not beat timing.
