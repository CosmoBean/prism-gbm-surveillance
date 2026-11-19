# Example papers

Published papers kept as models for the writing and the figures of the PRISM manuscript.

The papers themselves are copyrighted. They stay local, and `.gitignore` keeps them out of the repository. Only this README and the `*_NOTES.md` files, which hold our own analysis, are tracked.

| Paper | Local files | Notes |
|---|---|---|
| Tak D et al. Longitudinal risk prediction for pediatric glioma with temporal deep learning. *NEJM AI* 2025;2(5). doi:10.1056/AIoa2400703 | `tak2025_nejmai.md` is the full text from the NIH author manuscript (PMC12176428, NCBI efetch). `tak2025_figures/` holds figures 1–5; figure 6 could not be downloaded. | [tak2025_NOTES.md](tak2025_NOTES.md) |

To fetch another NIH-deposited paper, use `efetch.fcgi?db=pmc&id=<PMCID digits>&rettype=xml` for the text and `pmc.ncbi.nlm.nih.gov/articles/instance/<id>/bin/<figure>.jpg` for the figures. Publisher sites (NEJM, T&F) block automated downloads.
