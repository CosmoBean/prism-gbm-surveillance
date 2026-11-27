# Locked text

Wording the author or the PI has approved. It is not changed without the author's explicit approval, not even for
polish or a tone pass. If a later result makes a locked passage wrong, flag it to the author and propose the smallest
edit. `paper/build.sh` runs `scripts/check_locked.py`, which fails the build when a line of the list below is no
longer in `paper/main.tex` (whitespace and line breaks are ignored). To change locked wording with approval, change
it here and in the paper in the same commit.

## Abstract (approved 2026-11-26; numbers updated to PRISM's segmenter 2026-11-27)

```locked
Models for glioma follow-up MRI report high accuracy, but a single AUC cannot show what drives their predictions. We built a new framework, PRISM (Progression Reading with Independent Scores and Measurements), running on one local computer. It segments each scan with the winning BraTS 2024 post-treatment model, scores it from image measurements, clinical history and both with three logistic regressions and conformal sets, and has a local language model write a checked report of what each score rests on. On MU-Glioma-Post, the combined model reached an AUC of 0.82 in repeated cross validation, and up to 1.00 (mean 0.84) on single held-out splits, the design of earlier studies. Unlike most earlier models, PRISM was tested without retraining at two other centres, reaching 0.79 at LUMIERE and 0.81 at UCSF-ALPTDG, against a pooled AUC of 0.81 for earlier models tested at another centre.
```

## Sentences and phrases

Source of each item: the PI's marked copy of 2026-11-23 (commit 28e245b), the evaluation wording kept in 12f83d1, and
the author's approvals of 2026-11-26 and 2026-11-27.

```locked
\item A new local system is developed
\item PRISM separates imaging and clinical-history scores, each reported with its uncertainty.
\item PRISM provides an evaluation of what each score adds to what the clinician already knows.
\item External validation is performed without retraining.
\item Report is generated with deterministic verification.
The remainder of this paper is organized as follows.
We used three public cohorts of patients followed with MRI after treatment for glioma.
PRISM is developed on
We present PRISM (Progression Reading with Independent Scores and Measurements), a new system for glioma follow-up MRI that runs on one local computer.
PRISM works from conventional MRI and the clinical record, both part of every
\caption{\textbf{The workflow of PRISM.}
averaged over the five repeats, because a single split of a small cohort gives an estimate with a wide error
In a meta-analysis of 31 studies, models tested at another institution reached a pooled AUC of 0.81, against 0.91 at the institution that developed them \citep{zhang2026meta}.
For comparison with studies evaluated on one held-out split \citep{christodoulou2026}, the combined model was also fitted and scored on 100 random held-out sets of 18 of the 92 grade 4 patients, drawn as in an earlier re-implementation of that study (exploratory).
On 100 sets drawn the same way, PRISM's combined model reached up to 1.00, and 0.84 on average, with 95\% of sets between 0.68 and 0.96 (exploratory).
At MU-Glioma-Post, the combined model reached an AUC of 0.82 (0.76--0.89) in repeated cross validation, and up to 1.00 (mean 0.84) on single held-out splits of 18 patients, the design of earlier studies on this cohort \citep{christodoulou2026}.
The combined model reached 0.79 (0.72--0.86) at LUMIERE and 0.81 (0.70--0.90) at UCSF-ALPTDG, against a pooled AUC of 0.81 for earlier models tested at another institution \citep{zhang2026meta}.
All reports for held-out scans passed the checker, and both programs were tested with 24 types of planted error.
All evaluation reports passed the checker (Figure~\ref{fig:5} shows one).
PRISM's combined model ranked scans with an AUC of 0.82 at MU and held that level without retraining at both external centres, with 0.79 at LUMIERE and 0.81 at UCSF-ALPTDG. Splitting each score into its inputs showed what this ranking rests on: the treatment course and the image measurements each made up about two fifths of the combined score. The results held with PRISM's own segmenter, the conformal sets kept their 80\% coverage in every cohort, and every report passed the checker.
\subsection{Treatment history and images carry the combined score in near-equal parts}
\subsection{The combined score's sets held their coverage}
```
