# The full PRISM system for detection at the scan: records and S1–S4

Plan: [SYSTEM_PLAN.md](SYSTEM_PLAN.md) (pre-specified, e7cba80), sections 1–3 and 5. The reports (S5–S7) are a
separate stage ([REPORT_V3.md](REPORT_V3.md)). Aggregate results only. Patient-level files stay under `outputs/`
(git-ignored).

Code: `prism/analyses/system.py` (`PYTHONPATH=. .venv/bin/python -m prism system --workers 10`, about 2.5 min on
10 CPUs). It reuses `detection`, `ucsf_external`, `reliability_card`, `audit.conformal`, `audit.reliability` and
`audit.model` by import. Tests: `tests/test_system.py`. Outputs (`outputs/results/analyses/system/`):
- `records_{mu,lumiere,ucsf}.jsonl`: one record per scan. There is also `records_mu_all_glioma.jsonl`, the
  secondary population.
- `records_<cohort>_EVALUATION_ONLY.csv`: labels and evaluation-set membership. These are never in a record.
- `RECORDS_READY`: a sentinel file with the git state and record counts.
- `checks.csv`, `conformal.csv`, `conformal_conditional.csv`, `conformal_split_cost.csv`, `selective.csv`,
  `tiers.csv`, `run_info.json`, `run.log`.

## What the system outputs at a scan

| field | MU (development) | LUMIERE (locked) | UCSF grade 4, scan 2 (locked) |
|---|---|---|---|
| timeline | B1, out-of-fold (5 × 5) | Tbase | A-Tbase |
| images | I_pure, out-of-fold | T_img; a 3-volume model at the 10 scans with no previous scan | A-Ipure |
| combined | B1 + I_pure, out-of-fold | T | A-T |
| records | 313 grade-4 detection scans (381 for all gliomas) | 178 | 140 (all grade-4 scan-2 scans) |

**Checks before any evaluation, all passed (`checks.csv`; the run stops otherwise):**
- MU B1 equals the published detection out-of-fold scores (max deviation 1e-16) in both populations.
- MU I_pure and B1 + I_pure equal the reliability card's scores.
- The LUMIERE Tbase and T scores, and the UCSF A-Tbase, A-Ipure and A-T scores, equal the published locked scores
  (max deviation 1e-16).
- Every AUC reproduces the published value to 3 decimals:
  - MU grade 4, intended use: 0.822 / 0.709 / 0.821; all scans: 0.845 / 0.712;
  - MU all gliomas, intended use, B1: 0.814;
  - LUMIERE: Tbase 0.689, T 0.773, T_img on all scans 0.655;
  - UCSF: 0.561 / 0.726 / 0.856.
- With the 3-volume model at its 10 scans, the LUMIERE image AUC is 0.654.

### Record schema (`prism.system_record/1`, one JSON object per line)

| key | content |
|---|---|
| `schema`, `record_id`, `cohort`, `scan_id`, `patient_id`, `population` | identifiers; population = model population (grade4 / all_glioma) |
| `population_flags` | `grade4`; MU `intended_use` (RT started as of the scan day); UCSF `scan2`, `gbm_who` |
| `phase_of_care` | MU detection phase; UCSF `rt_phase`; LUMIERE "unknown". LUMIERE also has `rater_flag_within_3_months_after_rt` |
| `situation` | card phase, enhancement state, cell, text (as RELIABILITY_CARD.md) |
| `scores` | `timeline`, `images`, `combined` (probabilities; MU repeat 0 out-of-fold, external locked) |
| `measurements` | `volumes_cc` (MU / UCSF: et, snfh, necrosis, cavity; LUMIERE: et, snfh, necrosis_cavity), `previous` (days before, volumes), `change_from_previous_cc`, `earlier_minimum_cc`, `change_from_earlier_minimum_cc` (smallest strictly earlier volume per compartment), `n_earlier_scans`, `source`; null when there is no earlier scan |
| `card` | `reliability.build_card` output: tier and evidence for every cohort (AUC / CI only for tested cells, otherwise counts), agreement with its measured block, inputs in range |
| `conformal` | `alpha_0.2`, `alpha_0.1`: set per pathway ("{0}", "{1}", "{0, 1}", "{}"); `mondrian_secondary`, the same keys; `conformal_model_scores` |
| `flags` | `pathways_disagree`, `out_of_range` + `out_of_range_reasons`, `tier_flag` + `tier`, `conformal_uncertain` (combined set {0, 1} at α = 0.2), `any_flag` |
| `provenance` | MU: repeat, outer fold, models and the conformal split seed. External: the locked model id per pathway |

**No outcome label.** `assert_no_label` rejects any label-like key (label, rating, neg_class, days_to_progression,
pos_s2_*, …) at write time. The tests check this, and they check that a record does not change when the labels are
flipped. Evaluation-set membership is also kept out of the records, because on MU the secondary-only scans are all
non-progression scans.

## Results

Evaluation sets:
- MU grade 4, intended use, primary negatives: 62 positives / 84 negatives / 80 patients;
- MU all gliomas, intended use (secondary): 64 / 98;
- LUMIERE: 73 / 105 / 79;
- UCSF grade 4, scan 2, `pos_s2_pm30` vs primary negatives: 29 / 40 / 69.

Method:
- On MU every quantity is the mean over the 5 repeats.
- CIs come from a patient-cluster bootstrap with 1,000 draws, seed 20261026.

### S1: coverage at α = 0.2 (target ≥ 0.78; standard split conformal)

| cohort | timeline | images | **combined** | combined, events / non-events | combined α = 0.1 |
|---|---|---|---|---|---|
| MU grade 4 | 0.795 (0.731–0.853) met | 0.844 (0.797–0.890) met | **0.823 (0.759–0.883) met** | 0.819 / 0.826 | 0.922 |
| MU all gliomas | 0.825 met | 0.848 met | **0.837 (0.790–0.881) met** | 0.756 / 0.890 | 0.941 |
| LUMIERE | 0.798 (0.732–0.868) met | **0.708 (0.648–0.759) not met** | **0.871 (0.807–0.924) met** | 0.767 / 0.943 | 0.978 |
| UCSF | **0.696 (0.594–0.812) not met** | 0.826 (0.739–0.913) met | **0.783 (0.681–0.870) met** | 0.966 / 0.650 | 0.957 |

- **S1 is met for the combined score in every cohort.**
  - UCSF only just meets it, and its lower bound is 0.68.
  - Two external pathways fail: LUMIERE images, where events are covered at 0.29, and the UCSF timeline, where
    non-events are covered at 0.50.
- **Conditional coverage fails in several places** (combined, α = 0.2; `conformal_conditional.csv`):
  - MU later post-RT 0.743, and within it ET increased 0.683 and ET absent 0.667. The tested cell (later post-RT,
    ET not increased) is 0.781.
  - LUMIERE events 0.767.
  - UCSF non-events 0.650, and later post-RT with ET not increased 0.607.
  - Early post-RT is over-covered on MU (0.971). That is where the sets are easy.
- **The sets are wide.**
  - At α = 0.2 the combined singleton rate is 0.75 on MU, 0.62 on LUMIERE and 0.64 on UCSF.
  - At α = 0.1 every UCSF timeline set is {0, 1}, so its coverage of 1.000 is trivial.
- **Mondrian (secondary):**
  - MU stays close to standard: combined 0.788.
  - Externally it breaks: LUMIERE combined 0.652, UCSF combined 0.507. Non-event coverage is 0.51 and 0.18.
- **Cost of the split** (the conformal model's own AUC against the displayed score):

| cohort | timeline | images | combined |
|---|---|---|---|
| MU grade 4 | 0.798 vs 0.822 | 0.701 vs 0.709 | 0.800 vs 0.821 |
| MU all gliomas | 0.804 vs 0.814 | 0.725 vs 0.747 | 0.825 vs 0.840 |
| LUMIERE | 0.699 vs 0.689 | 0.638 vs 0.654 | 0.776 vs 0.773 |
| UCSF | 0.578 vs 0.561 | 0.738 vs 0.726 | **0.775 vs 0.856** |

### S2 (AUC unflagged − AUC flagged, combined score) and S3 (retained AUC − phase-composition-matched removal)

| cohort | flag | flagged | AUC unflagged / flagged | **S2** (95% CI) | S3 (95% CI) |
|---|---|---|---|---|---|
| MU grade 4 | disagreement | 40% | 0.901 / 0.594 | **+0.307 (+0.175 to +0.432) met** | **+0.083 (+0.046 to +0.123) met** |
| | out of range | 56% | 0.847 / 0.796 | +0.051 (−0.066 to +0.183) not met | +0.015 (−0.043 to +0.096) not met |
| | tier | 63% | 0.609 / 0.832 | −0.224 (−0.409 to −0.017) not met (reversed) | −0.014 (−0.129 to +0.100) not met |
| | conformal {0, 1} | 25% | 0.860 / 0.633 | **+0.228 (+0.074 to +0.370) met** | +0.024 (−0.000 to +0.048) not met |
| | **any flag** | 91% | 0.646 / 0.816 | **−0.170 (−0.503 to +0.147) not met** | +0.025 (−0.351 to +0.340) not met |
| MU all gliomas | disagreement | 37% | 0.876 / 0.681 | +0.195 (+0.080 to +0.316) met | +0.048 (+0.017 to +0.078) met |
| | out of range | 55% | 0.858 / 0.833 | +0.024 not met | +0.008 not met |
| | tier | 65% | 0.668 / 0.858 | −0.190 not met | −0.005 not met |
| | conformal {0, 1} | 24% | 0.871 / 0.664 | +0.207 (+0.103 to +0.320) met | +0.012 (−0.005 to +0.030) not met |
| | any flag | 93% | 0.663 / 0.835 | −0.172 not met | −0.011 not met |
| LUMIERE | disagreement | 57% | 0.826 / 0.721 | +0.105 (−0.049 to +0.266) not met | +0.051 (−0.028 to +0.144) not met |
| | out of range | 65% | 0.807 / 0.765 | +0.042 not met | +0.036 not met |
| | tier | 11% | 0.806 / 0.560 | +0.246 (−0.095 to +0.581) not met | +0.032 (−0.002 to +0.078) not met |
| | conformal {0, 1} | 38% | 0.814 / 0.567 | **+0.248 (+0.102 to +0.412) met** | +0.041 (−0.016 to +0.092) not met |
| | any flag | 93% | 1.000 / 0.750 | +0.250 (+0.156 to +0.343) met* | +0.226 (+0.134 to +0.323) met* |
| UCSF | disagreement | 55% | 0.850 / 0.869 | −0.019 (−0.218 to +0.175) not met | −0.004 not met |
| | out of range | 61% | 0.945 / 0.802 | +0.143 (−0.042 to +0.330) not met | +0.094 (−0.034 to +0.188) not met |
| | tier | 100% | – | n/a (no unflagged scan) | n/a |
| | conformal {0, 1} | 36% | 0.921 / 0.833 | +0.087 (−0.070 to +0.291) not met | **+0.073 (+0.014 to +0.138) met** |
| | any flag | 100% | – | n/a | n/a |

\* LUMIERE "any flag" leaves 12 unflagged scans (2 progressions / 10 non-progressions), so the AUC of 1.000 and the
"met" rest on very few scans.

Reading:
- **The flags pick out hard scans on MU, but only disagreement does more than change the case mix.**
  - Disagreement and conformal {0, 1} both pass S2 on MU.
  - Only disagreement also passes S3: +0.083 against a phase-matched random removal of the same size.
  - Conformal {0, 1} is +0.024, with a lower bound of −0.000.
- **The tier flag is reversed on MU.** The only tested MU cell is later post-RT. That is the hard phase, where
  progressions and stable scans overlap. The "few cases" cells are mostly early post-RT stable scans with no
  progression, and those are easy to rank. So the tier marks where evidence is thin, not where the score is wrong.
- **"Any flag" removes 91–100% of scans.** It cannot be used for abstention, and on MU it lowers the AUC of the scans
  it keeps.
- **External results:**
  - On LUMIERE, conformal {0, 1} is the only single flag that passes S2. No single flag passes S3.
  - On UCSF, conformal {0, 1} passes S3 (+0.073) but not S2. Disagreement carries no information there (−0.019).

### S4: Brier and error rate at the cohort-median threshold, by tier (combined score; descriptive)

| cohort | tier | scans (pos / neg) | Brier (95% CI) | error rate (95% CI) |
|---|---|---|---|---|
| MU grade 4 | tested | 54 (38 / 16) | 0.222 (0.159–0.292) | 0.293 (0.155–0.426) |
| | few cases | 92 (24 / 68) | 0.147 (0.114–0.183) | 0.235 (0.167–0.305) |
| MU all gliomas | tested | 56 | 0.218 | 0.286 |
| | few cases | 106 | 0.135 | 0.213 |
| LUMIERE | tested | 159 (66 / 93) | 0.187 (0.165–0.212) | 0.289 (0.204–0.380) |
| | few cases | 19 (7 / 12) | 0.258 (0.155–0.395) | 0.421 (0.176–0.688) |
| UCSF | few cases | 69 (29 / 40) | 0.208 (0.176–0.240) | 0.275 (0.174–0.377) |

No evaluation scan is "not tested". UCSF has no tested cell.

Reading:
- **The expected direction holds on LUMIERE**: "tested" has lower Brier and error than "few cases", with
  overlapping CIs.
- **On MU the direction is the opposite.** The "few cases" scans are mostly early post-RT stable scans, which are
  easy, as explained under S2.
- So the tier states how much evidence there is. It does not predict accuracy.

## Deviations and decisions

A council of three independent advisers was convened on the questions the plan does not settle, before any S1–S4
output was read. All three gave the same answer to every question:
1. **LUMIERE image pathway.** MU I_pure cannot be computed on LUMIERE: DeepBraTumIA has 3 labels and no morphology.
   The council chose:
   - the locked LUMIERE image set T_img (as in the card);
   - for the 10 scans with no previous scan, a locked MU model on the 3 current volumes (the I_scan analogue of the
     plan's "I_scan where there is no previous scan").

   One consequence: the card's measured agreement block on LUMIERE was computed with T_img on all scans.
2. **S1 "met"** is stated for each pathway, with the combined score as the headline.
3. **S3 composition** is matched by phase of care, as in P2:
   - MU detection phase;
   - UCSF `rt_phase`;
   - LUMIERE has a single stratum (no RT dates), so the matched reference is plain random removal.
4. **S4 is descriptive.** It has no met / not met; the direction is stated.
5. **Conformal flag** = the combined set {0, 1} at α = 0.2.
6. **Out of range, external cohorts** = the union of all pathway inputs. Ranges are the 1st–99th percentiles of the
   MU grade-4 training rows; IDH / MGMT unknown is also flagged. On MU, the same rule is applied inside each outer
   training fold, as in the card.
7. **Flags with no unflagged scans** (UCSF tier, UCSF any): n/a, neither met nor not met.

Specification details, fixed before evaluation:
- **MU records and display:**
  - The records show CV repeat 0, as in REPORT_AGENT.md.
  - S1–S4 use all 5 repeats.
  - Conformal split seed 10 · repeat + fold.
  - External conformal model: MU patient split 70 / 30, seed 0.
- **Agreement medians** follow the card's rule: the median over the cohort's evaluation set, per repeat.
- **The card** is the existing `reliability_card/lookup.csv`, unchanged. All-glioma MU scans are looked up in the
  grade-4 MU table, the only MU table there is. Their 12 "not tested" scans are non-grade-4 cells.
- **S3 references:**
  - point estimate: 1,000 matched draws;
  - CI: each bootstrap draw recomputes the reference with 100 draws, as P2 did.
- **UCSF records** cover all 140 grade-4 scan-2 scans. S1–S4 use the pre-specified 69.
- **The segmentation figures** (`figures/`) belong to the report stage (S5–S7) and are not produced here.

## Limits

- The calibration sets are small: about 30% of a training fold, about 30 patients. Coverage is therefore noisy, and
  conditional coverage fails in the later post-RT phase on MU.
- External coverage depends on the cohort:
  - LUMIERE images under-cover progression;
  - the UCSF timeline under-covers non-progression;
  - Mondrian sets break on both.
- The MU tier flag is tied to phase of care, so S2 for the tier mixes phase with evidence.
- LUMIERE "any flag" rests on 12 scans.

## EXPLORATORY: reduced confidence design

**EXPLORATORY.** This design was chosen after S1–S4 had been read, so none of it is pre-specified. The motivation:
- "any flag" marks 91–100% of scans;
- out of range picks out no errors in any cohort;
- the tier is reversed on MU.

The four rules below are tested on the same records, with the same metrics and bootstrap as S2 / S3
(patient-cluster, 1,000 draws, seed 20261026; S3 reference of 100 draws per bootstrap draw and 1,000 for the point).
Populations are grade 4 primary only: MU intended use (out-of-fold, mean over 5 repeats), LUMIERE, and UCSF grade-4
scan 2.

- **D1:** the pathways disagree.
- **D2:** combined conformal set {0, 1} at α = 0.2.
- **D3:** D1 OR D2.
- **D4:** D1 AND D2.

Code: `scripts/exploratory_reduced_flags.py`. It imports `prism.analyses.system` and changes nothing there.
Outputs are in `outputs/results/analyses/system/exploratory_reduced_flags/` (`selective.csv`, `error_by_flag.csv`,
`checks.csv`). The checks:
- the rebuilt cohorts reproduce the published AUCs;
- their repeat-0 flags equal the flags in `records_{mu,lumiere,ucsf}.jsonl`;
- the D1 and D2 rows equal the pre-specified S2 / S3 rows of `selective.csv` exactly.

Error is measured at the cohort-median threshold of the combined score, as in S4.

| cohort | rule | flagged | AUC unflagged / flagged | S2 diff (95% CI) | S3 retained − matched (95% CI) | error flagged / unflagged |
|---|---|---|---|---|---|---|
| MU grade 4 | D1 disagree | 40% | 0.901 / 0.594 | **+0.307 (+0.175 to +0.432)** | **+0.083 (+0.046 to +0.123)** | 0.43 / 0.14 |
| | D2 conformal | 25% | 0.860 / 0.633 | **+0.228 (+0.074 to +0.370)** | +0.024 (−0.000 to +0.048) | 0.37 / 0.22 |
| | D3 or | 52% | 0.930 / 0.650 | **+0.279 (+0.176 to +0.375)** | **+0.090 (+0.048 to +0.134)** | 0.38 / 0.12 |
| | D4 and | 12% | 0.845 / 0.511 | **+0.334 (+0.125 to +0.515)** | **+0.023 (+0.010 to +0.041)** | 0.52 / 0.22 |
| LUMIERE | D1 disagree | 57% | 0.826 / 0.721 | +0.105 (−0.049 to +0.266) | +0.051 (−0.028 to +0.144) | 0.36 / 0.22 |
| | D2 conformal | 38% | 0.814 / 0.567 | **+0.248 (+0.102 to +0.412)** | +0.041 (−0.016 to +0.092) | 0.48 / 0.20 |
| | D3 or | 68% | 0.860 / 0.730 | +0.130 (−0.003 to +0.258) | **+0.086 (+0.004 to +0.171)** | 0.36 / 0.19 |
| | D4 and | 27% | 0.818 / 0.518 | **+0.300 (+0.129 to +0.519)** | **+0.047 (+0.005 to +0.085)** | 0.54 / 0.22 |
| UCSF | D1 disagree | 55% | 0.850 / 0.869 | −0.019 (−0.218 to +0.175) | −0.004 (−0.112 to +0.103) | 0.26 / 0.29 |
| | D2 conformal | 36% | 0.921 / 0.833 | +0.087 (−0.070 to +0.291) | **+0.073 (+0.014 to +0.138)** | 0.32 / 0.25 |
| | D3 or | 68% | 0.929 / 0.863 | +0.066 (−0.130 to +0.229) | +0.086 (−0.006 to +0.190) | 0.26 / 0.32 |
| | D4 and | 23% | 0.890 / 0.850 | +0.040 (−0.148 to +0.309) | **+0.038 (+0.001 to +0.087)** | 0.38 / 0.25 |

Bold marks a CI that excludes 0. On LUMIERE the matched reference is plain random removal, because there is a single
stratum.

The CI of the error difference (flagged − unflagged) for D4 is:
- MU +0.30 (+0.17 to +0.43);
- LUMIERE +0.33 (+0.13 to +0.48);
- UCSF +0.13 (−0.13 to +0.40).

Reading:
- **No reduced rule passes both S2 and S3 in all three cohorts.**
- **D4 (disagree and {0, 1}) is the only rule whose S3 lower bound is above 0 in every cohort.** It also passes S2
  on MU and LUMIERE.
  - It flags 12–27% of scans.
  - Flagged scans are wrong at the median threshold about half the time on MU and LUMIERE (0.52, 0.54) and 0.38 on
    UCSF. Unflagged scans are wrong 0.22–0.25 of the time.
  - Its S3 gains are small: +0.02 to +0.05, with lower bounds of 0.010, 0.005 and 0.001. Abstaining on so few scans
    moves the retained AUC little.
  - The flagged MU set is small: at least 5 progressions and 4 non-progressions per repeat.
- **D3 (or)** gives the largest retained gain on MU (+0.090) and LUMIERE (+0.086). It flags 52–68% of scans, which is
  too many to act on. Its S2 fails on LUMIERE and UCSF.
- **Disagreement alone** carries no information on UCSF (S2 −0.019; flagged error 0.26 against 0.29 unflagged).
- **The conformal set alone** is the most consistent single signal. It passes S2 on MU and LUMIERE, and S3 on UCSF.

**Proposed confidence statement for the report (EXPLORATORY).** The card is worded as evidence, the conformal set
gives the number, and disagreement on an undecided set is the warning:

> *Evidence:* in this situation the system was tested on N progression and M non-progression scans
> (AUC and CI when "tested"; otherwise "few cases"). *At 80% confidence the answer is* {1} / {0} / {0, 1}
> (both answers possible). *Warning*, shown only when the set is {0, 1} and the pathways point opposite ways: in
> development and external testing, scans like this were misclassified about half the time (MU 0.52, LUMIERE 0.54,
> UCSF 0.38), against about one in four otherwise.

On its own, disagreement is stated as a fact in the card, not as a warning, because it is uninformative on UCSF. The
tier and out of range are not used as flags. This design would have to be tested on new data before it is claimed.

## EXPLORATORY: analyses requested in internal review (2026-10-26)

**EXPLORATORY.** These analyses were added after internal review round 3
([round3_reviewer2.md](../manuscript/council/round3_reviewer2.md), M2, M3, M4 and M6, plus NUMBERS.md mismatch 8).
None is pre-specified, except the UCSF calibration row under F (UCSF_PLAN.md, secondary).

The populations are those of S1–S4:
- MU grade 4, intended use: 62 / 84 / 80 patients, out-of-fold, mean over 5 repeats;
- LUMIERE: 73 / 105 / 79;
- UCSF grade 4, scan 2: 29 / 40 / 69.

Bootstrap: patient-cluster, 1,000 draws. Draw i uses `rng([20261026, i])`, as in `system.boot_job` (A–D). Two
exceptions:
- E uses `detection.evaluate_set` (seed 20261021), so it is paired with the other ladder intervals.
- F uses the UCSF plan's calibration bootstrap (seed 20261025), so the pre-specified UCSF row reproduces exactly.

Code: `scripts/exploratory_review_round3.py`. Outputs: `outputs/results/analyses/review_round3/` (CSVs A–F,
`checks.csv`, `run_info.json`, `run.log`).

The run stops unless every check passes. All of these did:
- the ladder AUCs (0.659 / 0.709 / 0.806) and the I − I_pure CI;
- the rebuilt locked scores (max deviation 0);
- the pre-specified S2 / S3 rows for disagreement and conformal;
- the class coverage points against `conformal.csv`;
- UCSF log ET 0.878;
- the UCSF A-T calibration against `ucsf/locked/calibration.csv`.

### A. Agreement with medians fixed on MU (combined score; S2 / S3 as in system.py)

How the medians are set:
- **MU.** The pre-specified rule already uses the MU OOF median. A fold-held-out variant was added: each test fold
  uses the median of the OOF scores of the other four folds in the same repeat.
- **External.** Each locked pathway model's median over its 181 MU training rows: timeline 0.387; images 0.356 for
  LUMIERE T_img (0.348 for the 3-volume model) and 0.299 for UCSF A-Ipure. The cohorts' own timeline medians were
  0.459 (LUMIERE) and 0.642 (UCSF).
- **Effect.** Agreement status changes for 31% of LUMIERE scans and 48% of UCSF scans.

| cohort | rule | flagged | AUC unflagged / flagged | S2 (95% CI) | S3 (95% CI) |
|---|---|---|---|---|---|
| MU | own (= MU OOF) median, pre-specified | 40% | 0.901 / 0.594 | **+0.307 (+0.175 to +0.432)** | **+0.083 (+0.046 to +0.123)** |
| | fold-held-out MU median | 40% | 0.902 / 0.589 | **+0.313 (+0.184 to +0.431)** | **+0.082 (+0.047 to +0.119)** |
| | fold-held-out median AND {0, 1} | 12% | 0.845 / 0.469 | **+0.376 (+0.166 to +0.552)** | **+0.023 (+0.009 to +0.040)** |
| LUMIERE | own median, pre-specified | 57% | 0.826 / 0.721 | +0.105 (−0.049 to +0.266) | +0.051 (−0.028 to +0.144) |
| | **MU median** | 60% | 0.889 / 0.667 | **+0.222 (+0.102 to +0.337)** | **+0.115 (+0.049 to +0.190)** |
| | MU median AND {0, 1} | 30% | 0.811 / 0.583 | **+0.227 (+0.054 to +0.398)** | +0.037 (−0.004 to +0.081) |
| UCSF | own median, pre-specified | 55% | 0.850 / 0.869 | −0.019 (−0.218 to +0.175) | −0.004 (−0.112 to +0.103) |
| | **MU median** | 48% | 0.879 / 0.745 | +0.134 (−0.096 to +0.397) | +0.023 (−0.086 to +0.099) |
| | MU median AND {0, 1} | 25% | 0.874 / 0.850 | +0.024 (−0.162 to +0.322) | +0.023 (−0.028 to +0.076) |

For comparison, the own-median AND {0, 1} rule (reduced D4) gave:
- LUMIERE: S2 +0.300, S3 +0.047 (+0.005 to +0.085);
- UCSF: S2 +0.040, S3 +0.038 (+0.001 to +0.087).

Reading:
- **Fixing the medians on MU does not weaken the rule. It strengthens it externally.** Disagreement alone now
  passes S2 and S3 on LUMIERE. On UCSF it moves in the expected direction, but the CI includes 0: only 8
  progressions are flagged.
- **The AND rule loses its external S3 lower bounds** (LUMIERE −0.004, UCSF −0.028).
- **On MU the fold-held-out median changes nothing.**

### B. Class-conditional coverage of the combined set at α = 0.2

| cohort | kind | progression (95% CI) | non-progression (95% CI) | all | singleton share, prog / non-prog |
|---|---|---|---|---|---|
| MU | standard | 0.819 (0.748–0.888) | 0.826 (0.731–0.908) | 0.823 | 0.66 / 0.82 |
| | Mondrian | 0.868 (0.797–0.934) | 0.729 (0.633–0.815) | 0.788 | 0.82 / 0.85 |
| LUMIERE | standard | **0.767 (0.671–0.872)** | 0.943 (0.857–1.000) | 0.871 | 0.49 / 0.71 |
| | Mondrian | 0.849 (0.760–0.931) | **0.514 (0.392–0.642)** | 0.652 | 0.97 / 0.92 |
| UCSF | standard | 0.966 (0.880–1.000) | **0.650 (0.511–0.791)** | 0.783 | 0.69 / 0.60 |
| | Mondrian | 0.966 (0.880–1.000) | **0.175 (0.062–0.308)** | 0.507 | 1.00 / 0.93 |

Reading:
- **Standard sets keep coverage in both classes only on MU.**
  - LUMIERE under-covers progression: 0.77, with the CI reaching 0.67.
  - UCSF under-covers non-progression: 0.65 (0.51–0.79).
- **Mondrian sets do not fix this externally.** The MU class thresholds do not transfer under the shift in score
  distribution, so exchangeability with MU does not hold class by class.

### C. Raw enhancing-tumour baselines (no fitting; larger = progression)

| cohort | log ET volume (95% CI) | log ET ratio to previous scan (95% CI) | ratio, scans with a previous scan only |
|---|---|---|---|
| MU-IU (146) | 0.622 (0.530–0.717) | 0.488 (0.399–0.580) | 0.486 (0.380–0.585), 62 / 46 |
| LUMIERE (163 with ET; 168 for the ratio) | 0.662 (0.563–0.751) | 0.628 (0.532–0.722) | 0.633 (0.530–0.732), 66 / 92 |
| UCSF (69) | **0.878 (0.793–0.948)** | 0.822 (0.707–0.930) | same: every scan 2 has scan 1 |

Reading:
- On MU, ET volume alone (0.62) is below the image pathway (0.71), and ET change is at chance.
- On LUMIERE, ET volume alone (0.66) matches the locked image pathway (0.65), and the combined score (0.77) is above
  both.
- On UCSF, ET volume alone (0.88) exceeds the locked image pathway (0.73) and matches the combined score (0.86).
- UCSF_AUDIT.md's MU log ET value of 0.635 is for a different MU row set; on MU-IU it is 0.622.

### D. Sensitivity and specificity of the combined score at the MU median threshold

| cohort | threshold | sensitivity (95% CI) | specificity (95% CI) | called positive | error rate | own-median reference (sens / spec) |
|---|---|---|---|---|---|---|
| MU | OOF median over MU-IU, per repeat (mean 0.402) | 0.787 (0.705–0.872) | 0.712 (0.614–0.813) | 50% | 0.256 | – |
| LUMIERE | locked T median on its MU training rows (0.363) | 0.890 (0.817–0.959) | 0.495 (0.357–0.636) | 66% | 0.343 | 0.740 / 0.667 |
| UCSF | locked A-T median on its MU training rows (0.363) | 1.000 (1.000–1.000) | **0.175 (0.061–0.297)** | 90% | 0.478 | 0.759 / 0.700 |

Reading:
- A threshold fixed on MU does not hold its operating point externally. It calls 66% (LUMIERE) and 90% (UCSF) of
  scans positive.
- This is consistent with the overprediction in F (UCSF O/E 0.72): the combined model's timing inputs
  extrapolate at UCSF.

### E. The ladder's middle step (MU-IU; paired patient bootstrap)

| contrast | all scans (95% CI) | phase-stratified (95% CI) |
|---|---|---|
| I_pure − I_scan (+ change from earlier scans) | **+0.050 (−0.003 to +0.106)**, P(≤ 0) = 0.03 | −0.003 (−0.095 to +0.080) |
| I − I_pure (+ schedule context; check) | +0.097 (+0.047 to +0.153) | −0.013 (−0.057 to +0.037) |

The middle step's interval includes 0, and within phase the step is nil.

### F. External calibration of the locked combined model

| cohort | model | slope (95% CI) | O/E (95% CI) | calibration-in-the-large | mean risk / observed |
|---|---|---|---|---|---|
| LUMIERE (EXPLORATORY) | T | 1.45 (0.85–2.54) | 0.97 (0.81–1.14) | −0.07 | 0.42 / 0.41 |
| UCSF (PLANNED secondary, UCSF_PLAN.md; reproduced) | A-T | 3.29 (1.96–6.28) | 0.72 (0.55–0.91) | −0.73 | 0.59 / 0.42 |

Reading:
- **LUMIERE.** Calibration in the large holds. The slope is above 1, so the predictions are somewhat compressed, but
  the CI includes 1.
- **UCSF.** The model overpredicts and is strongly compressed. It ranks well but is not calibrated there.
