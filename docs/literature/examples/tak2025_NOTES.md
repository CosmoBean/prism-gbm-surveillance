# What to take from Tak et al. 2025 (NEJM AI) for PRISM

Tak D et al., "Longitudinal risk prediction for pediatric glioma with temporal deep learning", *NEJM AI* 2025. The study uses 715 patients and 3,994 serial MRI scans from three institutions, with four test cohorts. Notes written 2026-11-18.

## Writing

**Introduction: four paragraphs, each with one job.**
1. **Clinical stakes, with numbers.** Prognosis, progression rates of 40–80% after subtotal resection, and why patterns vary.
2. **The clinical need, stated as an action.** Recurrence is hard to see across many time points. Earlier prediction "would provide actionable information to counsel patients regarding adjuvant therapy ... or intensified surveillance."
3. **The technical gap.** "none has leveraged multiple scans as input". Why: data and dimensionality. What could close it.
4. **"In this study, we developed …"** Gives cohort size and institutions, with a pointer to Fig. 1, then a one-sentence finding and one forward-looking sentence.

**Voice**
- Confident and plain. Claims are made directly ("we found that temporal learning substantially improves …").
- Hedges appear only where they matter clinically ("external validation of calibration is recommended before clinical implementation").
- No development history anywhere.

**Negative results are stated bluntly and put to use.** A single-scan model is "essentially futile, with model predictions not much better than chance (AUROC of 0.58 …)". The failure becomes the contrast that makes the method look necessary.

**For PRISM:** say plainly that the combined model added no clear gain over timing and enhancement, and use it as the reason the separation matters.

**Results headings state findings.** For example, "Recurrence prediction performance depends on the number of longitudinal input scans available".

**Discussion structure**
1. What was done, plus "this study establishes such a framework".
2. **Clinical use, concretely.** It "could inform if and when to initiate therapy"; and "in patients with low projected risk, model outputs may provide reassurance and the ability to deintensify surveillance".
3. **Why the baselines failed**, stated frankly.
4. **Mechanism**, framed as what a clinician does ("mimics the behavior of an expert neuroradiologist").
5. **Limitations** in one paragraph opening with "This study has several limitations. First, …".
6. A conclusion about broad impact.

**Captions are long and stand alone.** Each defines every abbreviation at the end ("CBTN denotes …"). Panels are described in order ("Panel A shows …").

## Figures

| Their figure | What it does | PRISM equivalent |
|---|---|---|
| **Fig 1. Study design and method overview** in four panels: (A) cohort, then one patient's real MRI timeline with days between scans and a label at each scan; (B) the architecture; (C) training and fine-tuning flow, with an ROC; (D) the external tests, each with its ROC. | The whole study on one page, anchored on real scans. | Rebuild Fig 1 on a real MU patient: scans on a time axis labelled with **days since radiotherapy**, the 12-week window shaded, then three models → record → report → check, then LUMIERE and UCSF with their AUCs. This replaces the drawn phantoms. |
| **Fig 2. Dataset characteristics**: Kaplan–Meier curves, follow-up, scans per patient, **scan interval**, event rate and resection status for each cohort. | Shows how the cohorts differ before any model is shown. | One panel per cohort (MU, LUMIERE, UCSF): time since radiotherapy at each scan, split by progression vs not, plus the scan interval and the progression rate. This *shows* the timing confound and the cohort shift, which is currently argued only in text. |
| **Fig 3. Performance by cohort**: one row per cohort, each with an ROC and an **AUROC dot plot with CIs and significance brackets**, baseline vs method. | Every comparison is readable at a glance. | One row per cohort: imaging, clinical history, combined, and the timing-and-enhancement baseline as dots with CIs, plus brackets for the paired differences. This puts the main comparisons into a figure, which the reviewers asked for. |
| **Fig 4. Representative cases**: each patient is a strip of real axial slices with days between scans, a header (sex, resection, recurrence), a **heat bar of the predicted probability under each scan**, and an EVENT marker; a red arrow marks the lesion. | The model's behaviour over time for individual patients. | **The figure "auditable" needs.** For three or four MU or LUMIERE patients, show a strip of scans with days since radiotherapy, three coloured bars under each scan (imaging, clinical history and combined score) plus the conformal set, and the outcome. Include one case where the models disagree. |
| Fig 5. Performance as scans are added. Fig 6. Calibration for each cohort. | Behaviour as the input grows; calibration. | Calibration plots per cohort, which the methodology review asked for. These could go in the supplement. |

**House style to copy**
- **One colour per dataset**, used the same way in every figure.
- Thin sans-serif type.
- Panel letters with a short title.
- Database and person icons used only in the design figure.
- Real MRI in two of the main figures.
- CIs shown as error bars.
- Chance shown as a dashed diagonal.
