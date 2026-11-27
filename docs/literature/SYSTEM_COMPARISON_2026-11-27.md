# System comparison for contribution 2 (agent report 1 of 2, 2026-11-27; to be verified before use in the paper)

Columns: (1) separate imaging and clinical-history scores; (2) per-prediction uncertainty; (3) what the score rests on, by
design; (4) every follow-up scan; (5) tested at another institution unchanged (cohorts); (6) written report; (7) report
checked against a source record; (8) runs locally; (9) conventional MRI + clinical record only; (10) public data / code.
Y yes, N no (stated), P partial, NR not reported, n/a.

| System | Task, validation, result | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| PRISM | progression at the scan; CV MU, 2 locked externals; 0.82 / 0.79 / 0.81 | Y | Y | Y | Y (UCSF: 2nd scan only) | 2 | Y | Y | Y | Y | Y / to state |
| Jabal 2026 RYAI [full arXiv v2] | BT-RADS per exam, 492 exams, 1 centre; accuracy 76.0% | N | NR | Y (rule chain, evidence spans) | Y | 0 | NR | P | Y | Y | N / on request |
| Christodoulou 2026 [abs+code] | progression (patient label), MU, held-out 30; AUC 0.80 | N | P (Platt) | N (post hoc) | Y | 0 | NR | n/a | NR | P | Y / Y |
| Gomaa 2025 [full] | PsP vs TP, 59 -> 20 external; 0.753 / clinical 0.727 / imaging 0.717 | P (ablation) | NR | N (SHAP) | N | 1 | N | n/a | NR | P (+RT dose) | P / NR |
| Tarek 2026 TRACE [full] | 4-class RANO per pair, LUMIERE 5-fold CV; macro F1 0.48 | N | NR | Y (concepts) | P | 0 | N | n/a | NR | P | Y / Y |
| Siakallis & Bisdas 2026 Cancers [full] | rule-based RANO 2.0 on LUMIERE; agreement 48.1% (k 0.17) | N | N | Y (rules) | Y | P (1, rules) | N | n/a | NR | P (MRI) | Y / N |
| Tak 2025 NEJM AI [full] | paediatric 1-y EFS from last scan; external RadART; AUC 0.75-0.89 | N | P (ECE) | N (Grad-CAM) | P | 1 | N | n/a | NR | P (FLAIR) | P / NR |
| Jang 2018 Sci Rep [full] | PsP vs PD, 59 -> 19; 0.83 MRI+clinical | P (ablation) | NR | N | N | 1 | N | n/a | NR | Y | N / Y |
| Kim JY 2019 Neuro-Oncol [full] | PsP <=12 wk, 61 -> 34; 0.85 external | N | NR | N | N | 1 | N | n/a | NR | N (ADC, CBV) | NR / NR |
| BTReport 2026 MIDL [full] (report only) | pre-operative report generation | n/a | NR | Y | N | 0 | Y | N | Y | P | Y / Y |

Evidence quotes, extended list and recommendation: see the agent report in the session of 2026-11-27 (summarised in
the PI checklist). Caveat from the agent: its fetch tool summarises pages, so quotes must be checked against the PDFs
before they are quoted in the paper. Christodoulou, Kickingereder, Kamel and the Jabal journal version were paywalled.

Recommendation: one compact feature table next to contribution 2 (no AUC column; a task/validation column instead),
NR rather than N where a paper is silent, external cohorts counted, a combination claim only ("no other row has 1, 2,
5 (>= 2 cohorts) and 7 together"), no "first" or "outperforms".

# Agent report 2 of 2: report and language-model systems

| System | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | read |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Jabal 2026 | N (fused by rule) | N | Y | Y | N | N (category) | N (schema only) | Y | Y | P | full arXiv v2 |
| BTReport 2026 | N (no prediction) | N | Y | N (pre-op) | n/a | Y | N | Y | P | Y | full |
| Valerio 2025 | N | NS | P | NS | NS | Y | N (prevention only) | Y | P | Y | abstract + README |
| TumorBoard (Liu 2026, arXiv 2608.03190) | N | P (deferral) | Y | P | n/a | Y | N | NS | N | N | full |
| Mansour 2026 (liver CT) | N | N | Y | N | N | Y | Y (flags) | NS | N | Y | full |
| Miteva & Nisheva-Pavlova 2026 (arXiv 2610.08660, pre-op GBM MGMT) | N | N | Y | N | Y | P | Y | N | P | P | full PDF |

Also: Zeba 2026 (LLM-free claim checks, discharge summaries), Pham 2026 (ECG; conformal sets + verifier, blocks numbers),
Erdur 2026, Ra 2026 (cloud LLM checks), Zhou 2026 Front Oncol (separate clinical/imaging/integrated pseudoprogression
models, cohort-level, uses rCBV/ADC).
Counterexamples to "no published glioma follow-up system combines separate per-scan imaging and clinical scores,
per-scan uncertainty and a report whose numbers are checked against a record": none found. Suggested claim wording:
"In a focused search to November 2026, we found no published system for post-treatment glioma follow-up that shows,
for every scan, separate imaging and clinical-history scores with a per-scan uncertainty, and a report whose every
number is checked against a structured record." Credit precedents (Jabal, BTReport/Valerio, Mansour/Zeba/Miteva,
TumorBoard/Pham).
