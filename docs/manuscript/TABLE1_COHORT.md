# Table 1. Cohort characteristics

Development cohort MU-Glioma-Post (all gliomas and the grade 4 subset) and external test cohort LUMIERE. Index scans are
post-treatment MRIs before first progression (cohort flow: `FLOW.md`). Labels are the primary censoring-aware labels
(`label_{H}`; death without documented progression censors; `docs/results/FIX_LABELS.md`).

| | MU all gliomas | MU grade 4 | LUMIERE |
|---|---|---|---|
| **Cohort** | | | |
| Patients | 155 | 126 | 61 |
| Index scans | 308 | 249 | 132 |
| Index scans per patient, median (range) | 2 (1–6) | 2 (1–6) | 2 (1–10) |
| **Patient level (first index scan)** | | | |
| Age, years, median [IQR] | 61 [47–69] | 62 [53–70] | 62 [53–70] |
| Male sex | 80 (52%) | 66 (52%) | 32 (52%) |
| IDH wildtype | 120 (77%) | 112 (89%) | 38 (62%) |
| IDH mutant | 22 (14%) | 8 (6%) | 1 (2%) |
| IDH unknown | 13 (8%) | 6 (5%) | 22 (36%) |
| MGMT methylated | 53 (34%) | 45 (36%) | 26 (43%) |
| MGMT unmethylated | 73 (47%) | 62 (49%) | 28 (46%) |
| MGMT unknown | 29 (19%) | 19 (15%) | 7 (11%) |
| WHO grade 1 | 3 (2%) | 0 | 0 |
| WHO grade 2 | 23 (15%) | 0 | 0 |
| WHO grade 3 | 2 (1%) | 0 | 0 |
| WHO grade 3 vs 4 | 1 (1%) | 0 | 0 |
| WHO grade 4 | 126 (81%) | 126 (100%) | 61 (100%) |
| Radiotherapy (any, documented) | 102 (66%) | 89 (71%) | not recorded |
| Initial chemotherapy (documented) | 96 (62%) | 88 (70%) | not recorded |
|   of which temozolomide | 95 (61%) | 87 (69%) | not recorded |
| **Scan level (all index scans)** | | | |
| Days from origin to scan, median [IQR] | 97 [46–186] | 96 [54–182] | 119 [82–226] |
| RT completed by scan day | 185 (60%) | 167 (67%) | not recorded |
| Early post-RT window | 104 (34%); unknown 94 | 98 (39%); unknown 65 | 27 (20%) |
| Gap to next MRI, days, median [IQR] | 77 [50–103] | 74 [49–98] | 91 [77–117] |
| Last documented follow-up after scan, days, median [IQR] | 275 [107–471] | 285 [112–478] | 462 [238–721] |
| Time to progression or censoring, days, median [IQR] | 125 [50–237] | 111 [48–208] | 168 [91–287] |
| Progression documented after scan (any time) | 220 (71%) | 190 (76%) | 122 (92%) |
| Death without documented progression | 22 (7%) | 20 (8%) | 7 (5%) |
| Field strength (T1c) 1.5 T / 3 T / other or missing | not distributed | not distributed | 81 (61%) / 44 (33%) / 7 |
| **Primary label, scans** | | | |
| 90 d: progression / no progression / censored | 65 / 195 / 48 | 62 / 152 / 35 | 24 / 101 / 7 |
| 120 d: progression / no progression / censored | 100 / 156 / 52 | 93 / 117 / 39 | 47 / 76 / 9 |
| 180 d: progression / no progression / censored | 144 / 105 / 59 | 131 / 75 / 43 | 62 / 61 / 9 |

Values are n (%) or median [IQR]. Percentages use the column's patients (patient rows) or index scans (scan rows).

**Definitions and caveats**
- **Patient-level rows** use each patient's first index scan. Age: MU = age at diagnosis; LUMIERE = age at surgery.
- **Grade.** MU: `clinical_grade_of_primary_brain_tumor` (one patient is recorded as "3 vs 4" and is not in the grade 4 subset).
  LUMIERE is a glioblastoma cohort by dataset definition, so every patient is counted as grade 4.
- **Treatment.** MU: radiotherapy = "Yes" or "Proton Therapy"; chemotherapy = initial chemotherapy "Yes" (agent shown when
  temozolomide). "RT completed by scan day" = documented RT end date on or before the scan day. LUMIERE does not record
  treatment per patient.
- **Days from origin to scan.** MU: days since diagnosis. LUMIERE: days since first surgery (rating week × 7). The origins
  differ, so the two are not directly comparable.
- **Early post-RT window.** MU: 0–84 d after the documented RT end date; unknown when the RT end date is missing (counted in the
  denominator). LUMIERE: the rater's "LessThan3Months" flag. The definitions differ (`FIX_LABELS.md`, rule 6).
- **Gap to next MRI.** From an index scan to the patient's next MRI of any kind (MU: any timepoint in the dataset, including
  excluded ones; LUMIERE: any rated study), among index scans that have a later MRI.
- **Last documented follow-up.** MU: death day if dead, otherwise the last documented day in the clinical record (includes
  non-imaging dates). LUMIERE: the earlier of the last rated study and death. **Time to progression or censoring** is the
  `time_to_event` used by the censoring-aware labels and IPCW.
- **Progression documented after scan** counts index scans whose patient has a documented first progression at any later
  time (MU: clinical record; LUMIERE: first RANO PD rating).
- **Field strength.** LUMIERE: `LUMIERE-MRinfo.csv`, T1c (CT1) series of each index study; "other or missing" = 1.0 T or no
  entry. MU-Glioma-Post is distributed as pre-processed NIfTI without acquisition metadata, so field strength is not available.

**Source.** `python -m prism.analyses.tables` → `$PRISM_OUTPUTS/results/analyses/tables/table1.{csv,md}` (copy:
`docs/manuscript/table1.csv`). Inputs: `outputs/data/mu_cohort.csv`, `mu_index.csv`, `lumiere_cohort.csv` (post-fix tables of
2026-10-11, HEAD 478e280) and the raw LUMIERE rating / MR-info CSVs. Built here from a private copy of `outputs/data`; the
coordinator should re-run the module on the final outputs (numbers should not change unless the cohort tables change).
