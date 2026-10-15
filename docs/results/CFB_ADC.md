# CFB-GBM: does diffusion (ADC) add to conventional radiomics?

Code: `prism/analyses/cfb_adc.py` (`python -m prism cfbadc`). Outputs: `outputs/results/analyses/cfb_adc/`.
Data: `data/cfb-gbm/clinical/` (TCIA CFB-GBM clinical v03, treatment v02, MRI availability v02, RANO v04, PyRadiomics
features v03 on the GTV). No images are used. Dataset facts: `docs/literature/DATASETS.md`.

## 0. Why

On MU-Glioma-Post, conventional MRI (T1, T1c, T2, FLAIR) adds nothing to clinical + treatment information. One open
question is whether the limit is the *modality*. CFB-GBM ships PyRadiomics features on the GTV for every timepoint and
sequence, including ADC, so a conventional-vs-diffusion test can run without the images.

## 1. Analysis plan (pre-specified)

Written into this doc and the module docstring before any model of this module was run. A copy was saved to
`outputs/results/analyses/cfb_adc/PLAN_snapshot.md` before the run. Anything added after the results is labelled
**EXPLORATORY**. Before the plan was fixed only availability counts were looked at, no model output.

**Task.** One row per patient. Outcome = `rano_t1_to_t2 == "Progressive Disease (PD)"`; patients without a t1→t2 label
are dropped (SD / PR / CR = 0). Predictors are measured at t1 or before.

**Feature sets.**

| Set | Features |
|---|---|
| (a) clinical | age at t0, male, WHO performance status, WHO guideline (2021 vs 2016), RT dose, fractions, delay t0→RT (weeks), weeks t0→t1 |
| (b) + volume | (a) + log GTV volume at t1 + change t0→t1 (log1p(size_t1) − log1p(size_t0); RANO table) |
| (c) + conventional radiomics | (b) + t1gd and FLAIR first-order + texture features at t1, plus the GTV shape features once (shared mask) |
| (d) + ADC | (c) + ADC first-order + texture features at t1 |

**Cohorts.** conv = labelled patients with t1gd and FLAIR features at t1. adc = conv patients with ADC features at t1.

**Contrasts.** Primary: (d) vs (c) on the adc cohort. Secondary: (c) vs (b) and (b) vs (a) on the conv cohort; all four
sets also on the adc cohort.

**Learner** (fitted inside each outer training fold). Non-radiomics block: median impute + missingness indicators,
standardise. Each radiomics block (conventional; ADC separately): QuantileClip 1% (`c3_radiomics`), median impute,
variance filter, standardise, top-k univariate F with k ∈ {5, 10} (same k for both blocks). Concatenate, then L2
("ridge") logistic regression with C ∈ {0.01, 0.03, 0.1, 0.3, 1, 3}. k and C are chosen by inner stratified 3-fold CV AUC.

**Evaluation.** Repeated stratified 5-fold CV, 20 repeats, identical splits for every set within a cohort (paired). AUC
= mean over repeats of each repeat's pooled-OOF ROC AUC. 95% CIs from a patient bootstrap (1000 draws, all models on the
same draws, so ΔAUC is paired). Permutation test for the primary only: the whole ADC feature row is moved between
patients, (d) refitted, p = (1 + #{Δ_perm ≥ Δ_obs}) / (1 + n_perm), n_perm = 1000. For each contrast: n patients, n
events, and a power caveat from the bootstrap SE of Δ (minimal detectable Δ at 80% power ≈ 2.8 × SE).

**Pre-specified rule.** ADC "helps" if **Δ(d − c) ≥ 0.03 with the bootstrap 95% CI excluding 0**. Otherwise "not shown".

**Caveats (fixed in advance).**

- No IDH or MGMT in CFB-GBM: the clinical set is weaker than MU's.
- The label is volumetric RANO 2.0 from the GTV delineations. Volume and shape features at t1 are the denominator of the
  t1→t2 change, so (b) and the shape part of (c) are partly circular with the label (a large t1 GTV needs a larger
  absolute increase; regression to the mean).
- t1 lies ~6–8 weeks after RT ends, inside the 12-week pseudoprogression window. t1→t2 PD can be true progression, a
  late pseudoprogression, or growth from a t1 that was itself reduced.
- Small: about 30 events in total.

## 2. Results

Source: `outputs/results/analyses/cfb_adc/{results.csv, rule.json, permutation.csv, chosen.csv}`. The module ran twice
on the same seeds (16 and 100 workers, after an interrupted session); `rule.json` is identical to the 1e-15 level
(Δ 0.007214…, perm. p 0.1508), so the files on disk are the 16-worker run (`run_info.json`, 4,455 s).

**Primary (pre-specified): ADC on top of conventional radiomics, adc cohort (77 patients, 19 events).**

| Contrast | ΔAUC (95% CI) | Permutation p | Minimal detectable Δ (80 % power) |
|---|---|---|---|
| (d) + ADC vs (c) conventional | **+0.007 (−0.019, +0.035)** | 0.151 (1,000 perms) | 0.038 |

**Rule: NOT met.** ADC adds +0.007, below the 0.03 threshold, with a CI including 0. With a minimal detectable effect
of about 0.04, an ADC gain larger than ~0.04 is unlikely in this setting; smaller gains cannot be excluded.

**All sets.** AUC = mean over 20 repeats of pooled-OOF ROC AUC, 95% patient-bootstrap CI.

| Set | conv cohort (107 pts, 30 events) | adc cohort (77 pts, 19 events) |
|---|---|---|
| (a) clinical | 0.501 (0.403–0.596) | 0.565 (0.437–0.689) |
| (b) + GTV volume and change t0→t1 | 0.685 (0.569–0.781) | 0.713 (0.589–0.814) |
| (c) + conventional radiomics (t1gd, FLAIR) | 0.676 (0.575–0.769) | 0.691 (0.576–0.788) |
| (d) + ADC radiomics | 0.696 (0.593–0.785)¹ | 0.698 (0.577–0.800) |

¹ In the conv cohort, the 30 patients without ADC at t1 have the ADC block imputed with missingness indicators;
secondary only.

**Secondary contrasts** (paired bootstrap 95% CI):

| Contrast | conv cohort | adc cohort |
|---|---|---|
| (b) volume vs (a) clinical | +0.185 (+0.064, +0.293) | +0.148 (+0.031, +0.266) |
| (c) conventional radiomics vs (b) | −0.009 (−0.067, +0.051) | −0.022 (−0.074, +0.025) |
| (d) ADC vs (c) | +0.019 (−0.006, +0.045) | +0.007 (−0.019, +0.035) (primary) |

**Reading.**

- Clinical information alone is at chance (0.50–0.57). CFB-GBM has no IDH or MGMT and no treatment-phase variation
  (every t1 scan is at the same post-RT stage), so the predictors that carry MU's baseline are absent by design.
- GTV volume and its change t0→t1 are the only informative block (+0.15 to +0.19, CIs exclude 0). This is partly
  circular: the label is the t1→t2 change of the same GTV volume (pre-registered caveat), so it is not evidence for
  imaging beyond what defines the endpoint.
- Conventional texture adds nothing beyond volume (−0.009 / −0.022), the same pattern as on MU.
- ADC adds nothing measurable beyond conventional radiomics (primary +0.007).

## 3. Conclusion

On a third cohort with a different label (volumetric RANO 2.0) and diffusion imaging, the MU pattern repeats: once size
is accounted for, conventional texture adds nothing, and ADC first-order and texture features add nothing measurable
(+0.007, CI −0.019 to +0.035; rule not met). The test is small (77 patients, 19 events) and uses precomputed GTV-level
features, not the images; perfusion was not available. It does not support "conventional MRI is the ceiling and
diffusion moves it" for this forward task.
