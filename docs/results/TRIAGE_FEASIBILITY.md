# Triage feasibility on the existing data: longitudinal volume trajectory (T1) and rule-out operating points (T2)

Code: `prism/analyses/triage_feasibility.py` (`python -m prism triage`). Outputs:
`outputs/results/analyses/triage_feasibility/`.

Status: plan committed before any T1 / T2 quantity was computed on real labels (fc2d247); full run 2026-10-21 (Results
below).

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

## Results

Run on 2026-10-21 (`run_info.json`: 25 workers, 1000 bootstrap draws, 12 s; Slurm allocation, CPU only). All files are
in `outputs/results/analyses/triage_feasibility/`. Plan snapshot: `PLAN_snapshot.md` (git fc2d247). Before the run only
the feature table and the leakage check were computed (no labels involved).

**Checks** (`checks.csv`).

- **Leakage**: for every one of the 249 index scans, all scans of the same patient dated after the index day were
  perturbed (volumes × U(0.1, 10) + U(0, 50) cc) and 30% of them dropped, and the features were recomputed: maximum
  deviation 0, identical missingness. The feature code also asserts that every history scan is dated ≤ the index day.
- **Reproduction**: the recomputed C2 OOF predictions equal the stored `phase_censoring/oof_grade4_full` and
  `oof_grade4_rt_started` C2 predictions (max deviation 1e-16), so the C2 column below is the published C2.
- Feature coverage: 123 of 249 grade-4 scans (97 of 173 intended-use scans) have ≥ 1 earlier MRI; for the others the
  slope and deviation features are missing (median-imputed in-fold with an indicator).

### T1. C2 + trajectory (`auc.csv`)

IPCW AUC(120 d), mean over 5 repeats, 95% paired patient-cluster bootstrap CI; Δ vs C2 paired.

| Evaluation set (scans / events / non-events / censored) | Arm | AUC (95% CI) | Δ vs C2 (95% CI) | O/E | Slope |
|---|---|---|---|---|---|
| **Intended use, trained on all scans (PRIMARY)** (173 / 88 / 84 / 1) | C2 | 0.601 (0.515–0.686) | – | 1.01 | 0.53 |
| | **C2 + trajectory** | **0.594 (0.504–0.681)** | **−0.008 (−0.074 to +0.052)** | 1.01 | 0.43 |
| | trajectory only | 0.543 (0.451–0.639) | −0.058 (−0.184 to +0.064) | 1.14 | 0.30 |
| Grade 4 overall, trained on all scans (249 / 93 / 117 / 39) | C2 | 0.678 (0.596–0.755) | – | 1.04 | 0.85 |
| | C2 + trajectory | 0.674 (0.592–0.759) | −0.005 (−0.048 to +0.040) | 1.03 | 0.68 |
| | trajectory only | 0.567 (0.480–0.652) | −0.111 (−0.218 to −0.007) | 0.97 | 0.33 |
| Intended use, refitted inside intended use (secondary) | C2 | 0.595 (0.517–0.682) | – | 0.98 | 0.71 |
| | C2 + trajectory | 0.615 (0.535–0.704) | +0.020 (−0.038 to +0.067) | 0.98 | 0.69 |
| | trajectory only | 0.512 (0.425–0.602) | −0.083 (−0.203 to +0.025) | 0.99 | 0.12 |
| Intended use with ≥ 1 earlier MRI, trained on all (descriptive) (97 / 50 / 46 / 1) | C2 | 0.630 (0.528–0.729) | – | 1.01 | 0.56 |
| | C2 + trajectory | 0.610 (0.507–0.722) | −0.020 (−0.115 to +0.060) | 0.99 | 0.45 |
| | trajectory only | 0.546 (0.397–0.679) | −0.084 (−0.273 to +0.090) | 1.10 | 0.44 |

Trajectory features add nothing to C2, either overall or in the 97 scans that have a volume history. On their own they
rank intended-use scans barely above chance (0.543, CI spans 0.5). Their largest mean standardised ridge coefficients
(`coefficients.csv`, full-cohort C2 + trajectory fits) are the exponentially weighted ET level (+0.20, essentially the
current ET volume), the deviation of the current ET and lesion volume from their smoothed history (+0.11, +0.10) and
days since the ET nadir (+0.09). The robust slopes (ET −0.07, lesion 0.00) and the ratio to nadir (ET +0.03, lesion
−0.04) carry almost no weight. The longer histories do not rescue the noise of single-scan volumes.

### T2. Rule-out operating points in the intended use (`operating_points.csv`)

Held-out predictions of the models trained on all scans; low risk = the lowest q fraction of each repeat's predictions;
IPCW NPV is primary (marginal KM within intended use). With 1 censored scan, NPV on verified scans equals the IPCW NPV
to 3 decimals for every row. Means over 5 repeats; 95% CIs from 1000 patient-cluster bootstrap draws with the threshold
and weights re-derived in each draw.

| Arm | Target low risk | Achieved (scans) | Events among low-risk scans | **NPV, IPCW (95% CI)** | Sensitivity | Specificity | Events missed |
|---|---|---|---|---|---|---|---|
| C2 | 20% | 20.3% (35.2) | 11.8 | **0.664 (0.508–0.786)** | 0.866 (0.809–0.909) | 0.279 (0.222–0.343) | 13.4% (9.1–19.1) |
| C2 | 30% | 30.1% (52.0) | 19.6 | 0.623 (0.478–0.721) | 0.777 (0.704–0.824) | 0.386 (0.318–0.455) | 22.3% (17.6–29.6) |
| C2 | 40% | 39.9% (69.0) | 28.6 | 0.583 (0.459–0.682) | 0.675 (0.600–0.729) | 0.476 (0.412–0.555) | 32.5% (27.1–40.0) |
| C2 + trajectory | 20% | 20.2% (35.0) | 11.6 | **0.669 (0.515–0.803)** | 0.868 (0.818–0.914) | 0.279 (0.231–0.341) | 13.2% (8.6–18.2) |
| C2 + trajectory | 30% | 30.1% (52.0) | 18.4 | 0.642 (0.488–0.767) | 0.791 (0.724–0.848) | 0.393 (0.331–0.470) | 20.9% (15.2–27.6) |
| C2 + trajectory | 40% | 39.9% (69.0) | 27.6 | 0.597 (0.458–0.713) | 0.686 (0.607–0.759) | 0.486 (0.413–0.571) | 31.4% (24.1–39.3) |

NPV difference C2 + trajectory − C2 (descriptive): +0.004 (−0.093 to +0.127) at 20%, +0.019 (−0.061 to +0.122) at 30%,
+0.013 (−0.060 to +0.086) at 40%.

For reference, event prevalence among verified intended-use scans is 0.51, so "everyone low risk" has NPV 0.49. The
best rule-out group (lowest 20%) still progresses within 120 days in about a third of scans (1 − NPV ≈ 0.34), and
discarding it misses about 13% of all progressions. The descriptive curve (`npv_curve.csv`, points only) never reaches
0.85 for any fraction from 5% to 50%. The highest value is 0.80 at 5% (C2 + trajectory; 9 scans, 1.8 events), and C2
peaks at 0.72 (5%).

**Decision curve** (`decision_curve.csv`; "treat" = flag for early review, prediction ≥ p_t; net benefit per scan,
IPCW). Below p_t ≈ 0.30 both models equal treat-all (difference ≤ 0.005). C2 + trajectory exceeds treat-all by 0.001–0.002
at p_t 0.10–0.20, with CI lower bounds at 0.000, which is clinically negligible. Between 0.35 and 0.50 the models exceed
the better default by +0.007 to +0.063, but every CI includes 0 (e.g. C2 at 0.50: +0.063, −0.051 to +0.110). Above
0.55 they are at or below treat-none (C2 + trajectory at 0.75: −0.072, −0.149 to −0.005). There is no threshold range
with a net benefit that is clearly positive and of a useful size.

### Verdict under the pre-specified rule (`rule.csv`)

| Rule item | Result | Verdict |
|---|---|---|
| T1: C2 + trajectory − C2 ≥ +0.03 with CI excluding 0 (intended use, trained on all) | −0.008 (−0.074 to +0.052) | **Fails** |
| T2: some q with ≥ 20% low risk and IPCW NPV lower bound ≥ 0.85 (C2 or C2 + trajectory) | best lower bound 0.515 (C2 + trajectory, 20%); best point 0.669 | **Fails** (all 6 rows) |
| **Overall** | neither T1 nor T2 | **NO-GO on MU-Glioma-Post alone** |

**Conclusion (fixed wording of the plan):** no triage model is supported on this data. Neither a longitudinal volume
trajectory nor any rule-out threshold of the deployed model reaches a triage-useful operating point after RT. New data,
labels (e.g. imaging-adjudicated progression rather than documented clinical progression) or modalities (e.g.
perfusion, diffusion, spectroscopy, which separate true progression from treatment effect) are required.

### Deviations and notes

- **No DEVIATION** from the plan. Every pre-specified quantity was computed as written. The only computation before
  the run was the feature table and the leakage check (no labels).
- The quantile thresholds are taken from the evaluation predictions themselves. This uses no labels, but in practice
  the threshold would be fixed from training data. With CIs this wide, the difference would not change the verdict.
- The decision curve uses C2's predictions as they are. Their calibration slope in intended use is 0.53 (0.43 with
  trajectory), so they are too spread out, which pushes the high-threshold net benefit below zero. Recalibration was not
  pre-specified and was not done. It cannot raise the NPV or AUC, which depend only on the ranking.
- Secondary result worth noting: refitted inside intended use, C2 + trajectory is +0.020 (−0.038 to +0.067), below the
  +0.03 bar and with a CI spanning 0. It is not a rule item.
- `paper/` and the other docs are untouched.
