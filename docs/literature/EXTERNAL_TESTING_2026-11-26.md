# Prior external testing of glioma progression models (search 2026-11-26)

Two searches (web, PubMed/PMC, OpenAlex citing lists of the MU-Glioma-Post, LUMIERE, UCSF-ALPTDG, UCSD-PTGBM, RHUH-GBM,
BraTS 2024 post-treatment and Burdenko papers). [full] = full text read; [abs] = abstract only. Unverified items are
marked; do not cite them as fact.

## Learned progression / pseudoprogression classifiers tested at another institution

| Study | Dev → external | Unit, time point | Unchanged? | External result | Level |
|---|---|---|---|---|---|
| Jang 2018 Sci Rep, 10.1038/s41598-018-31007-2 | 59 → 19 (sister hospital) | patient, one scan | yes | AUC 0.83 (T1c + clinical) | [full] |
| Kim JY 2019 Neuro-Oncology 21(3):404, 10.1093/neuonc/noy133 | 61 → 34 | patient, ≤12 wk after CRT | yes | 0.85 (with ADC/CBV); 0.74 conventional | [full] |
| Ismail 2018 AJNR, 10.3174/ajnr.A5858 | 59 → 46 | unclear | features chosen on train | accuracy 90.2% | [abs] |
| Akbari 2020 Cancer 126:2625, 10.1002/cncr.32790 | UPenn → 20 (Jefferson) | patient, re-resection | reduced model | AUC 0.80 | [full] |
| Park JE 2021 Eur Radiol, 10.1007/s00330-020-07414-3 | → two hospitals | patient | not verified | 0.78 | [abs] |
| Park YW 2021 Sci Rep, 10.1038/s41598-021-82467-y | 86 → 41 | patient, >12 wk | yes | 0.80 (ADC); 0.65–0.66 conventional | [full] |
| Gomaa 2025 Sci Rep 15:17133, 10.1038/s41598-025-02026-7 | Burdenko (public) → 20 Erlangen | patient | fold models applied, no fine-tuning stated | 0.753 | [full] |
| Yang 2026 JMRI, 10.1002/jmri.70419 | 121 → 72 | patient, ASL/DWI | — | 0.890 | [abs] |
| Jang 2020 Cancers, 10.3390/cancers12092706 | 2018 model → 104 | patient | failed, then retrained | — | [full] |

Every one: a single external cohort, one scan per patient, mostly a fixed window after treatment.

## Cross-cohort work on PRISM's datasets (not scan-level progression classification)

- CLARITY (Ding 2025, arXiv 2512.08029; ECCV 2026): MU → UCSF-ALPTDG zero-shot, treatment recommendation [full].
- Brain-WM (Wang 2026, arXiv 2603.07562): trained on LUMIERE + MU + UCSF-ALPTDG pooled → RHUH + UCSD; next treatment [full].
- Bio-SSM-Flow (GitHub only, Oct 2026): LUMIERE → frozen, pre-registered tests on UCSF-ALPTDG and MU; MRI forecasting,
  "does not perform response assessment" [README].
- BraTPRO, BraTS-Lighthouse 2025 Task 11 (Zenodo 10.5281/zenodo.15094823): LUMIERE → hidden EORTC-26101, 4-class RANO
  per scan pair; no hidden-test results found; three LNCS entries (10.1007/978-3-032-16370-7_21/_22/_23) unread.
- Jawad 2026 Neuro-Oncology suppl IMG-45: LUMIERE and MU, each cohort separately (not external) [abs].
- STRIDE (Guo 2026, arXiv 2610.08848): pretrain BraTS24 + LUMIERE, fine-tuned on Burdenko [full].
- Kamel 2026 AJNR (10.3174/ajnr.A9372), Siakallis 2026 Cancers: rule-based RANO from automatic masks on (probably)
  LUMIERE. Kickingereder 2019 Lancet Oncol: volumetric response, private → EORTC.
- Hashim 2026 Cureus: correction to our notes; no MU-built model was carried to another cohort.

## New single-cohort work to cite

- Farokhi Nia 2026, Mach Learn Knowl Extr 8(11):372, 10.3390/make8110372: MU, 180-day recurrence, holdout 0.786 [abs].
- Meta-analysis Zhang … Booth 2026 Neuro-Oncology, 10.1093/neuonc/noag259: 31 studies, 7 external test cohorts
  (219 patients), pooled external AUC 0.81 vs 0.91 internal [abs].

## Corrections to our notes

- Booth 2022 pooled 11 of 18 studies (summary AUC 0.765), not 18 (RELATED_WORK.md, comparison.md).
- Chen 2026 Bioengineering: the abstract names no datasets; "LUMIERE train / RHUH external" is unverified.

## Claims

Not defensible: first externally validated progression model; first with the model unchanged; first on conventional
MRI; first on these three cohorts together; first zero-shot use of UCSF-ALPTDG; first public-data external test.

Defensible ("to our knowledge"):
- First scan-level progression classifier developed on MU-Glioma-Post and applied without retraining to LUMIERE and
  UCSF-ALPTDG.
- The combination: every follow-up scan scored (not one early scan per patient); two external cohorts with the model
  unchanged (all prior learned classifiers found: one); conventional MRI and clinical history only; all data public.
