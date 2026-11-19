# Review folder

Everything waiting for the author's review, in one place. Open in a markdown preview (VS Code: Ctrl+Shift+V).

| File | What it is | Status |
|---|---|---|
| [FIGURE_REVIEW.md](FIGURE_REVIEW.md) | Every manuscript figure in reading order, with notes | Figures in the paper (2026-11-19) |
| [REPORT_FORMAT_RESEARCH.md](REPORT_FORMAT_RESEARCH.md) | How good radiology and clinical-AI reports are laid out; what the old Figure 5a did oddly; the redesign | Redesign built (`scripts/fig5_report.py`) |
| [WRITING_NOTES_TAK_COMPARISON.md](WRITING_NOTES_TAK_COMPARISON.md) | Our prose against Tak et al. 2025 (NEJM AI), section by section, with rewrites | Notes only; nothing applied |
| [WRITING_NOTES_BEST_PRACTICE.md](WRITING_NOTES_BEST_PRACTICE.md) | Our prose against journal guidance (NEJM AI, Lancet DH, Nat Med, Radiology: AI), Gopen & Swan, TRIPOD+AI, CLAIM | Notes only; nothing applied |

Where both writing reviews agree (start here):
1. The locked abstract attaches "AUC 0.80" so that it reads as the combined model's; it is the baseline's. The
   abstract also never says "progression". Locked text: the author decides.
2. The Section 4.5 heading ("after one revision of the prompt") carries development history.
3. The Figure 2 (performance) caption says "development centre".
4. Results headings and caption titles are labels rather than findings.
5. Protocol detail (planned or exploratory, which masks, which bootstrap) sits inside findings sentences.
