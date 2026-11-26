# Where PRISM's report design comes from: the evidence (2026-11-20)

Purpose: the evidence base for saying in the paper where the design of PRISM's report comes from, meaning what
peer-reviewed work and official documents say about how clinicians want follow-up MRI reports and AI output
presented, mapped onto the report as built. It replaces the trade-press items in
`docs/review/REPORT_FORMAT_RESEARCH.md` (auntminnie, radiologybusiness) and settles the items marked "* not verified"
in `docs/literature/REPORT_DESIGN_SOURCES_2026-11-03.md`. Nothing in `paper/` was edited.

**How sources were checked.** Every source kept below was checked against its DOI on Crossref (authors, year,
journal, volume, pages). The finding attributed to it was then read in the PubMed abstract, the publisher page or the
proceedings page. Trade press was dropped. Conference abstracts and preprints are marked as such. Section 6 lists what
could not be verified.

**What the report is, as built** (read from the code on 2026-11-20):

- **Record.** `prism/report/facts_v3_2.py` (v3.2 = v3.1 with the paper's model names). The language model sees
  only the record. Its prompt is `prompts_v3_2.py`, prompt v3.5, which is a renamed v3.4.
- **Model output.** JSON-schema decoding into a list of sentences. Each sentence carries a section tag (scan, models,
  combined, trust) and the record keys it cites. The sentences come in a fixed order (a to j):
  - timing;
  - indicative volumes;
  - change since the previous scan and since the smallest earlier enhancing volume;
  - one sentence per model, giving what it is based on and its score relative to the cohort median;
  - agreement;
  - the combined score and what a score means;
  - the 80% conformal set of the combined score;
  - the situation and tier from the card;
  - one sentence per raised flag.

  The rules for the text are: under 260 words, "no lists, no headings", numbers copied as digits, and fixed phrases
  copied ("tested" / "few cases" / "not tested"; "both outcomes" / "progression only" / "no progression only";
  "agree" / "disagree").
- **Forbidden content (prompt and checker).** The prompt and `checker.py` (`FORBIDDEN`, `V3_FORBIDDEN`) forbid:
  - diagnosis wording ("consistent with", "suggestive of", "shows progression", ...);
  - response categories (PD/SD/PR/CR and their words);
  - management ("recommend", "should", "must", "consider", biopsy, drugs, "follow-up imaging", "MDT", "decision", ...);
  - certainty words ("definitely", "rules out", "confirm");
  - verbal probability ("likely", "unlikely", "high risk", "reassuring", "concerning", "benign", "favourable").

  Disclaimers in the text are forbidden, because the report has a fixed limitations block.
- **Deterministic parts.** These come from `sections_v3.py` and are never written by the language model:
  - a timing row;
  - a table of volumes, with change since the previous scan (cc, %) and the enhancing volume against the smallest
    earlier volume;
  - a score table: model, based on, score, cohort median, side, 80% and 90% sets;
  - agreement, the meaning of a score and the conformal method;
  - a card table: situation, tier, tier rule, measured agreement, four flags;
  - the fixed limitations paragraph;
  - the attached segmentation figure.
- **Two layouts.** The system renderer (`render_md` / `render_html`, used for v3 and v3.1) places each section's
  prose first and its table after it, in four headed sections ("1. What the scan shows", "2. The two pathways",
  "3. The combined score", "4. How much to trust this here"). It joins the sentences into one paragraph. Figure 5a
  (`scripts/fig5_report.py`, v3.2) is drawn differently, in this order:
  1. header with timing, comparison and flag chips;
  2. images beside the volume table;
  3. score tracks with median ticks and the sets as {0}, {1} or {0, 1};
  4. a three-state tier scale;
  5. the model's sentences, numbered, with the cited keys in a column;
  6. the limitations.

  There is no v3.2 page renderer (`prism/analyses/report_v3_2.py` renders none), so the Figure 5a layout exists only
  in the figure script.

---

## (a) Summary

- **Overall.** Most of PRISM's report design rests on evidence that is either indirect (surveys of referring
  clinicians about radiologists' reports) or from another field (AI-advice and uncertainty-display experiments outside
  neuro-oncology). No study has asked neuro-oncology clinicians what an AI follow-up report should contain, and no
  clinician has read a PRISM report.
- **Choices with direct support:**
  - a structured layout with tables plus a short narrative. Clinicians prefer this blend in a recent survey of 477
    (Kowalczyk 2025), prefer tables with a comment (Plumb 2009), rate structured reports clearer (Schwartz 2011), and
    rated BT-RADS reports more consistent and less ambiguous (Gore 2019);
  - automated volumetry. It supports more reproducible response assessment in neuro-oncology (Vollmuth 2023;
    Kickingereder 2019; Chang 2019);
  - attaching the images. Clinicians ask for images (Bosmans 2011b; Ignácio 2018), and annotated AI advice gave the
    highest accuracy (Gaube 2023);
  - numeric uncertainty in place of verbal hedges. Verbal certainty phrases vary between radiologists (Shinagare
    2019), and guidance favours stated ranges (van der Bles 2019; Spiegelhalter 2017).
- **Choices supported only by analogy:**
  - conformal sets shown literally (Cresswell 2024; Zhang 2024, in non-clinical image labelling);
  - the reliability card and fixed limitations (Sendak 2020 Model Facts; Mitchell 2019);
  - sentences that cite record keys (grounded reporting: MAIRA-2, a preprint; error studies of generated reports:
    Tanno 2025);
  - the language model limited to prose (BTReport, a preprint);
  - no category or advice. Automation-bias experiments support it: incorrect AI BI-RADS suggestions cut readers'
    accuracy sharply (Dratsch 2023), and inaccurate advice harmed accuracy whatever its label (Gaube 2021; Yu 2024).
- **Choices with no support or contrary evidence:**
  - three scores shown beside a cohort median. In the one interface trial, adding an AI confidence score to text did
    not improve readers, while text alone did (Tang 2023);
  - the model-agreement statement (no study found);
  - no conclusion or impression. Referring clinicians ask for a conclusion (Bosmans 2011b), and BT-RADS itself is
    "management-based" (Weinberg 2018);
  - length and repetition. The example report states the disagreement in three places, and concise reporting is a
    recurring request (Bosmans 2011b; Wallis 2011). Detailed reports were preferred to brief ones, however (Plumb
    2009), so the evidence points against repetition rather than against detail.
- **Mismatches in the paper text:**
  - the claim that the report "follows the content of the BT-RADS follow-up template" overstates what is shared;
  - the Figure 5 caption's "order of the BT-RADS follow-up template" describes the figure script, not the system's
    renderer.

  Section 7 gives the wording points.

---

## (b) Design choice → evidence

Strength codes:

- **D** = direct evidence: a trial, a reader study or a survey of clinicians about this kind of output;
- **G** = guideline, consensus or official template;
- **A** = analogy from another field or another kind of report;
- **—** = no support found;
- **✗** = evidence against.

| # | Design choice (as built) | Sources | Strength | Notes |
|---|---|---|---|---|
| 1 | Section order: timing and comparison, then measurements, then scores, sets and card, then text, then limitations (Figure 5a). The system renderer instead puts prose before the table in each section | weinberg2018 (BT-RADS template order: indication, history, comparison, findings, impression); dossantos2023, esr2018 (standard structure); bink2018 | G | BT-RADS ends with the impression, and PRISM puts its scores where the impression would be. The figure then repeats everything as prose, which BT-RADS does not. No study tests section order for AI output. Clinger 1988 found referrers split on where the summary goes (32% beginning, 29% end) |
| 2 | Header with timing (time after radiotherapy, with the 12-week boundary) and comparison (days since the previous scan) | weinberg2018 (template: surgery and radiation dates; the 12-week rule for category 3a); wen2023 (RANO 2.0: the post-radiotherapy baseline and the 12-week window; Introduction use only); bosmans2011b (clinical information requested); kahn2009 | G | RANO is cited only as other people's criteria (STYLE §2) |
| 3 | Measurements in a table (enhancing, FLAIR, necrosis and cavity volumes; change in cc and %) labelled indicative | plumb2009 (tables with a comment preferred, n=49); kowalczyk2025 (blended structure and narrative preferred by 62.5% of 477); schwartz2011 (clarity and content higher); bosmans2011a (itemised reports preferred for complex examinations); vollmuth2023 (AI volumetry improves reproducibility of time-to-progression ratings, CCC 0.77 to 0.91); kickingereder2019; chang2019; abayazeed2023 | D | sistrom2005: structured and free text were equally efficient and accurate, but structured was preferred. johnson2009: structured reporting lowered residents' accuracy and completeness for stroke MRI, which is contrary evidence for templates filled in by humans |
| 4 | "Indicative" label on volumes from automatic segmentation | hoebel2024 (experts' ratings of glioma segmentation quality vary, α = 0.34, and Dice does not track them); chang2019; abayazeed2023 (post-operative Dice about 0.75–0.78) | D | Supports labelling the volumes and showing the masks so that the reader can judge them |
| 5 | Segmentation slices attached to the report (deterministic, not seen by the language model) | gaube2023 (annotated AI advice gave the highest accuracy); bosmans2011b (integrate or refer to images); ignacio2018 (59.4% want images with the report); tang2023 (an overlay was preferred by 8 of 10 readers but did not improve AUC) | D (mixed) | Preference and benefit diverge (tang2023) |
| 6 | Three scores, each beside its cohort median and a "side" (above or below) | sendak2020 (show output with its context); yang2023 (NeuroQuant volumes reported as normative percentiles) | A / ✗ | tang2023: text plus an AI confidence score did not improve readers (AUC 0.77 against 0.82 with no AI, P = .46); text only did (0.87). No study of a score against a cohort median was found |
| 7 | Conformal sets shown literally ({0}, {1}, {0, 1}, at 80% and 90%) with fixed phrases | cresswell2024 (pre-registered RCT: conformal sets raised accuracy over fixed-size sets); zhang2024chi (sets help most out of distribution and when small); kompa2021 (communicate uncertainty, allow abstention); goddard2012 (confidence attached to output mitigates automation bias) | A | All of this is multi-class image labelling by lay participants. In a binary task the set {0, 1} carries no ranking information, and zhang2024chi found large sets less useful |
| 8 | Reliability card tier (tested, few cases, not tested) with case counts, and fixed limitations | sendak2020 (Model Facts label: one page, validation and warnings in fixed blocks); mitchell2019 (cited); vanderbles2019 (indirect uncertainty, the quality of the evidence behind a number, should be stated) | A / G | No clinical test of a per-scan evidence tier was found |
| 9 | Model-agreement statement and flag | — | — | Closest is kompa2021 (disagreement as a cue for uncertainty). No display study found |
| 10 | No diagnosis, no response or BT-RADS category, no advice (prompt and checker) | dratsch2023 (incorrect AI BI-RADS category suggestions dropped correct ratings from about 80% to 20–46%); gaube2021 (inaccurate advice lowered accuracy whatever its labelled source); yu2024 (inaccurate AI harmed 140 radiologists); goddard2012; parillo2023 (BT-RADS discordance would have changed management in 18% of cases) | A | ✗ in part: clinicians ask radiologists for a conclusion, a diagnosis or differential (bosmans2011b; ignacio2018: 75.7% want differentials with their degree of certainty), and BT-RADS is "management-based" (weinberg2018; gore2019: facilitation of management rated higher). PRISM is an adjunct to the radiologist's read, not a replacement, which is the stated reason for the difference |
| 11 | No verbal probability or certainty words; position stated only as above or below the median | shinagare2019 (radiologists' certainty phrases are unreliable; Krippendorff α low); panicek2016 (a standard certainty lexicon); bruno2017; vanderbles2019 and spiegelhalter2017 (numbers with ranges are read more consistently than words); wallis2011 (avoid hedging) | G / D | panicek2016 and shinagare2019 argue for a standard lexicon rather than for removing words altogether. PRISM goes further, which is consistent with them but not tested |
| 12 | Every sentence cites record keys, and a checker and verifier tie numbers to fields | tanno2025 (clinically significant errors in 22.8% of in- and outpatient AI reports only, and in 24.8% in both AI and human reports); bannur2024 (grounded reporting, preprint); ostmeier2024 (GREEN error notation); rao2025rexerr (cited); prucker2025 (cited) | A | No study shows that clinicians use cited keys. The figure prints them in a separate column |
| 13 | The language model writes prose only; numbers, tables, sets, card and limitations are deterministic | herasrivera2026 (cited; same split, preprint); hong2025 (AI draft reports cut reading time from 34.2 s to 19.8 s and raised sensitivity); huang2023 (generative chest radiograph reports were rated like radiologists' reports) | A | Hong and Huang concern image-to-text generation with radiologist editing, not record-to-text generation |
| 14 | Prose without lists ("no lists, no headings"); the figure numbers the sentences, but the system renderer joins them into a paragraph | bosmans2011a (itemised reporting preferred for complex examinations); kowalczyk2025 (blend of structure and narrative) | ✗ (system renderer) | A preference for numbered or bulleted impressions (about 80%) exists only as a 2009 RSNA meeting abstract, which is not peer reviewed. The numbered layout of the figure is the better-supported one |
| 15 | Length: prompt limit of 260 words, median 308 words in practice (paper), 17 sentences in the example, much of it repeating the tables | bosmans2011b ("concise reporting" is a recurring request); wallis2011 (brevity) | ✗ in part | plumb2009: detailed reports were preferred to brief ones. Restating the tables in prose is what lacks support, not the detail itself |
| 16 | Content compared with the BT-RADS follow-up template (Supplementary S24) | weinberg2018; gore2019; zhang2020; essien2024 (BT-RADS inter-rater Gwet AC2 0.83); parillo2023 (Fleiss κ 0.70); almalki2024 (prospective; readers endorsed it); persico2026 (scores predict progression-free survival); thust2018 | G / D for BT-RADS | These validate BT-RADS reading by radiologists, not a report that omits the category |

---

## (c) Gaps between what the evidence says clinicians want and what the report does

Each gap ends with a recommendation: **Change** (change the report), **Limitation** (state it as a limitation) or
**Future** (leave it to future work).

1. **No impression or bottom line.** Referrers ask for a conclusion (bosmans2011b), prefer a structured blend with a
   comment (plumb2009; kowalczyk2025), and a BT-RADS report ends with a numbered impression (weinberg2018). In PRISM
   the facts that matter come only at the end of the text or as flag chips (in the example: no enhancing change, the
   two models disagree, few cases).
   - **Change.** Add a deterministic summary block at the top of the rendered page, about three numbered lines copied
     from record fields: change in enhancing and FLAIR volume, the combined score's side and 80% set, and the tier
     and raised flags. It needs no language model, no category and no checker change, so the frozen evaluation is
     untouched.
   - If not done, **Limitation**: say the report has no impression because PRISM gives no category.
2. **No management-oriented category.** BT-RADS's value to clinicians was tied to management (weinberg2018;
   gore2019). PRISM deliberately assigns none, and the automation-bias evidence (dratsch2023; gaube2021; yu2024)
   supports that.
   - **Limitation**, framed as intended use: the report accompanies the radiologist's report, it does not replace
     it. Do not change.
3. **No clinician has read a PRISM report.** Reader studies are how AI-drafted reports are judged (tanno2025;
   hong2025; huang2023), and preference does not track performance (tang2023). The design choices in (b) marked A,
   — or ✗ are untested.
   - **Future.** Suggested design: a small reader study with PRISM's page against the template-only page against no
     page, measuring readers' accuracy and time, not only preference. The limitations block already says "No
     clinician has evaluated this report."
4. **Scores shown prominently, with no evidence that showing scores helps.** tang2023 is the closest trial: adding a
   score did not help, and text did. PRISM shows three scores, two sets per score and a median tick.
   - **Future** (the reader study above).
   - **Limitation** in one clause.
   - If the page is redesigned, a **Change**: show the combined score's set first and move the per-model scores to a
     secondary row.
5. **Missing comparison points and template elements.**
   - There is no explicit post-radiotherapy baseline (RANO 2.0 and BT-RADS compare against baseline or nadir).
   - The smallest earlier volume is given for enhancing tumour only, not for FLAIR.
   - There are no new-lesion sites and no medications (steroids, bevacizumab).
   - There is no location, diffusion or perfusion information.
   - **Limitation**: most of these are not recorded in the three cohorts, and Supplementary S24 already lists them.
   - **Change** (cheap): add FLAIR against its smallest earlier volume, if the record holds it.
6. **Repetition and length.** In the example, the disagreement appears in three places (models sentence, trust flag
   sentence, header chip) and the tier twice. Of 17 sentences, most restate a table row.
   - **Future**, because the prompt is frozen for the evaluated reports. A later prompt could drop the sentences
     that restate a table, or the deterministic page could stop repeating flag text that the model already wrote.
7. **The system's own page is not the figure's page.** `sections_v3.render_html` (v3.1) still titles a section
   "The two pathways" (STYLE §2 forbids "pathway"). It puts prose before tables, joins the sentences into a
   paragraph and has no score tracks, tier scale or flag chips. There is no v3.2 renderer.
   - **Change**: port the Figure 5a layout into the renderer, as already proposed in REPORT_FORMAT_RESEARCH.md §4,
     with no change to the language model or the checker.
   - If not done, describe Figure 5a in the paper as a layout of the report's content, not as the page the system
     renders.
8. **No neuro-oncology-specific evidence on AI report content.** The searches found only:
   - hoebel2024, on how experts perceive segmentation;
   - jin2024, where AI predictions helped in glioma grading but explanations added nothing;
   - vollmuth2023, where less experienced readers found AI volumetry more helpful.

   Nothing found surveys what neuro-oncology clinicians want an AI follow-up report to contain.
   - **Limitation** (one sentence), and **Future**.

---

## (d) Verified BibTeX entries (new sources only)

Style follows `paper/refs.bib`: author+year keys, initials, "and others" for long author lists, titles in double
braces. Every DOI resolved on Crossref on 2026-11-20 with the authors, year, journal, volume and pages shown.
Existing keys (weinberg2018, gore2019, zhang2020, thust2018, wen2023, mitchell2019, herasrivera2026, jabal2026,
rao2025rexerr, prucker2025) are not repeated.

```bibtex
% --- What referring clinicians want from radiology reports
@article{bosmans2011a,
  author  = {Bosmans, J. M. L. and Weyler, J. J. and De Schepper, A. M. and Parizel, P. M.},
  year    = {2011},
  title   = {{The radiology report as seen by radiologists and referring clinicians: Results of the COVER and ROVER surveys}},
  journal = {Radiology},
  volume  = {259},
  number  = {1},
  pages   = {184--195},
  doi     = {10.1148/radiol.10101045}
}

@article{bosmans2011b,
  author  = {Bosmans, J. M. L. and Peremans, L. and De Schepper, A. M. and Duyck, P. O. and Parizel, P. M.},
  year    = {2011},
  title   = {{How do referring clinicians want radiologists to report? Suggestions from the COVER survey}},
  journal = {Insights into Imaging},
  volume  = {2},
  number  = {5},
  pages   = {577--584},
  doi     = {10.1007/s13244-011-0118-z}
}

@article{plumb2009,
  author  = {Plumb, A. A. O. and Grieve, F. M. and Khan, S. H.},
  year    = {2009},
  title   = {{Survey of hospital clinicians' preferences regarding the format of radiology reports}},
  journal = {Clinical Radiology},
  volume  = {64},
  number  = {4},
  pages   = {386--394},
  doi     = {10.1016/j.crad.2008.11.009}
}

@article{kowalczyk2025,
  author  = {Kowalczyk, B. and Ramis, P. and Hillman, A. and others},
  year    = {2025},
  title   = {{Radiology reporting preferences: What do referring clinicians want?}},
  journal = {Academic Radiology},
  volume  = {32},
  number  = {1},
  pages   = {439--449},
  doi     = {10.1016/j.acra.2024.09.006}
}

@article{clinger1988,
  author  = {Clinger, N. J. and Hunter, T. B. and Hillman, B. J.},
  year    = {1988},
  title   = {{Radiology reporting: Attitudes of referring physicians}},
  journal = {Radiology},
  volume  = {169},
  number  = {3},
  pages   = {825--826},
  doi     = {10.1148/radiology.169.3.3187005}
}

@article{ignacio2018,
  author  = {Ign{\'a}cio, F. C. G. R. and de Souza, L. R. M. F. and D'Ippolito, G. and Garcia, M. M.},
  year    = {2018},
  title   = {{Radiology report: What is the opinion of the referring physician?}},
  journal = {Radiologia Brasileira},
  volume  = {51},
  number  = {5},
  pages   = {308--312},
  doi     = {10.1590/0100-3984.2017.0115}
}

@article{wallis2011,
  author  = {Wallis, A. and McCoubrie, P.},
  year    = {2011},
  title   = {{The radiology report --- Are we getting the message across?}},
  journal = {Clinical Radiology},
  volume  = {66},
  number  = {11},
  pages   = {1015--1022},
  doi     = {10.1016/j.crad.2011.05.013}
}

@article{kahn2009,
  author  = {Kahn, C. E. and Langlotz, C. P. and Burnside, E. S. and others},
  year    = {2009},
  title   = {{Toward best practices in radiology reporting}},
  journal = {Radiology},
  volume  = {252},
  number  = {3},
  pages   = {852--856},
  doi     = {10.1148/radiol.2523081992}
}

% --- Certainty and uncertainty language
@article{panicek2016,
  author  = {Panicek, D. M. and Hricak, H.},
  year    = {2016},
  title   = {{How sure are you, doctor? A standardized lexicon to describe the radiologist's level of certainty}},
  journal = {American Journal of Roentgenology},
  volume  = {207},
  number  = {1},
  pages   = {2--3},
  doi     = {10.2214/AJR.15.15895}
}

@article{shinagare2019,
  author  = {Shinagare, A. B. and Lacson, R. and Boland, G. W. and others},
  year    = {2019},
  title   = {{Radiologist preferences, agreement, and variability in phrases used to convey diagnostic certainty in radiology reports}},
  journal = {Journal of the American College of Radiology},
  volume  = {16},
  number  = {4},
  pages   = {458--464},
  doi     = {10.1016/j.jacr.2018.09.052}
}

@article{bruno2017,
  author  = {Bruno, M. A. and Petscavage-Thomas, J. and Abujudeh, H. H.},
  year    = {2017},
  title   = {{Communicating uncertainty in the radiology report}},
  journal = {American Journal of Roentgenology},
  volume  = {209},
  number  = {5},
  pages   = {1006--1008},
  doi     = {10.2214/AJR.17.18271}
}

@article{vanderbles2019,
  author  = {van der Bles, A. M. and van der Linden, S. and Freeman, A. L. J. and others},
  year    = {2019},
  title   = {{Communicating uncertainty about facts, numbers and science}},
  journal = {Royal Society Open Science},
  volume  = {6},
  number  = {5},
  pages   = {181870},
  doi     = {10.1098/rsos.181870}
}

@article{spiegelhalter2017,
  author  = {Spiegelhalter, D.},
  year    = {2017},
  title   = {{Risk and uncertainty communication}},
  journal = {Annual Review of Statistics and Its Application},
  volume  = {4},
  pages   = {31--60},
  doi     = {10.1146/annurev-statistics-010814-020148}
}

% --- Structured reporting and its evidence
@article{schwartz2011,
  author  = {Schwartz, L. H. and Panicek, D. M. and Berk, A. R. and Li, Y. and Hricak, H.},
  year    = {2011},
  title   = {{Improving communication of diagnostic radiology findings through structured reporting}},
  journal = {Radiology},
  volume  = {260},
  number  = {1},
  pages   = {174--181},
  doi     = {10.1148/radiol.11101913}
}

@article{sistrom2005,
  author  = {Sistrom, C. L. and Honeyman-Buck, J.},
  year    = {2005},
  title   = {{Free text versus structured format: Information transfer efficiency of radiology reports}},
  journal = {American Journal of Roentgenology},
  volume  = {185},
  number  = {3},
  pages   = {804--812},
  doi     = {10.2214/ajr.185.3.01850804}
}

@article{johnson2009,
  author  = {Johnson, A. J. and Chen, M. Y. M. and Swan, J. S. and Applegate, K. E. and Littenberg, B.},
  year    = {2009},
  title   = {{Cohort study of structured reporting compared with conventional dictation}},
  journal = {Radiology},
  volume  = {253},
  number  = {1},
  pages   = {74--80},
  doi     = {10.1148/radiol.2531090138}
}

@article{bink2018,
  author  = {Bink, A. and Benner, J. and Reinhardt, J. and others},
  year    = {2018},
  title   = {{Structured reporting in neuroradiology: Intracranial tumors}},
  journal = {Frontiers in Neurology},
  volume  = {9},
  pages   = {32},
  doi     = {10.3389/fneur.2018.00032}
}

@article{esr2018,
  author  = {{European Society of Radiology (ESR)}},
  year    = {2018},
  title   = {{ESR paper on structured reporting in radiology}},
  journal = {Insights into Imaging},
  volume  = {9},
  number  = {1},
  pages   = {1--7},
  doi     = {10.1007/s13244-017-0588-8}
}

@article{dossantos2023,
  author  = {dos Santos, D. P. and Kotter, E. and Mildenberger, P. and Mart{\'i}-Bonmat{\'i}, L. and {European Society of Radiology (ESR)}},
  year    = {2023},
  title   = {{ESR paper on structured reporting in radiology --- update 2023}},
  journal = {Insights into Imaging},
  volume  = {14},
  number  = {1},
  pages   = {199},
  doi     = {10.1186/s13244-023-01560-0}
}

@article{gunderman2014,
  author  = {Gunderman, R. B. and McNeive, L. R.},
  year    = {2014},
  title   = {{Is structured reporting the answer?}},
  journal = {Radiology},
  volume  = {273},
  number  = {1},
  pages   = {7--9},
  doi     = {10.1148/radiol.14132795}
}

% --- BT-RADS validation
@article{essien2024,
  author  = {Essien, M. and Cooper, M. E. and Gore, A. and others},
  year    = {2024},
  title   = {{Interrater agreement of BT-RADS for evaluation of follow-up MRI in patients with treated primary brain tumor}},
  journal = {American Journal of Neuroradiology},
  volume  = {45},
  number  = {9},
  pages   = {1308--1315},
  doi     = {10.3174/ajnr.A8322}
}

@article{parillo2023,
  author  = {Parillo, M. and Mallio, C. A. and Pileri, M. and others},
  year    = {2023},
  title   = {{Interrater reliability of Brain Tumor Reporting and Data System (BT-RADS) in the follow up of adult primary brain tumors: A single institution experience in Italy}},
  journal = {Quantitative Imaging in Medicine and Surgery},
  volume  = {13},
  number  = {11},
  pages   = {7423--7431},
  doi     = {10.21037/qims-22-850}
}

@article{almalki2024,
  author  = {Almalki, Y. E. and Basha, M. A. A. and Metwally, M. I. and others},
  year    = {2024},
  title   = {{Validating Brain Tumor Reporting and Data System (BT-RADS) as a diagnostic tool for glioma follow-up after surgery}},
  journal = {Biomedicines},
  volume  = {12},
  number  = {4},
  pages   = {887},
  doi     = {10.3390/biomedicines12040887}
}

@article{persico2026,
  author  = {Persico, M. and Essien, M. and Assaye, T. and Donovan, L. E. and Zhong, J. and Weinberg, B. D.},
  year    = {2026},
  title   = {{Predictive value of brain tumor reporting and data system scores for functional outcomes and progression-free survival in newly diagnosed glioblastoma}},
  journal = {Neuro-Oncology Advances},
  volume  = {8},
  number  = {1},
  pages   = {vdag094},
  doi     = {10.1093/noajnl/vdag094},
  note    = {CHECK: end of title truncated in the Crossref and PubMed listings}
}

% --- Volumetry in neuro-oncology follow-up
@article{kickingereder2019,
  author  = {Kickingereder, P. and Isensee, F. and Tursunova, I. and others},
  year    = {2019},
  title   = {{Automated quantitative tumour response assessment of MRI in neuro-oncology with artificial neural networks: A multicentre, retrospective study}},
  journal = {The Lancet Oncology},
  volume  = {20},
  number  = {5},
  pages   = {728--740},
  doi     = {10.1016/S1470-2045(19)30098-1}
}

@article{chang2019,
  author  = {Chang, K. and Beers, A. L. and Bai, H. X. and others},
  year    = {2019},
  title   = {{Automatic assessment of glioma burden: A deep learning algorithm for fully automated volumetric and bidimensional measurement}},
  journal = {Neuro-Oncology},
  volume  = {21},
  number  = {11},
  pages   = {1412--1422},
  doi     = {10.1093/neuonc/noz106}
}

@article{vollmuth2023,
  author  = {Vollmuth, P. and Foltyn, M. and Huang, R. Y. and others},
  year    = {2023},
  title   = {{Artificial intelligence (AI)-based decision support improves reproducibility of tumor response assessment in neuro-oncology: An international multi-reader study}},
  journal = {Neuro-Oncology},
  volume  = {25},
  number  = {3},
  pages   = {533--543},
  doi     = {10.1093/neuonc/noac189}
}

@article{abayazeed2023,
  author  = {Abayazeed, A. H. and Abbassy, A. and M{\"u}eller, M. and others},
  year    = {2023},
  title   = {{NS-HGlio: A generalizable and repeatable HGG segmentation and volumetric measurement AI algorithm for the longitudinal MRI assessment to inform RANO in trials and clinics}},
  journal = {Neuro-Oncology Advances},
  volume  = {5},
  number  = {1},
  pages   = {vdac184},
  doi     = {10.1093/noajnl/vdac184}
}

@article{hoebel2024,
  author  = {Hoebel, K. V. and Bridge, C. P. and Ahmed, S. and others},
  year    = {2024},
  title   = {{Expert-centered evaluation of deep learning algorithms for brain tumor segmentation}},
  journal = {Radiology: Artificial Intelligence},
  volume  = {6},
  number  = {1},
  pages   = {e220231},
  doi     = {10.1148/ryai.220231}
}

@article{yang2023,
  author  = {Yang, M. H. and Kim, E. H. and Choi, E. S. and Ko, H.},
  year    = {2023},
  title   = {{Comparison of normative percentiles of brain volume obtained from NeuroQuant vs. DeepBrain in the Korean population: Correlation with cranial shape}},
  journal = {Journal of the Korean Society of Radiology},
  volume  = {84},
  number  = {5},
  pages   = {1080},
  doi     = {10.3348/jksr.2023.0006},
  note    = {CHECK: page range; Crossref gives first page only}
}

% --- How AI output is shown to clinicians
@article{sendak2020,
  author  = {Sendak, M. P. and Gao, M. and Brajer, N. and Balu, S.},
  year    = {2020},
  title   = {{Presenting machine learning model information to clinical end users with model facts labels}},
  journal = {npj Digital Medicine},
  volume  = {3},
  pages   = {41},
  doi     = {10.1038/s41746-020-0253-3}
}

@article{tang2023,
  author  = {Tang, J. S. N. and Lai, J. K. C. and Bui, J. and others},
  year    = {2023},
  title   = {{Impact of different artificial intelligence user interfaces on lung nodule and mass detection on chest radiographs}},
  journal = {Radiology: Artificial Intelligence},
  volume  = {5},
  number  = {3},
  pages   = {e220079},
  doi     = {10.1148/ryai.220079}
}

@article{gaube2021,
  author  = {Gaube, S. and Suresh, H. and Raue, M. and others},
  year    = {2021},
  title   = {{Do as AI say: Susceptibility in deployment of clinical decision-aids}},
  journal = {npj Digital Medicine},
  volume  = {4},
  pages   = {31},
  doi     = {10.1038/s41746-021-00385-9}
}

@article{gaube2023,
  author  = {Gaube, S. and Suresh, H. and Raue, M. and others},
  year    = {2023},
  title   = {{Non-task expert physicians benefit from correct explainable AI advice when reviewing X-rays}},
  journal = {Scientific Reports},
  volume  = {13},
  pages   = {1383},
  doi     = {10.1038/s41598-023-28633-w}
}

@article{dratsch2023,
  author  = {Dratsch, T. and Chen, X. and Rezazade Mehrizi, M. and others},
  year    = {2023},
  title   = {{Automation bias in mammography: The impact of artificial intelligence BI-RADS suggestions on reader performance}},
  journal = {Radiology},
  volume  = {307},
  number  = {4},
  pages   = {e222176},
  doi     = {10.1148/radiol.222176}
}

@article{goddard2012,
  author  = {Goddard, K. and Roudsari, A. and Wyatt, J. C.},
  year    = {2012},
  title   = {{Automation bias: A systematic review of frequency, effect mediators, and mitigators}},
  journal = {Journal of the American Medical Informatics Association},
  volume  = {19},
  number  = {1},
  pages   = {121--127},
  doi     = {10.1136/amiajnl-2011-000089}
}

@article{yu2024,
  author  = {Yu, F. and Moehring, A. and Banerjee, O. and Salz, T. and Agarwal, N. and Rajpurkar, P.},
  year    = {2024},
  title   = {{Heterogeneity and predictors of the effects of AI assistance on radiologists}},
  journal = {Nature Medicine},
  volume  = {30},
  number  = {3},
  pages   = {837--849},
  doi     = {10.1038/s41591-024-02850-w}
}

@article{jin2024,
  author  = {Jin, W. and Fatehi, M. and Guo, R. and Hamarneh, G.},
  year    = {2024},
  title   = {{Evaluating the clinical utility of artificial intelligence assistance and its explanation on the glioma grading task}},
  journal = {Artificial Intelligence in Medicine},
  volume  = {148},
  pages   = {102751},
  doi     = {10.1016/j.artmed.2023.102751}
}

% --- Showing uncertainty and prediction sets to people
@article{kompa2021,
  author  = {Kompa, B. and Snoek, J. and Beam, A. L.},
  year    = {2021},
  title   = {{Second opinion needed: Communicating uncertainty in medical machine learning}},
  journal = {npj Digital Medicine},
  volume  = {4},
  pages   = {4},
  doi     = {10.1038/s41746-020-00367-3}
}

@inproceedings{cresswell2024,
  author    = {Cresswell, J. C. and Sui, Y. and Kumar, B. and Vouitsis, N.},
  year      = {2024},
  title     = {{Conformal prediction sets improve human decision making}},
  booktitle = {Proceedings of the 41st International Conference on Machine Learning},
  series    = {Proceedings of Machine Learning Research},
  volume    = {235},
  pages     = {9439--9457},
  url       = {https://proceedings.mlr.press/v235/cresswell24a.html},
  note      = {No DOI; checked on the PMLR proceedings page}
}

@inproceedings{zhang2024chi,
  author    = {Zhang, D. and Chatzimparmpas, A. and Kamali, N. and Hullman, J.},
  year      = {2024},
  title     = {{Evaluating the utility of conformal prediction sets for AI-advised image labeling}},
  booktitle = {Proceedings of the CHI Conference on Human Factors in Computing Systems (CHI '24)},
  pages     = {1--19},
  publisher = {ACM},
  doi       = {10.1145/3613904.3642446}
}

% --- Generated radiology reports and their evaluation
@article{tanno2025,
  author  = {Tanno, R. and Barrett, D. G. T. and Sellergren, A. and others},
  year    = {2025},
  title   = {{Collaboration between clinicians and vision--language models in radiology report generation}},
  journal = {Nature Medicine},
  volume  = {31},
  number  = {2},
  pages   = {599--608},
  doi     = {10.1038/s41591-024-03302-1}
}

@article{hong2025,
  author  = {Hong, E. K. and Roh, B. and Park, B. and others},
  year    = {2025},
  title   = {{Value of using a generative AI model in chest radiography reporting: A reader study}},
  journal = {Radiology},
  volume  = {314},
  number  = {3},
  pages   = {e241646},
  doi     = {10.1148/radiol.241646}
}

@article{huang2023,
  author  = {Huang, J. and Neill, L. and Wittbrodt, M. and others},
  year    = {2023},
  title   = {{Generative artificial intelligence for chest radiograph interpretation in the emergency department}},
  journal = {JAMA Network Open},
  volume  = {6},
  number  = {10},
  pages   = {e2336100},
  doi     = {10.1001/jamanetworkopen.2023.36100}
}

@inproceedings{ostmeier2024,
  author    = {Ostmeier, S. and Xu, J. and Chen, Z. and others},
  year      = {2024},
  title     = {{GREEN: Generative radiology report evaluation and error notation}},
  booktitle = {Findings of the Association for Computational Linguistics: EMNLP 2024},
  pages     = {374--390},
  doi       = {10.18653/v1/2024.findings-emnlp.21}
}

@misc{bannur2024,
  author       = {Bannur, S. and Bouzid, K. and Castro, D. C. and others},
  year         = {2024},
  title        = {{MAIRA-2: Grounded radiology report generation}},
  howpublished = {Preprint, {arXiv}:2406.04449},
  doi          = {10.48550/arXiv.2406.04449},
  url          = {https://doi.org/10.48550/arXiv.2406.04449}
}
```

---

## 6. Dropped or not verified

Dropped:

- auntminnie.com and radiologybusiness.com items (trade press). They are replaced by kowalczyk2025, plumb2009,
  bosmans2011a/b and gore2019.
- "About 80% want a numbered or bulleted impression; 607 staff physicians" (Hershey, RSNA 2009). This is a meeting
  abstract only (archive.rsna.org/2009/8004098.html). It is not peer reviewed, so it gets no bib entry.
- `PMC10585089`, cited in REPORT_FORMAT_RESEARCH.md as the source for the icobrain and NeuroQuant report layout.
  It is in fact a Korean study of NeuroQuant normative percentiles (yang2023 above), not a report-layout source.
  The claimed layout (header, overlay row, volume table with percentiles, longitudinal percent change) is not
  verified from a peer-reviewed source. Vendor sample reports would be primary documents but were not retrieved.

Not verified:

- **ACR Practice Parameter for Communication of Diagnostic Imaging Findings** (the ACR portal lists a 2025
  revision, Resolution 9). The PDF was retrieved, but its text could not be extracted here, and the summary a web
  tool gave of it was wrong (it described BI-RADS). Read it before citing anything specific from it.
- **RSNA RadReport brain-tumour follow-up template.** No template page was located. BT-RADS's own templates
  (btrads.com, read 2026-11-03) remain the primary template source.
- **FDA 510(k) numbers** in REPORT_DESIGN_SOURCES (NS-HGlio K221738, NeuroQuant brain tumour K241098, Brainlab
  K250440). Not checked. abayazeed2023 is the peer-reviewed NS-HGlio source.
- **Lee et al.** (referring-clinician survey) could not be identified. gunderman2014 is a commentary, kept only as
  a counterpoint on structured reporting.
- **IHE AI Results (AIR) profile.** Exists as an IHE Radiology Technical Framework Supplement, Rev. 1.2, Trial
  Implementation (ihe.net). The document itself was not read. It is a standard for display and storage, not evidence
  about clinicians.

---

## 7. Paper text the evidence does not support as written (for the author; nothing edited)

1. **main.tex §2.3:** "The report follows the content of the BT-RADS follow-up template \citep{weinberg2018}
   without its category or advice".
   - Supplementary Table S6 itself lists the template elements the report lacks: medications, new FLAIR or
     enhancing sites, location, diffusion, perfusion, mass effect, clinical status and the impression.
   - The template is "management-based" by title.
   - A wording the evidence supports: "The report carries the clinical history, comparison and change elements of
     the BT-RADS follow-up template \citep{weinberg2018}, which referring clinicians rated more consistent and less
     ambiguous than free prose \citep{gore2019}, without its category or advice."
2. **Figure 5 caption:** "The page follows the order of the BT-RADS follow-up template".
   - BT-RADS goes from indication and history, through comparison and findings, to the impression. The figure's
     scores, sets and card take the impression's place, and the language model's text then restates them, which
     BT-RADS does not.
   - The page is drawn by `scripts/fig5_report.py`. The system's renderer (`sections_v3.render_html`) has another
     order and section titles, and there is none for v3.2.
   - "The report PRISM writes" is accurate for the sentences and the values, but not for the layout. Either port the
     layout to the renderer (gap 7) or say the panel lays out the report's content.
3. **Supplementary S24, "Reading":** "Its phase of care uses the template's own boundary of 12 weeks".
   - REPORT_DESIGN_SOURCES (2026-11-03) records the shared 12-week boundary as a coincidence, not a design choice.
   - "Phase of care" is a retired term (STYLE §2: "time window", "time after radiotherapy").
   - Table S6 also says "the evidence and confidence above", but the report forbids "confidence".
4. **main.tex Introduction:** "A report is useful only if each statement in it can be traced to the record and
   checked."
   - No study found shows that traceability makes a report useful to clinicians. tanno2025 and prucker2025 show that
     errors are common, which motivates checking, not usefulness.
   - The evidence supports "A report can be trusted only as far as its statements can be checked against the
     record".
5. **main.tex and Supplementary S24**, the claims that BT-RADS reports were "rated more consistent" (gore2019) and
   "recorded more treatment history" (zhang2020). These match the verified abstracts, with no change needed. The
   numbers in thust2018 (60% free text, 27% RANO, 23% template) also match.
