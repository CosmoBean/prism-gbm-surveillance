# The story and the results behind it

What we have, what each result does for the story, and where it goes. Agree on this before writing prose.
[OUTLINE.md](OUTLINE.md) holds the abstract and figure plan; [STYLE.md](STYLE.md) the rules; [RESERVE.md](RESERVE.md)
the answers held back for reviewers.

Status labels: **planned** = rule written down before the run; **exploratory** = added after results were seen.
All numbers are grade 4, MU-Glioma-Post, repeated 5 × 5 patient-grouped cross-validation, unless stated.

## The story in one paragraph

We built PRISM to predict progression from surveillance MRI, and its first test gave an AUC of 0.80. A model with no
images did better on the same test patients, which told us the score was coming from somewhere other than the
tumour. PRISM was rebuilt to keep the two kinds of evidence a clinician weighs apart: what the images show, and
where the patient is in treatment. Taking them apart showed that the treatment timeline carries most of what any
model can do, because progression is called late in treatment. Every assumption we gave the image model raised its
score by teaching it the timeline, yet within a phase of care the images held their own. So PRISM shows both kinds
of evidence for every scan, says where each is reliable, and flags the weeks after radiotherapy, where neither has
been shown to be.

## The results, step by step

### Step 1. A favourable split, not a good model

| Result | Number | Status | Goes to | Source |
|---|---|---|---|---|
| First test: PRISM's initial radiomics model, one split (all gliomas, 29 test patients) | 0.80 | historical | Abstract, Results 1, Fig 2 | Table 2 |
| Same split, model with no images (clinical + timing + treatment) | 0.87 | planned (rescoring) | Abstract (as "did better"), Fig 2 | Table 2 |
| Same split, a rule with no training: "the scan is after RT" | 0.74 | exploratory | Results 1 (the persuasive number) | main.tex 3.2 |
| Why: 36 of the 60 negative test scans were taken before RT, none progressed | 60% of pairs | | Results 1, Fig 2B | main.tex 3.2 |
| The same pipeline over 500 splits of the same design | mean 0.72; first split above 92% of them | planned | Abstract, Fig 2 | Table 2 |
| Same model with no images under repeated CV vs on the first split | 0.72 vs 0.87 (all gliomas) | planned | Results 1 (one sentence) | main.tex 3.2 |

The step ends on the question: what made the split easy? Answer: its mix of phases of care.

### Step 2. The treatment timeline carries most of the score

| Result | Number | Status | Goes to | Source |
|---|---|---|---|---|
| Detection at the scan: clinical + timeline, no images | **0.82 (0.75–0.90)** | planned | Abstract, Results 2, Table 2 | DETECTION_TASK.md |
| Detection: clinical alone | 0.53 | planned | Results 2 (shows the gain is the timeline) | DETECTION_TASK.md |
| Detection: everything combined | 0.84 (0.76–0.90); images add +0.015 (−0.03 to +0.06) | planned | Results 2, Table 2 | DETECTION_TASK.md |
| Why: 56 of 62 progression scans are > 12 weeks after RT; 51 of 84 stable scans are within 12 weeks | counts | planned | Results 2 (concrete counts persuade) | DETECTION_TASK.md |
| 120-day risk: clinical alone → + timing → + treatment status | 0.59 → 0.64 → 0.70 | planned | Results 2 (one sentence) or Fig | main.tex 3.3 |
| 120-day risk: four phase-of-care categories recover most of the gain | 0.66 vs 0.59 | planned | Reserve or one clause | main.tex 3.3 |

### Step 3. What each assumption buys the images

| Result | Number | Status | Goes to | Source |
|---|---|---|---|---|
| Images: the scan alone (volumes, shape, intensity) | 0.66 | exploratory | Abstract, Fig 3 | DETECTION_TASK.md, exploratory section |
| + comparison with earlier scans (growth, ratio to smallest volume) | 0.71 (+0.05, −0.00 to +0.11) | exploratory | Fig 3 | same |
| + scan-schedule context (days since previous scan, has previous, RT-anchored nadir) | 0.81 (+0.10, +0.05 to +0.15) | planned model; decomposition exploratory | Abstract, Fig 3 | same |
| Within a phase of care: every image version | 0.66–0.68 | exploratory | Abstract ("about 0.68"), Fig 3 | same |
| Within a phase of care: the timeline | 0.64 | planned | Abstract ("as much as"), Fig 3 | DETECTION_TASK.md |
| Fine-tuned networks given none of these assumptions (9 arms) | image-only 0.45–0.57; the shuffled-label control 0.48 | planned | Results 3 (one sentence) | DETECTION_DEEP.md |
| 120-day risk: no imaging branch added to the timeline model (radiomics, frozen and fine-tuned encoders) | −0.03 to +0.02 | planned | Results 3 (one sentence), Table 3 | Table 3 |

### Step 4. Where PRISM is meant to be used

| Result | Number | Status | Goes to | Source |
|---|---|---|---|---|
| 120-day risk from the start of RT (intended use) | 0.60 (0.52–0.69) | planned | Results 4 (always in the main text) | INTENDED_USE.md |
| The early post-RT window: progression scans available to test detection | 4 of 55 scans | planned | Results 4, Fig 4 (why PRISM flags it) | DETECTION_TASK.md |
| LUMIERE (no treatment dates): locked detection model | 0.77 (0.68–0.86); without images 0.69; images add +0.08 (−0.01 to +0.16) | planned (the no-image reference exploratory) | Results 4 (images carry more where dates are missing) | DETECTION_TASK.md |
| LUMIERE, outside the rater's early post-RT window | images add +0.13 (+0.01 to +0.23) | exploratory | Reserve | same |

### Step 5. What the record shows, and the report

| Result | Number | Status | Goes to | Source |
|---|---|---|---|---|
| Shortcuts found by reading the record: unknown-IDH shortcut, molecular look-ahead, documentation leak, cause of external miscalibration | 4 findings | planned audit | Results 5, Fig 5A | main.tex 3.5 |
| Corrected model after removing them | 0.68 (0.60–0.76), well calibrated | planned | Results 5 | main.tex 3.5 |
| Reports: passed the faithfulness checker / contained every required item | 249 / 249; 247 / 249 | planned | Results 5 (one sentence), Fig 5B | main.tex 3.6 |
| No clinician has read the reports | — | | Discussion (always) | |

## Results that complicate the story (handle, do not hide)

| Result | What it says | How we handle it |
|---|---|---|
| All gliomas, detection on all scans: images add +0.041 (+0.006 to +0.081) to the timeline | Outside grade 4 the images add a little, measurably | One sentence in Results 3; consistent with "images hold their own" |
| LUMIERE: images add +0.08 | Where timing is missing, images carry more | Supports the story; Results 4 |
| The "images only" model as originally specified scored 0.81 | Our own planned imaging model contained timing | Told openly as the third rung of the ladder; this is the finding, not a flaw to hide |
| Detection was a planned go/no-go study and the answer was no-go (images did not add +0.03 to the timeline) | The prespecified question was answered negatively | Table 3 lists it as planned with its answer; the text describes what was found, without go/no-go language |
| Forward external test: locked 120-day model on LUMIERE 0.61; corrected 0.64 | Modest transport for 120-day risk | Reserve / supplement; 120-day risk is not the headline |

## Gaps to fill before prose
1. Images alone for 120-day risk with the timing inputs removed (as for detection), and within-phase AUCs for
   120-day risk, so Table 2 has the same columns for both questions.
2. Images alone on LUMIERE (the transportable model without clinical and timing inputs).
3. Bootstrap interval for "within a phase, images vs timeline" (I_pure − B1 phase-stratified: +0.04, −0.15 to +0.19;
   wide; supports "as much as", not "more than").

## Gaps filled (2026-10-24, exploratory; `scripts/exploratory_pure_imaging_forward_lumiere.py`)

**120-day risk, grade 4 (IPCW AUC, marginal KM; images = volumes, shape, intensity, change from the previous scan,
ratio to the whole-history smallest volume; no days, no flags):**

| | images alone | corrected core (timeline + clinical) | both |
|---|---|---|---|
| all scans (249) | 0.65 (0.57–0.73) | 0.68 (0.60–0.76) | 0.69 (0.62–0.77) |
| all scans, within phase | 0.62 (0.54–0.71) | 0.61 (0.53–0.69) | 0.64 |
| intended use (173) | 0.62 (0.54–0.70) | 0.60 (0.52–0.68) | 0.62 |
| intended use, within phase | 0.62 (0.52–0.71) | 0.62 (0.52–0.70) | 0.63 |

- Images alone − core in the intended use: +0.02 (−0.10 to +0.14). Both − core: +0.015 (−0.08 to +0.10).
- Before RT, images rank scans (0.78, descriptive; few events) where the core model does not (0.49).
- Comparison with earlier scans adds nothing for 120-day risk (+0.002); the timing proxies cost 0.01.
- Reading: for 120-day risk, images and timeline are equally weak (about 0.62 where PRISM is meant to be used), and
  combining them does not help.

**LUMIERE detection, locked, image inputs only** (ET, necrosis + cavity, oedema volumes and their ratios to the
previous scan): 0.66 (0.57–0.73). Clinical + timeline only 0.69 (0.60–0.81). Both 0.77 (0.68–0.86). On LUMIERE the
two pathways are complementary: together they beat either alone.

## UCSF-ALPTDG results (2026-10-26; plan pre-specified at 0e7c9fe; details in docs/results/UCSF_RESULTS.md, UCSF_AUDIT.md)

Grade 4, scan 2 (29 progression / 40 stable); all gliomas 48 / 78 give the same picture.

| | locked MU model | trained on UCSF |
|---|---|---|
| clinical alone | 0.50 | 0.41 |
| UCSF timeline (no RT end date; B1 not buildable) | – | 0.67 |
| images, scan alone | 0.80 | 0.83 |
| images + change | 0.73 | 0.86 |
| LUMIERE image set | 0.89 | 0.91 |
| deep networks (G1 / G3 / transfer) | 0.75 / 0.71 / – | 0.74 / 0.74 / 0.75 |
| deep, permuted labels | – | 0.54 |

- Audit: no leakage, but enhancing-tumour volume alone gives 0.88; 27 of 29 positives are UCSF-rated "ET increased";
  within ET-increased scans the images fall to 0.53–0.65; every deep score tracks ET volume (r ≈ 0.8).
- Reading: on UCSF the label is an enhancement call at the same scan, so images score high by re-detecting it. The
  cohort's labelling decides what a model learns: the timeline on MU, enhancement on UCSF. This fits the paper's
  question ("what has the model learned to see?") and needs a story decision with the author.
- UCSF's own train/test split: the timeline model 0.45 vs median 0.72 over 100 random splits (split variance again).

## The full system (2026-10-26; SYSTEM_PLAN.md e7cba80; SYSTEM_RESULTS.md, REPORT_V3.md, RELIABILITY_CARD.md)

| | MU | LUMIERE | UCSF |
|---|---|---|---|
| conformal coverage, combined score, α 0.2 (target 0.78) | 0.82 | 0.87 | 0.78 |
| reports faithful (frozen checker) | 114/114 | 0/178 (prompt asks for a fact not in the record) | 140/140 |
| tier stated where evidence is thin | 71/71 | 19/19 | 140/140 |

- Pathway disagreement is the flag that picks out errors on MU (S2 +0.31; S3 +0.08 beyond case mix). "Any flag"
  marks 91–100% of scans (unusable as one warning). The card tier measures evidence, not accuracy.
- Perturbations: reports followed the changed field in 29/30.
- Literature (SYSTEM_LANDSCAPE.md): components exist separately; the combination appears new (moderate claim).
