# Report figure (Figure 5a): format research and redesign

Research by a sub-agent, 2026-11-19; the redesign it led to is `scripts/fig5_report.py` (what was built, and what
was not, is at the end).

## 1. Findings

### 1.1 Structured radiology reporting and brain-tumour follow-up
- **BT-RADS follow-up template** (PowerScribe B03b; http://btrads.com/wp-content/uploads/2018/05/powerscribe_templates_2018_05_24.zip,
  https://btrads.com/resources/; Weinberg et al. JACR 2018, https://pubmed.ncbi.nlm.nih.gov/29503151/). Order: exam →
  clinical indication → clinical block (tumour type and mutations; surgical and radiation history; medications) →
  technique → comparison → findings: tumour → additional findings → legend → impression. Tumour findings are one line
  per compartment in a closed vocabulary ("FLAIR: no change / increasing / decreasing"). The impression is numbered.
  After adoption, referrers rated reports more consistent and less ambiguous
  (https://radiologybusiness.com/topics/imaging-informatics/structured-reports-improve-perceptions-radiologists).
- **RANO 2.0** (Wen et al., JCO 2023; https://pmc.ncbi.nlm.nih.gov/articles/PMC11493521/): the post-RT scan is the
  baseline, change is judged against baseline or nadir, and within 12 weeks of RT progression needs confirmation, so
  the comparison point and the time since RT belong at the top. (Background only: the paper does not use RANO.)
- **ESR structured reporting update 2023** (https://pmc.ncbi.nlm.nih.gov/articles/PMC10667169): standard structure
  and lexicon; quantitative data inserted automatically; AI results through the IHE AI Results profile.
- **Structure helps:** Schwartz et al., Radiology 2011 (https://pmc.ncbi.nlm.nih.gov/articles/PMC3121011); Bink et
  al., Front Neurol 2018 on intracranial tumours (https://www.frontiersin.org/journals/neurology/articles/10.3389/fneur.2018.00032/full).
- **What referrers read:** about a third read the body only if the impression flags an abnormality; about 80% want
  a numbered or bulleted impression
  (https://www.auntminnie.com/imaging-informatics/enterprise-imaging/is/article/15593540/radiology-reports-what-do-physicians-really-want).

### 1.2 How AI output is shown to clinicians
- **Model Facts label** (Sendak et al. 2020, https://pmc.ncbi.nlm.nih.gov/articles/PMC7090057/): one page, fixed
  order (name, locale, version; summary; mechanism; validation; uses; warnings), localised and versioned. Warnings and
  validation are fixed blocks, not repeated in every sentence.
- **FDA-cleared imaging AI** (https://www.nature.com/articles/s41746-024-01080-1.pdf): a compact core output (flag,
  score or measurement) plus supporting detail, often a secondary-capture page in PACS. Brainomix e-ASPECTS: number,
  overlay, edited results labelled (https://www.brainomix.com/stroke/e-aspects/).
- **NeuroQuant / icobrain reports:** demographics header → row of overlay images → table of volume, normalised
  volume and percentile against a reference → reference charts; icobrain adds longitudinal percent change
  (https://pmc.ncbi.nlm.nih.gov/articles/PMC10585089). Each number is shown against its reference.
- **Prediction sets shown to people:** conformal sets improved human accuracy over top-k in a pre-registered RCT
  (Cresswell et al., ICML 2024, https://arxiv.org/abs/2401.13744); sets help most out of distribution and when small
  (CHI 2024, https://arxiv.org/abs/2401.08876). Show the set literally, with its level, never as a probability.
- **The display changes performance**, and preference does not track performance
  (https://pmc.ncbi.nlm.nih.gov/articles/PMC10245182).

### 1.3 Longitudinal volumetry
- Tables across timepoints with absolute and percent change are the norm (icobrain; UCSF automated low-grade glioma
  volumetry for tumour boards, https://arxiv.org/pdf/2212.14177).
- Change is read against measurement error (QIBA: change is real if X > 2.77 × wCV,
  https://qibawiki.rsna.org:443/images/c/c3/CT-VOLUMETRY-Poster_QIBA_Kiosk_RSNA2015.pdf). PRISM's counterparts: the
  word "indicative" and the enhancement rule.
- A two-point line plot only repeats two numbers; a sparkline earns its place with three or more points.

### 1.4 Report figures in high-impact papers
- Tak et al., NEJM AI 2025: real scans with a score bar under each scan; the output is visual, not prose.
- Tanno et al., Nat Med 2024 (https://doi.org/10.1038/s41591-024-03302-1): generated and clinician reports side by
  side as short text blocks.
- MAIRA-2, Fig. 3 (https://arxiv.org/html/2406.04449v1): a grounded report is a list of short sentences, each keyed
  to its evidence by number or colour, not by a caption under every line.

## 2. What the old Figure 5a did oddly
1. It was not what PRISM renders: `prism/report/sections_v3.py` puts a deterministic table after each section's prose
   ("1. What the scan shows" … "4. How much to trust this here"); the figure dropped the tables and invented headings.
2. A monospace key under every sentence doubled its length, and truncated keys could not be checked.
3. No comparison header (interval, smallest earlier volume), though the record holds both.
4. No bottom line: the facts that matter were buried in sentences 3, 6 and 10.
5. Repetition: the disagreement three times, the score meaning twice.
6. Numbers in prose rather than a table; necrosis and cavity missing.
7. Scores without their reference shown visually; no house score colour in the panel.
8. The conformal set as a bare sentence, no {0, 1} notation, no 90% set.
9. The reliability tier as a word, the three-state scale never shown.
10. Cartoon brains took a third of the panel; the two-point plot repeated two numbers.
11. Five font sizes, three styles, ~92-character lines.

## 3. Redesign principles (applied)
- A report page in BT-RADS order: header (timing, comparison, flags) → measurements → scores → card → report text →
  limitations.
- Numbers in tables and graphics; the language model's sentences once, numbered, with a separate column of cited
  fields (full keys, never truncated). Nothing said twice in the deterministic parts.
- House colours only for the three scores; navy for structure; grey for references (median ticks).
- Scores as dots on a 0–1 track with the cohort median as a tick; sets as {0}, {1}, {0, 1} at 80% and 90%.
- Tier as a three-state scale with the active tier filled.

## 4. What was built, and what was not
Built (`scripts/fig5_report.py`, 2026-11-19): the page above for a **real** report instead of a synthetic one: MU
PatientID_0029 Timepoint 4, the progression scan of strip C in the case-strip figure, held out from prompt
development, report v3.2 accepted by the checker (asserted in the script). Every value is read from the record's facts
and the model output; the slices follow the report's own segmentation rules (`prism/report/seg_figure.py`).

Not built:
- the research's "Summary" block of three numbered points: deterministic but new to the rendered report; the flag
  chips in the header do that job from fields the report already has;
- a volume sparkline (only two earlier scans; the table carries the comparison).

Open: `sections_v3.render_html` still uses the v3.1 keys (`pathway.*`); if the page layout should also become the
system's own HTML output, port this layout there (no change to the language model or the checker).
