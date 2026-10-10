# PRISM — progression risk during post-treatment glioma surveillance

Given one follow-up MRI of a treated glioma (plus the clinical and treatment information known on that day),
estimate the probability of progression within the next 120 days. The pipeline handles censoring (scans whose
follow-up ends before 120 days), evaluates with censoring-aware metrics under patient-grouped cross-validation, and
tests transport to an external cohort.

- Development: **MU-Glioma-Post** (University of Missouri, TCIA; 203 patients, 596 timepoints, expert-refined
  4-label masks, clinical workbook).
- External test: **LUMIERE** (Suter et al., Sci Data 2022; 91 GBM patients, expert RANO rating per timepoint).

## Install

Python 3.11–3.12 and [uv](https://docs.astral.sh/uv/):

```bash
uv sync                    # core pipeline
uv sync --extra legacy     # also the archived code in legacy/ (torch, MONAI, LightGBM, ...)
```

Or with pip (pyradiomics 3.0.1 needs numpy at build time):

```bash
pip install numpy==2.2.6 versioneer
pip install --no-build-isolation pyradiomics==3.0.1
pip install -e .
```

## Data

Put the datasets under `data/` (or point the environment variables at them):

| Dataset | Where to get it | Expected layout | Override |
|---|---|---|---|
| MU-Glioma-Post | TCIA, [doi:10.7937/7K9K-3C83](https://doi.org/10.7937/7K9K-3C83) (descriptor: [doi:10.1038/s41597-025-06011-7](https://doi.org/10.1038/s41597-025-06011-7)) | `data/mu-glioma-post/MU-Glioma-Post/PatientID_*/Timepoint_*/*.nii.gz` and `data/mu-glioma-post/MU-Glioma-Post_ClinicalData-July2025.xlsx` | `PRISM_MU` |
| LUMIERE | figshare, linked from [doi:10.1038/s41597-022-01881-7](https://doi.org/10.1038/s41597-022-01881-7) | `data/lumiere/{LUMIERE-ExpertRating-v202211.csv, LUMIERE-Demographics_Pathology.csv, Imaging-v202211.zip}` | `PRISM_LUMIERE` |
| *(optional)* original PRISM radiomics | `hf download sbandred/mu-glioma-post-processed --repo-type dataset --local-dir data/mu-reference-processed` | `data/mu-reference-processed/postoperative_progression_surveillance/features/` | — |

The optional download is needed only for experiments that compare against the original PRISM radiomics features
(`c1`, `c2`, `c3`). Outputs go to `outputs/` (`PRISM_OUTPUTS`); image stages use all CPUs (`PRISM_WORKERS`).

## Run

```bash
uv run prism data          # = prism mu, prism lumiere, prism measurements   (~1 min on 100 CPUs)
uv run prism radiomics     # corrected PyRadiomics features (slow; only needed by c3)

uv run prism external      # train on MU, test on LUMIERE
uv run prism c1            # naive vs censoring-aware outcome formulations
uv run prism c2 --population grade4
uv run prism c3 --population grade4
uv run python -m unittest discover -s tests
```

`uv run prism` with no arguments lists the stages.

## Pipeline

| Stage | Module | Output (`outputs/`) |
|---|---|---|
| MU index → cohort → folds | `prism/data/mu.py`, `prism/models/folds.py` | `data/mu_index.csv`, `data/mu_cohort.csv`, `data/mu_flow.csv`, `data/folds.csv` |
| LUMIERE cohort | `prism/data/lumiere.py` | `data/lumiere_cohort.csv` |
| Image measurements | `prism/features/measurements.py` | `features/measurements.csv` |
| Radiomics | `prism/features/radiomics.py` | `features/radiomics.csv`, `features/radiomics_eroded.csv` |
| Feature groups | `prism/features/tabular.py` | (in memory: clinical, timing, treatment, volumes, morphology, delta, radiomics, shared MU/LUMIERE set) |
| Outcome formulations | `prism/models/formulations.py` | naive / verified / IPCW / discrete-time hazard learners |
| Metrics | `prism/models/metrics.py` | IPCW AUC(t), IPCW Brier(t), O/E, calibration slope, patient-cluster bootstrap |
| Experiments | `prism/experiments/*.py` | `results/<experiment>/` |

Cohort and label rules (applied in order, counts in `mu_flow.csv`): all four sequences and mask present → tumour
present → MRI day known → before late treatment (2nd-line, immunotherapy, new treatment) → before first progression.
Label at horizon H: 1 = progression within H days; 0 = progression later than H, death without progression, or
progression-free follow-up ≥ H; otherwise censored.

## Repository layout

```
prism/          the pipeline (data → features → models → experiments)
tests/          label, censoring and fold invariants
docs/           reviews, results write-ups, publication plan, literature comparison
legacy/         original PRISM code (radiomics search, SwinUNETR, MLP fusion, report agent) and reproduction
                scripts — kept for provenance, not used by the pipeline
```
