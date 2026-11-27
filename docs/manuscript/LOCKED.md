# Locked text

Wording the author or the PI has approved. It is not changed without the author's explicit approval, not even for
polish or a tone pass. If a later result makes a locked passage wrong, flag it to the author and propose the smallest
edit. `paper/build.sh` runs `scripts/check_locked.py`, which fails the build when a line of the list below is no
longer in `paper/main.tex` (whitespace and line breaks are ignored). To change locked wording with approval, change
it here and in the paper in the same commit.

## Abstract (approved 2026-11-26; numbers updated to PRISM's segmenter 2026-11-27)

```locked
Models for glioma follow-up MRI report high accuracy, but a single AUC cannot show what drives their predictions. We built a new framework, PRISM (Progression Reading with Independent Scores and Measurements), running on one local computer. It segments each scan with the winning BraTS 2024 post-treatment model, scores it from image measurements, clinical history and both with three logistic regressions and conformal sets, and uses a local language model to write a checked report of what each score rests on. On MU-Glioma-Post, the combined model reached an AUC of 0.82 in repeated cross validation, and 0.85 on the held-out set of an earlier study on this cohort, against 0.80 reported. Unlike most earlier models, PRISM was tested without retraining at two other centres, reaching 0.79 at LUMIERE and 0.81 at UCSF-ALPTDG, against a pooled AUC of 0.81 for earlier models tested at another centre.
```

## Sentences and phrases

Source of each item: the PI's marked copy of 2026-11-23 (commit 28e245b), the evaluation wording kept in 12f83d1, and
the author's approvals of 2026-11-26 and 2026-11-27.

```locked
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
In a meta-analysis of 31 studies separating true progression from pseudoprogression in glioblastoma, seven external test cohorts gave a pooled AUC of 0.81, against 0.91 for internal test cohorts \citep{zhang2026meta}.
The published radiomics study on MU-Glioma-Post scored its model on one held-out set of 30 patients \citep{christodoulou2026}. We recreated that set from the study's published code, fitted PRISM's models and the radiomics model (with its authors' code) on the other patients, and scored them on the set's grade 4 patients. The AUC on one small held-out set depends strongly on which patients are drawn, so the combined model was also fitted and scored on 100 random held-out sets of 18 of the 92 grade 4 patients (20\%), drawn as in our earlier re-implementation of that study. To compare with models developed at the centre where they are tested, every model was also trained within UCSF-ALPTDG by five repeats of fivefold cross validation grouped by patient, and fine-tuned by refitting on all MU training scans together with the training folds of UCSF-ALPTDG. These analyses are exploratory.
Table~\ref{tab:lit} sets PRISM beside earlier models (exploratory). On the held-out set of the published radiomics study \citep{christodoulou2026}, PRISM's combined model reached 0.85, above the 0.80 that study reported and the 0.59 of its model rerun on our label. This set held 29 evaluation scans of 13 grade 4 patients, and single sets this small vary widely: over 100 random held-out sets, PRISM's combined model averaged 0.84, and our earlier re-implementation of the radiomics model 0.63.
Without retraining, the combined model matched earlier models tested at another institution, with 0.79 at LUMIERE and 0.81 at UCSF-ALPTDG against a pooled 0.81 for separating true progression from pseudoprogression \citep{zhang2026meta}. Fine-tuning on UCSF-ALPTDG scans changed it little (0.82). Trained at UCSF-ALPTDG itself, it reached 0.87, close to the pooled 0.91 of earlier models tested at the institution that developed them.
At MU-Glioma-Post, the combined model reached an AUC of 0.82 in repeated cross validation. A radiomics model published on this cohort reported 0.80 on one held-out set of 30 patients \citep{christodoulou2026}. On that same held-out set, PRISM reached 0.85, and the published model, rerun with its authors' code on our label, 0.59. Because one small held-out set gives an unstable AUC, we also repeated this design on 100 random held-out sets, where PRISM averaged 0.84 and reached up to 1.00.
The combined model reached 0.79 at LUMIERE and 0.81 at UCSF-ALPTDG, the same as the pooled AUC of 0.81 for earlier models separating true progression from pseudoprogression at another institution \citep{zhang2026meta}. Trained at UCSF-ALPTDG itself, it reached 0.87, close to the pooled 0.91 of earlier models tested where they were developed.
All reports for held-out scans passed the checker, and both programs were tested with 24 types of planted error.
All evaluation reports passed the checker (Figure~\ref{fig:5} shows one).
PRISM's combined model ranked scans with an AUC of 0.82 at MU and held that level without retraining at both external centres, with 0.79 at LUMIERE and 0.81 at UCSF-ALPTDG. Splitting each score into its inputs showed what this ranking rests on: the treatment course and the image measurements each made up about two fifths of the combined score. The results held with PRISM's own segmenter, the conformal sets kept their 80\% coverage in every cohort, and every report passed the checker.
\subsection{Treatment history and images carry the combined score in near-equal parts}
\subsection{The combined score's sets held their coverage}
```

## PI's Figure 1 requests (marked copy 2026-11-23, items 22, 25, 28, 29; restored 2026-11-27; revised by her marked copy of
## 2026-11-27: Figure 1 split into Figures 1, 3, 4 and 5, overview without figure references, 'writing', 'system PRISM is', 'b,a')

```locked
PRISM reads each follow-up MRI scan of a patient treated for glioma and returns three scores of progression with a written report. Section~\ref{sec:2.1} describes the cohorts and the label. Section~\ref{sec:2.2} describes PRISM's segmenter and its six stages. Section~\ref{sec:2.3} describes how PRISM was developed on MU-Glioma-Post and tested without retraining on LUMIERE and UCSF-ALPTDG.
The task was to distinguish the scan at which progression was documented from scans without progression (Figure~\ref{fig:patient}).
On MU, every model was evaluated by five repeats of fivefold cross validation grouped by patient (Figure~\ref{fig:evaluation}).
\paragraph*{Segmentation (Stage 1).}
\paragraph*{Measurements (Stage 2).}
\paragraph*{Models (Stage 3).}
\paragraph*{Evidence (Stage 4).}
\paragraph*{Record (Stage 5).}
\paragraph*{Report and checks (Stage 6).}
\item A new local system PRISM is developed, which segments
Yongjie Jessica Zhang\textsuperscript{b,a}
```
