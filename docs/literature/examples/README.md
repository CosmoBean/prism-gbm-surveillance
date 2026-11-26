# Example papers

Published papers kept as models for the writing and the figures of the PRISM manuscript.

The papers themselves are copyrighted. They stay local, and `.gitignore` keeps them out of the repository. Only this README and the `*_NOTES.md` files, which hold our own analysis, are tracked.

| Paper | Local files | Notes |
|---|---|---|
| Tak D et al. Longitudinal risk prediction for pediatric glioma with temporal deep learning. *NEJM AI* 2025;2(5). doi:10.1056/AIoa2400703 | `tak2025_nejmai.xml` is the JATS full text of the NIH author manuscript (PMC12176428, NCBI efetch), `tak2025_nejmai.txt` is NIH's plain-text copy from the public PMC Cloud Service bucket, and `tak2025_nejmai.md` is the text as markdown. `tak2025_figures/` holds figures 1–6. The PDF and the supplementary appendix are behind a reCAPTCHA on PMC, and the medRxiv preprint (doi:10.1101/2024.06.04.24308434) is behind Cloudflare, so both need a browser. | [tak2025_NOTES.md](tak2025_NOTES.md) |

To fetch another NIH-deposited paper, use `efetch.fcgi?db=pmc&id=<PMCID digits>&rettype=xml` for the text and `pmc.ncbi.nlm.nih.gov/articles/instance/<id>/bin/<figure>.jpg` for the figures (plain curl gets a bot-check page; the WebFetch tool follows the redirect to cdn.ncbi.nlm.nih.gov and works). Publisher sites (NEJM, T&F) block automated downloads.

NIH author manuscripts are also in the public bucket `https://pmc-oa-opendata.s3.amazonaws.com/` (`metadata/<PMCID>.1.json`, then `<PMCID>.1/<PMCID>.1.xml|.txt`). The bucket has text and XML, not PDFs.
