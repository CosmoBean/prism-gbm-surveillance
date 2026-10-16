# Journal rules: CMBBE: Imaging & Visualization (Taylor & Francis)

The submission rules for the PRISM paper (`paper/main.tex`), with the paper's status against each. Check this file
before every submission step, and recheck the live page before submitting, because T&F changes its rules.

**Sources**
- Live instructions for authors: https://www.tandfonline.com/action/authorSubmission?show=instructions&journalCode=tciv20
  - T&F blocks automated access to this page. **Sections A and B below were pasted from the live page by the user
    on 2026-10-16** and are the current rules.
- Section C comes from the 2022-06-19 Web Archive snapshot of the same page:
  http://web.archive.org/web/20220619034004/https://www.tandfonline.com/action/authorSubmission?show=instructions&journalCode=tciv20
  Confirm it against the live page.
- Journal home: https://www.tandfonline.com/journals/tciv20. DOAJ record (open access, APC):
  https://doaj.org/toc/2168-1171/about
- LaTeX template (Interact, CSE references): https://files.taylorandfrancis.com/InteractCSELaTeX.zip
- Journal comparison and the choice of journal: [DRAFT_NOTES.md](DRAFT_NOTES.md), section "Target journal".

Status key: **done** · **draft** (text present, authors must confirm) · **open** (authors must supply) ·
**at submission** (a step in the submission system, not in the manuscript).

## A. Declarations and front and back matter (live page, 2026-10-16)

| Rule (summarised from the live page) | Status in the paper |
|---|---|
| **Author details.** All authors must meet the T&F authorship criteria. The cover page gives each author's full name and affiliation, plus an ORCID and social media handle (Facebook, X or LinkedIn) where available. One corresponding author with an email address, normally shown in the PDF and online. The affiliation is where the research was done. An author who moves during review gives the new affiliation as a footnote. No affiliation changes after acceptance. | **open**: the title block in `main.tex` has placeholders for names, affiliations, ORCID and contact email. Social media handles are optional. |
| **CRediT roles.** The submitting author enters a CRediT role for every author during submission, and the roles are published with the article. | **at submission**: decide the roles in advance (authors). |
| **Video abstract.** Optional; T&F offers a paid creation service. | Not planned. |
| **Funding details.** Declare every source of financial support for the work reported, in the form "This work was supported by the [Funding Agency] under Grant [number]". If there was none, say so. | **open**: placeholder in `\section*{Funding}` gives both wordings. |
| **Disclosure statement.** Any financial or non-financial interest arising from direct applications of the research. If none: "The authors report there are no competing interests to declare." | **open**: placeholder. An editorial or advisory role at this journal held by any author belongs here and in the cover letter (see DRAFT_NOTES). |
| **Declaration of generative AI use.** State whether and how generative AI was used in the research and in preparing the manuscript. If none was used, say so. | **draft**: `\section*{Declaration of generative AI use}` added 2026-10-16. It covers the language models inside PRISM, the judge model and the AI assistant used for code, analysis and drafting. Authors must confirm it and extend it if other tools were used. |
| **Biographical note.** Short note for each author, no more than 200 words. | **open**: placeholder in `\section*{Notes on contributors}`. |
| **Data availability statement.** Where the data behind the results can be found, with a hyperlink, DOI or other persistent identifier. T&F provides templates. | **draft**: the three public data sets and their DOIs are listed. Still to decide: which derived data, fold files and model files are released, and where. |
| **Data deposition.** Data shared openly go to a recognised repository before or at submission; the submission asks for a DOI, a pre-reserved DOI or other identifier. | **open**: choose a repository (e.g. Zenodo, which can also archive the code release) if derived data are shared. BrainSegFounder weights must not be redistributed (UK Biobank MTA). |
| **Supplemental online material.** Any supporting files; published on Figshare. | **done** as a separate file (`paper/supplement.pdf`); upload it separately. |
| **Article extenders.** Graphical abstract, infographic, video, podcast, lay summary: optional, paid service available. | Optional. A graphical abstract could reuse Figure 1 (architecture). |
| **Figures.** 1200 dpi line art, 600 dpi greyscale, 300 dpi colour, at the printed size. Preferred formats: PS, JPEG, TIFF (or DOC/DOCX for figures drawn in Word); other types per "Submission of electronic artwork". | **open**: the figures exist as vector PDF plus 300 dpi PNG (`docs/manuscript/figures/`). For upload, export each as TIFF at printed size: 600 dpi for the charts, which mix colour and line work, and 1200 dpi for pure line art. Alternatively, EPS from the vector PDFs. |
| **Tables.** Must give new information rather than repeat the text, be readable without the text, and be supplied as editable files. | **partly**: captions and notes make Tables 1–3 readable alone, and LaTeX tables are editable. **To fix:** Results 3.4–3.5 repeat many Table 3 numbers; cite the table and keep only the key numbers in the text. Any new table (e.g. prespecified questions and answers) must follow this rule. |
| **Equations.** Editable (applies to Word submissions). | Not applicable (LaTeX). |
| **Units.** SI units, upright (not italic). | **done**: units are written as upright text (mm, days, GB). Recheck after edits. |

## B. Back matter order used in `main.tex`

Acknowledgements → Disclosure statement → Declaration of generative AI use → Funding → Ethics statement → Data
availability statement → Supplemental material → PRISM versions → Notes on contributors → References → Tables →
Figure legends.

## C. Format rules from the 2022 snapshot (confirm on the live page)

| Rule | Status |
|---|---|
| Article: no word limit | **done**: no length change needed |
| Abstract: unstructured, 100–150 words | **done**: 148 words (2026-10-16) |
| Keywords: no more than 3 (the 2022 page; some T&F journals now allow 3–6) | **done**: 3 |
| British spelling with -ise endings | **done**: recheck after edits |
| Template: T&F Interact (Word or LaTeX); submit LaTeX source together with the PDF | **done**: `interact` class, `largeformat` |
| References: CSE name-year (`tfcse.bst`) | **done** |
| Review: single-anonymous (names on the manuscript) | **done** |
| Open access: APC US$2,630 (DOAJ, 2026-10-15); waivers and institutional agreements possible | Authors: check institutional agreements |

## D. Submission checklist (before upload)

1. Recheck the live instructions page against this file; update anything that changed.
2. Fill every `\todo{PENDING ...}` and resolve every `\flag{[CHECK]}` in `main.tex` and `supplement.tex`.
3. Authors: names, affiliations, ORCIDs, corresponding author email, CRediT roles, biographies (≤ 200 words each).
4. Declarations: disclosure (including any editorial-board role at this journal), funding (or "no funding"),
   generative AI use (confirm the draft), ethics, data availability with persistent identifiers.
5. Figures exported as separate TIFF (or EPS) files at the required resolution and printed size.
6. Supplement uploaded as a separate file; LaTeX source plus compiled PDF.
7. Cover letter: novelty, fit with the journal, any conflict of interest with the editorial board, and a request
   that a board member with a conflict does not handle the paper.
