# Plan: three methods for the methods rewrite (2026-11-15)

Written 2026-11-15, before any of the analyses below was run or coded. The author chose a methods / medical AI
framing (conversation 2026-11-15): the paper presents three methods, each with a defined object and a measured
property, and PRISM implements them. UCSF-ALPTDG is not on disk (link expired 2026-11-01); every analysis runs on MU
and LUMIERE with `PRISM_SKIP_UCSF=1`, and the code has the UCSF path for when the data returns, with no change to this
plan. No analysis here is confirmatory. All are descriptive estimates with patient-level bootstrap intervals; the
registered results (SYSTEM_PLAN.md, REPORT_V3_1_PLAN.md) stay as they are.

Scores: the system's scores, unchanged (`prism.analyses.system`): MU out-of-fold (5 repeats x 5 folds), LUMIERE the
locked MU models (images: the three-volume model where there is no previous scan). Evaluation sets as registered: MU
grade 4 intended use (146 scans), LUMIERE all (178 scans). Bootstrap: 2000 resamples of patients, seed 20261115; at
MU each resample averages the statistic over the 5 repeats.

## M1. Splitting the AUC by where its discrimination comes from

Object. For a score s, positives P, negatives N and a context c (a stratum label per scan), the pairs P x N split
into W = pairs with c_i = c_j and B = the rest. With A_W and A_B the AUCs (ties 1/2) over W and B, and w = |W| / |P x N|,
AUC = w A_W + (1 - w) A_B exactly. A_W measures discrimination with the context held fixed; A_B mixes the context and
the score. Context-only score: each stratum's progression rate (MU: computed on the training folds of each repeat;
LUMIERE: MU's rate for the matching stratum). Its A_W is 0.5 by construction; its A_B is how far the context alone
separates the across-context pairs.

Context. MU: time after radiotherapy from the treatment dates (pre_rt, during_rt, early_post_rt (to 12 weeks after
the end), later_post_rt), as in the registered within-phase audit. LUMIERE: the rater's "within 3 months after
radiotherapy" flag (two strata); for the context-only score, flagged scans take MU's early_post_rt rate and the rest
MU's pooled rate over the other strata. UCSF (when restored): rt_phase.

Outputs per cohort: for the clinical-history, imaging and combined models, enhancing volume alone and the
context-only score: AUC, w, A_W, A_B (bootstrap 95% intervals); the identity checked to 1e-12 on every resample;
increments (combined - clinical-history) and (combined - imaging) on AUC, A_W and A_B with intervals. Reading fixed
now: a model whose A_B exceeds its A_W by more than the interval of the difference is said to draw part of its
discrimination from the context; nothing else is claimed. The MU A_W values must reproduce the registered
within-phase AUCs (clinical-history 0.64, imaging 0.68) to 0.01, or the analysis stops.

## M2. Group-conditional (Mondrian) conformal sets with a fallback

Object. Groups g = time after radiotherapy x enhancement state (the reliability card's situation). Calibration as
registered (MU: a 70 / 30 patient split inside each outer training fold, model refitted on the 70%; external: MU
split seed 0), patient weights as `conformal.threshold`, score 1 - p(y), alpha 0.2. Each scan is calibrated in the
finest level of the hierarchy with at least 10 calibration patients: level 1 its group; level 2 its enhancement state
(all times); level 3 all calibration scans (the registered marginal set). A scan whose time after radiotherapy is
unknown in an external cohort (all of LUMIERE) starts at level 2. The level used is part of the record and replaces
the card's tier ("calibrated in this situation" at level 1).

Outputs per cohort, combined model (clinical-history and imaging secondary): marginal coverage, coverage within
each group and each level with patient-bootstrap intervals, the share of scans calibrated at each level, the share
of two-outcome sets and of empty sets, all next to the registered marginal sets. The worst-group coverage gap
(nominal minus the lowest group coverage among groups with at least 10 evaluation scans) is reported for both. No
adoption rule: the paper reports both and states the guarantee each has (level-1 and level-2 sets are conditional on
the group under exchangeability within the group; nothing holds externally without exchangeability).

## M3. A verifier that binds each claim to what it refers to

Object. The frozen checker (blob 26d6637a, not edited) plus two rules in a new module `prism/report/verifier.py`,
applied to v3.1-vocabulary claims (v3.2 reports through `facts_v3_2.back_claims`):
- V1 entity binding. In each claim, every number that sits next to an entity term (enhancing; FLAIR or oedema;
  necrosis; cavity; clinical-history (timeline), imaging (image) or combined score) must equal a value of a cited
  field whose key names that entity. A number with no entity term next to it keeps the frozen rule.
- V2 direction binding. A direction word (larger, increased, grew, rose, higher; smaller, decreased, shrank, fell,
  lower) must agree with every cited field that carries a direction (a statement field that contains a direction
  word; a numeric change field, by its sign). A direction word next to a volume entity with no cited direction source
  is unsupported.
The terms and windows are fixed in the module before the evaluation runs and are not tuned on the evaluation reports.

Evaluation.
1. Synthetic records (checker_mutation.py, 52 records): every existing operator, plus three new held-out operators
   fixed now: B3 the change sentence rewritten by hand with the opposite direction word ("Enhancing tumour increased
   since the previous scan." when it decreased, and the reverse); B4 the clinical-history score sentence given the
   imaging score's value while citing both score fields; B5 a rewritten sentence that gives the FLAIR volume as the
   enhancing volume while citing both volume fields. Per operator: mutants and share rejected, for the frozen
   checker and the verifier. Correct reports rejected (false rejections).
2. Real reports (MU 114, LUMIERE 162; v3.2 language model and the template, already generated): share of correct
   reports the verifier rejects, by rule. The reports are not read in a hosted context; only counts are printed.
   Every operator applied to the real reports where its pattern occurs: mutants and share rejected, per operator and
   writer.
Reading fixed now: the verifier is reported as closing a blind spot only for an operator it rejects in at least 95%
of synthetic mutants; false rejections on real reports are reported as counts with the rule that fired, and are not
adjudicated.

## Order
Plan committed -> code -> M1 identity and reproduction checks -> M1, M2, M3 runs -> results in
docs/results/METHODS_RESULTS.md (aggregate numbers only) -> manuscript rewrite.
