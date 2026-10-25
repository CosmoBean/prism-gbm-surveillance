# The full PRISM system for detection at the scan: plan (pre-specified)

**Written 2026-10-26, before any run below.** Committed before the first run that reads labels with system outputs.
Anything added after the results is marked *EXPLORATORY*.

The author's direction (2026-10-26) is a modular system:
- clinical and timeline features in one pathway;
- simple, engineered image measurements in another;
- deep segmentation supplying the measurements and the report's images;
- a confidence made of the reliability card's tier plus a numeric per-scan measure.

Earlier work: [RELIABILITY_CARD.md](RELIABILITY_CARD.md), [AUDIT_SYSTEM.md](AUDIT_SYSTEM.md) (P1 / P2 conformal and
selective prediction, built for the 120-day task), [REPORT_AGENT.md](REPORT_AGENT.md),
[REPORT_USEFULNESS.md](REPORT_USEFULNESS.md), [DETECTION_TASK.md](DETECTION_TASK.md),
[UCSF_RESULTS.md](UCSF_RESULTS.md).

## 1. The system's output per scan

The task is detection at the scan: is this scan the one at which progression is called?

| field | MU (development) | LUMIERE, UCSF (external, locked) |
|---|---|---|
| timeline pathway score | B1, out-of-fold (5 × 5) | the transportable timeline (Tbase), locked; the UCSF-trained timeline is not used (not locked) |
| image pathway score | I_pure, out-of-fold | locked MU I_pure; I_scan where there is no previous scan |
| combined score | B1 + I_pure | locked T |
| measurements from segmentation | ET, SNFH, necrosis, cavity volumes; change from the previous scan and from the smallest earlier volume | same |
| reliability card | tier of the scan's situation (RELIABILITY_CARD.md) | same lookup |
| conformal set | per pathway and combined, α = 0.2 and 0.1 | MU-calibrated, applied locked |
| flags | pathways disagree; out of training range; card tier "few cases" or "not tested"; conformal set {0, 1} | same |

Populations: grade 4 primary (MU intended use; LUMIERE; UCSF grade-4 scan 2), all gliomas secondary. Labels and
negatives exactly as in DETECTION_TASK.md and UCSF_PLAN.md.

## 2. Numeric confidence: conformal sets

- **Method:** patient-level split conformal (`prism/audit/conformal.py`), as in AUDIT_SYSTEM.md.
- **MU:** inside each outer training fold, a 70 / 30 patient split gives proper-training and calibration sets. The
  conformal model is the same pathway refitted on the 70%. Its AUC is reported as the cost of splitting.
- **External:** one MU-calibrated model and threshold per pathway, applied once.
- **Also reported:** class-conditional (Mondrian) sets as a secondary.

## 3. Pre-specified questions

| # | question | met if |
|---|---|---|
| S1 | Do the conformal sets keep their coverage? | coverage ≥ 0.78 at α = 0.2 on MU (out-of-fold) and on each external cohort, with the patient-bootstrap CI reported; per-situation coverage reported as conditional coverage |
| S2 | Do the system's flags pick out the scans where it is wrong? | AUC on unflagged scans minus AUC on flagged scans > 0, CI excluding 0, for the combined score on MU; also on LUMIERE and UCSF |
| S3 | Does abstaining on flagged scans beat removing the same number at random? | retained-scan AUC minus composition-matched random-removal AUC > 0, CI excluding 0 (the P2 design of AUDIT_SYSTEM.md) |
| S4 | Do the card's tiers mean something? | Brier score and error rate at the cohort-median threshold, by tier; descriptive. "Tested" should be lower than "few cases" |
| S5 | Are the reports faithful to the record, including the card? | ≥ 95% of evaluation reports pass the deterministic checker with the card rule (`check(..., card=True)`) |
| S6 | Do the reports state the tier where the evidence is thin? | 100% of reports for "few cases" / "not tested" scans state the tier |
| S7 | Do the reports follow the record? | in a perturbation set (one field changed per record), the report changes accordingly in ≥ 90% |

Each flag is also reported on its own for S2 and S3: disagreement, out of range, tier, conformal {0, 1}.

## 4. Reports (version 3)

- **Model and serving:** the same local model and serving as REPORT_AGENT.md (Qwen3.8-27B, vLLM, separate env).
  Here it runs on one H100 (tensor parallel 1). If it cannot fit, use FP8 weights of the same model and record the
  deviation. Temperature 0, seed 0. No patient data leaves the cluster.
- **What a report contains:** written only from the system record of section 1:
  - the two pathways side by side;
  - the combined score;
  - the card's tier, stated in plain words;
  - the conformal set;
  - the flags;
  - the segmentation measurements, with a figure of the segmentation (deterministic; the LLM does not see images).

  It gives no recommendation or decision.
- **Development set:** 20 MU patients, fixed by seed 20261026 before any report is generated. Prompts are iterated
  only on these patients.
- **Evaluation set:** all other MU grade-4 detection scans in the intended use, all LUMIERE detection scans, and all
  UCSF grade-4 scan-2 records.
- **Perturbation set:** 30 evaluation records, each with one field changed:
  - the card tier;
  - pathway agreement;
  - the ET change;
  - the out-of-range flag;
  - the conformal set.
- **The checker:** the existing deterministic checker, extended to the new fields. The checker rules are frozen
  before evaluation reports are generated.

## 5. Outputs

- `outputs/results/analyses/system/`:
  - `records_{mu,lumiere,ucsf}.jsonl` (one system record per scan);
  - `conformal*.csv`, `selective*.csv`, `tiers.csv`;
  - `figures/<scan_id>.png` (segmentation panels).
- `outputs/results/analyses/report_v3/`: the reports, checker results and perturbation results.
- Results go in `docs/results/SYSTEM_RESULTS.md` and `docs/results/REPORT_V3.md`.
