# Report

`main.tex` — technical report: does post-treatment MRI add to clinical information for 120-day progression prediction?
Numbers come from `docs/results/` (C2, C3, EXTERNAL_LUMIERE, IMAGING_VS_NONIMAGING); update them there first.

Build (any LaTeX distribution; no BibTeX step needed):

```bash
pdflatex main.tex && pdflatex main.tex      # or: tectonic main.tex
```

`original_prism_report/` — LaTeX remake of `docs/original_prism_report.pdf` (IEEE conference format). Text is copied
word for word and the five figures were extracted losslessly from the original PDF; only the typesetting changed.
Build: `cd original_prism_report && pdflatex original_prism_report.tex` (twice).
