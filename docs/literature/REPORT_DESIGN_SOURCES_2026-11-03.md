# Report design sources: clinician reports, BT-RADS and other decision-support outputs (2026-11-03)

Why: the author asked whether PRISM's report can be compared with real clinician reports, and which published
systems and templates its design can be cited against. Web searches by two research agents plus primary-source
checks; no patient data used. Paper changes: Methods paragraph after the checker (Sec 2.1) and Supplementary S24 /
Table S46.

## 1. Public data with clinician-written reports

**None pairs post-treatment glioma follow-up MRI with real clinician reports.**

| Source | Reports? | Note |
|---|---|---|
| MU-Glioma-Post (TCIA, 10.7937/7K9K-3C83) | no | clinical, treatment, progression tables only |
| LUMIERE (Suter 2022) | no | one rater's RANO rating with a written rationale per timepoint (RANO is out of the paper) |
| UCSF-ALPTDG (Fields 2024) | no | progression by expert consensus; DUA |
| BraTS 2024 post-treatment, UCSF-PDGM, RHUH-GBM, Burdenko, TCGA-GBM/LGG (VASARI) | no | images, masks, labels |
| MIMIC-IV-Note (PhysioNet, credentialed) | yes, 2.3M radiology reports incl. MRI; no images | not our patients; local models only under its DUA; glioma follow-up count not verified |
| MR-RATE (98k brain/spine MRI, LLM-restructured reports), MSKBrain (77k, data not released), RadGenome-Brain MRI (reports written after the fact for pre-op BraTS) | partly | none is post-treatment glioma follow-up with original reports |

Routes to a true comparison, best first: ask the UCSF / Calabrese group for de-identified reports of the ALPTDG
scans (DUA amendment); a local-only style comparison against MIMIC-IV-Note brain tumour follow-up reports.

## 2. BT-RADS (primary documents read 2026-11-03 from btrads.com)

- Follow-up template v1.03: clinical indication (tumour type and mutations; last surgery date; radiation
  completion date; medications: Avastin or steroids); technique; comparison; findings (location; FLAIR change and
  new FLAIR; enhancement change at the primary site and new enhancement; diffusion; perfusion; spectroscopy;
  post-treatment changes); additional findings; impression score with a legend.
- Categories v1.01: 0 not scored; 1a improvement; 1b medication effect; 2 no change; 3a favour treatment effect;
  3b indeterminate; 3c favour tumour progression; 4 highly suspicious for progression. Management: 0-2 continued
  follow-up; 3a-3b shorter follow-up interval; 3c consider change in management vs shorter interval; 4 consider
  change in management.
- Full guide v1.02: **3a requires worsening within 12 weeks of completing the most recent CRT; 3b is outside 12
  weeks.** 3c/4 use a 25% increase in enhancing or FLAIR component. PRISM's phase of care uses the same 12-week
  boundary (facts_v3 PHASE_TEXT); this is a coincidence of boundaries, not a design choice taken from BT-RADS.

Citations (Crossref-checked): weinberg2018 (JACR 15(5):767-771), gore2019 (Acad Radiol 26(7):974-980; 53 then
38 clinicians surveyed; less ambiguity, more consistency; 81% template use at 9 months), zhang2020 (Acad Radiol
27(6):780-784; 211 vs 172 reports; more history, fewer hedges), thust2018 (Eur Radiol 28(8):3306-3317; 220 centres;
60% qualitative follow-up reports, 27% RANO, 23% template).

## 3. Other decision-support outputs (agent survey; items marked * not verified by us)

- Cleared tools output volumes, overlays and prior-scan comparison with an "adjunct, not for primary diagnosis"
  disclaimer: Neosoma NS-HGlio (K221738)*, Cortechs NeuroQuant brain tumour (K241098)*, Brainlab RT Elements
  (K250440, RT contouring)*. None shows uncertainty.
- Research systems: automated volumetric response (Kickingereder 2019; Chang 2019 AutoRANO); BrICS-LIT (Ramesh 2020,
  up to 5 timepoints, dose overlays, BT-RADS support)*; agentic BT-RADS (jabal2026, already cited); TumorBoard
  (liu2026, defers when evidence is weak); BTReport (herasrivera2026, deterministic features, LLM writes narrative).
- Clinician-facing output evidence: Model Facts label (Sendak 2020)*; Radiology: AI 2023 interface study
  (10.1148/ryai.220079)*: radiologists preferred text + confidence + overlay, but only text-only output improved
  their performance.
- What PRISM does that none found does: conformal sets shown per scan; image and timeline scores side by side with
  an agreement flag; a reliability card per scan; a deterministic check of every number in the text.
- What others do that PRISM does not: image overlays; multi-timepoint plots; a standard category (BT-RADS); deferral
  when evidence is weak; radiation-field context.
