# Triage feasibility on the existing data: longitudinal volume trajectory (T1) and rule-out operating points (T2)

Code: `prism/analyses/triage_feasibility.py` (`python -m prism triage`). Outputs:
`outputs/results/analyses/triage_feasibility/`.

Status: plan written and committed before any T1 / T2 quantity was computed on real labels. Results follow in a later
commit.

## 0. Why, and what is already known

The deployed model C2 (ridge on clinical + timing + scan-day treatment; `phase_censoring.arm_design("C2")`) reaches IPCW
AUC(120 d) 0.601 (0.515–0.686) in the scan-day intended use (grade-4 scans on or after the documented RT start: 173
scans, 86 patients, 88 events, 84 non-events, 1 censored; `INTENDED_USE.md`). The question here is whether anything on
the existing MU-Glioma-Post data reaches a triage-useful operating point after RT, or whether new data, labels or
modalities are needed.

Known before this plan (so the reader can judge what is pre-specified):

- Single-scan imaging and last-scan change features add little: R2 + I2 (volumes + morphology + last-scan / nadir
  deltas) vs R2 in post-RT surveillance +0.061 (−0.033 to +0.155), not supported (`PHASE_LADDER.md`); nested radiomics
  and the fine-tuned encoder add nothing to core (`INTENDED_USE.md` R4).
- Consecutive-scan ET volume changes are very noisy (median 3.2-fold within 14 days) and ET does not increase at the
  documented progression scan (`DIAGNOSTICS_IMAGING.md`). This motivates multi-scan robust summaries rather than
  last-scan differences.
- Feature-only fact checked before writing the plan (no labels): of the 173 intended-use scans, 76 have no earlier MRI
  with a mask, 53 have 1, 28 have 2, 16 have 3–5. Trajectory features are therefore informative for at most 97 scans.
- C2 held-out predictions in the intended use have calibration slope 0.53 and O/E 1.01; event prevalence among
  verified intended-use scans is 88 / 172 = 0.51. NPV of "everyone is low risk" is therefore about 0.49.
- No rule-out operating point, NPV or decision curve of C2 in the intended use has been computed.

## Plan (pre-specified)

Horizon H = 120 d; label, censoring and evaluation machinery unchanged: documented progression within 120 d, censored
scans through IPCW; shared 5×5 patient-grouped folds (`outputs/data/folds.csv`); AUC = mean over the 5 repeats of the
pooled out-of-fold IPCW AUC(120 d); 95% paired patient-cluster bootstrap, 1000 draws (`metrics.evaluate_repeated`, with
C2 as `reference` for paired ΔAUC). Grade 4 only (all gliomas not analysed).

### (a) Populations

- **Training: all grade-4 scans (249 scans, 126 patients)**, as for the deployed model.
- **Intended use (PRIMARY evaluation)**: the grade-4 scans with RT started by the scan day (`phase_label != pre_rt`;
  173 scans), scored with the held-out predictions of the models trained on all scans (the `C2@full` design of
  `INTENDED_USE.md`); censoring weights re-estimated within the intended-use scans (marginal KM).
- Secondary: grade 4 overall (all 249 scans).
- Secondary: models refitted inside the intended-use population (patients keep their shared folds), scored there.
- Descriptive: intended-use scans with ≥ 1 earlier MRI (the only scans where trajectory features carry history).

### (b) Trajectory features (T1), as of the scan day

History of an index scan = every MU timepoint of the same patient with a mask and a known MRI day
(`outputs/features/measurements.csv`, 591 timepoints, including timepoints that are not index scans), **dated on or
before the index scan day** (the index scan included). Scans after the index day are never used; the code asserts that
every history scan day is ≤ the index scan day. No feature uses an outcome, and no feature has a parameter fitted across
patients, so features can be computed once; every fitted step (median imputation with missingness indicators, scaling,
choice of C by inner patient-grouped CV, ridge) stays inside the training folds (`audit.model.fit_pipeline`, the C2
pipeline).

For V ∈ {ET, lesion} (`et_cc`, `lesion_cc`; lesion = enhancing + necrotic + non-enhancing T2/FLAIR, as in
`measurements`), x = log(V + 0.1 cc), t = days since diagnosis:

| Feature | Definition | Missing when |
|---|---|---|
| `traj_n_prior_scans` | number of history scans strictly before the index day | never |
| `traj_slope_log_{V}` | Theil–Sen slope of x on t over all history scans, per 30 days (`scipy.stats.theilslopes`) | < 2 history scans |
| `traj_ew_level_log_{V}` | exponentially weighted mean of x over the history, weights 0.5^((t_index − t_j)/90 d) | never |
| `traj_ew_dev_log_{V}` | x at the index scan − the same exponentially weighted mean over the strictly earlier scans | no earlier scan |
| `traj_logratio_nadir_{V}` | x at the index scan − min x over the nadir window | never (0 if the index scan is the nadir) |
| `traj_days_since_nadir_{V}` | t_index − t of the (latest) scan attaining the window minimum | never (0 if index is nadir) |

Nadir window (RANO concept, "minimum since RT end", using only scan-day knowledge): history scans on or after the
documented RT end day if RT is completed by the index scan day (`treatment().rt_completed`); otherwise on or after the
RT start day if RT has started; otherwise the whole history. The index scan always belongs to the window. 11 features
in all. Missing values are handled by the in-fold `BASE_PRE` (median + indicator), like every other C2 input.

### (c) Models

| Arm | Inputs | Role |
|---|---|---|
| C2 | `arm_design("C2")` (reproduces the stored C2 OOF of `phase_censoring/oof_grade4_full`; asserted, max deviation < 1e-6) | reference |
| **C2 + trajectory** | C2 inputs + the 11 trajectory features | PRIMARY T1 arm |
| trajectory only | the 11 trajectory features | descriptive |

All arms: same `fit_pipeline` (BASE_PRE + verified-label ridge, inner choice of C, seed = repeat), same 5×5 folds.

### (d) T1 quantities

1. IPCW AUC(120 d) with 95% CI of each arm, and **ΔAUC (C2 + trajectory − C2) with paired 95% CI**, in the intended use
   (PRIMARY: trained on all scans) and in grade 4 overall; also in the refitted-in-intended-use version (secondary).
2. Calibration (O/E, IPCW slope) and IPCW Brier of each arm (`evaluate_repeated`).
3. Descriptive: the same AUCs restricted to intended-use scans with ≥ 1 earlier MRI (censoring weights within that
   subset); mean standardised ridge coefficients of the trajectory features over the 25 fits.

### (e) T2 quantities: rule-out operating points in the intended use

Predictions: the held-out predictions of C2 and C2 + trajectory (trained on all scans) on the 173 intended-use scans.
For each repeat r and each target fraction q ∈ {0.20, 0.30, 0.40}: **low risk** = prediction ≤ the empirical
q-quantile (numpy `method="lower"`) of that repeat's intended-use predictions. The threshold is a quantile of the
predictions, never chosen with the labels. Weights: marginal KM IPCW within the intended-use scans (cases 1/G(T_i),
controls 1/G(H), censored 0; the headline weights).

- **NPV (IPCW, PRIMARY)** = Σw(controls, low risk) / Σw(cases and controls, low risk). NPV on verified scans
  (unweighted) reported alongside; with 1 censored scan they differ by at most that scan.
- Sensitivity (IPCW) = Σw(cases, not low risk) / Σw(cases); specificity (IPCW) = Σw(controls, low risk) / Σw(controls);
  **share of events missed** = 1 − sensitivity; achieved fraction low risk; verified counts (low-risk scans, events
  among them).
- Each quantity: mean over the 5 repeats; 95% CI from 1000 patient-cluster bootstrap draws, in which the quantile
  threshold and the censoring weights are re-derived within each draw (the CI is for the "lowest q fraction" rule).
  Paired difference C2 + trajectory − C2 for NPV, descriptive.
- Descriptive: NPV and share of events missed for q from 0.05 to 0.50 in steps of 0.05 (point estimates only).
- **Decision curve** (intended use; "treat" = flag the scan for early review / intensified work-up): net benefit
  NB(p_t) = [Σw(cases flagged) − Σw(controls flagged) · p_t / (1 − p_t)] / Σw(cases and controls), flagged =
  prediction ≥ p_t, for p_t = 0.05 … 0.80 in steps of 0.05; treat-all and treat-none (NB = 0) curves; mean over
  repeats. Descriptive with 95% bootstrap CIs for NB(model) − max(NB treat-all, 0). The predictions are used as they
  are (no recalibration), because that is how the deployed model would be applied.

### (f) Decision rules (fixed now)

- **T1 succeeds** if, in the intended use (PRIMARY, trained on all scans), C2 + trajectory − C2 ΔAUC ≥ +0.03 **and** its
  paired 95% CI excludes 0 (lower bound > 0).
- **T2 identifies a triage-useful rule-out point** if, for C2 or C2 + trajectory, some q ∈ {0.20, 0.30, 0.40} classifies
  ≥ 20% of intended-use scans as low risk (achieved fraction, mean over repeats) with **IPCW NPV lower 95% bound ≥
  0.85**.
- **Overall: GO** for a triage model on this data only if T1 or T2 succeeds. Otherwise **NO-GO on MU-Glioma-Post
  alone**: the conclusion is that new data, labels or modalities are required.
- No multiplicity correction. Everything outside the rule items is secondary or descriptive. Any analysis added after
  the results are seen is labelled **EXPLORATORY**; any change to this plan is labelled **DEVIATION**.

**Run** (step 2): `python -m prism triage --workers <n>` (75 ridge fits for the full-cohort arms + 75 refitted, then
bootstraps; minutes on CPU, Slurm allocation). The plan section is snapshotted to `PLAN_snapshot.md` by the first run.
