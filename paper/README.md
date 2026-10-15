# Manuscript (LaTeX) — source of truth

From 2026-10-15 the manuscript lives here. `docs/manuscript/DRAFT.md` and `docs/manuscript/SUPPLEMENT.md`
are **frozen snapshots** of the text this project was converted from; do not edit them. Make all text, number and
reference changes in this directory.

| File | Content |
|---|---|
| `main.tex` | Main text: title block, abstract, key points, sections 1–4, declarations, Tables 1–3, Figures 1–5 |
| `supplement.tex` | Supplementary Material S1–S18, Supplementary Tables S1a–S25, supplementary figure list |
| `macros.tex` | Shared preamble (layout, line numbers, tables, `\code`, `\flag`/`\todo` placeholders, natbib) |
| `refs.bib` | References (one entry per item of the draft's reference list; `note = {CHECK}` = unverified) |
| `plainnat-amp.bst` | `plainnat` with "&" in two-author in-text citations (one-line change, see header) |
| `build.sh` | Builds both PDFs with tectonic |
| `SOURCE_MAP.md` | Where every number in the draft came from (moved verbatim out of DRAFT.md; not submitted) |

## Build

```bash
./paper/build.sh            # or: cd paper && ./build.sh
```

Requires `tectonic` (default `$HOME/.local/opt/texenv/bin/tectonic`; override with `TECTONIC=/path/to/tectonic`).
The script compiles `main.tex` and `supplement.tex` (XeTeX + BibTeX, intermediates in `paper/build/`), copies
`main.pdf` and `supplement.pdf` into `paper/`, prints page counts, and exits non-zero on LaTeX/BibTeX errors,
undefined references or citations, or overfull boxes wider than 10 pt. The only expected BibTeX warning is the
missing year of the CFB-GBM dataset entry.

Figures are not copied: `macros.tex` sets `\graphicspath{{../docs/manuscript/figures/}}`, and the PDF versions are
used where they exist (Figure 5 is PNG only).

## Conventions

- Red text marks open items: `\flag{[CHECK ...]}` for unverified citations, `\todo{PENDING ...}` /
  `\flag{[PENDING ...]}` for author decisions. Search for `CHECK` and `PENDING` before submission.
- Numbers are typed exactly as reported; minus signs are `$-$`, Δ/±/×/≥ are math symbols, ranges use `--`.
- Citations: `\citep{...}` for purely bibliographic parentheses, `\citealp{...}` inside running parentheses,
  `\citet{...}` in text. Keys are `firstauthorYEAR` (see `refs.bib`).
- PRISM is the authors' own system and is not yet published: never write "published". The original 0.80 result is "our initial single-split evaluation" on "our initial evaluation split".
- Supplementary tables carry fixed numbers (`\renewcommand{\thetable}{S..}` inside each float) so that the
  numbering of the frozen draft is preserved; tables without a number in the draft have no caption.
- Line numbers (`lineno`) and 1.3 line spread are for review; remove `\linenumbers` / adjust `\linespread` in
  `macros.tex` for a journal template.
