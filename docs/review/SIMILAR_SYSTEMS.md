# Similar systems, and what to call PRISM (2026-11-19)

A sub-agent's search for systems close to PRISM, made so the Introduction can say what PRISM *is*. It searched
published papers and preprints from 2022 to 2026, and every ID was checked to exist. "Partly verified" means only the
abstract or the listing was read.

The paper now cites the two nearest neighbours in the "what PRISM is" paragraph, after the contributions:
BTReport (`herasrivera2026`) and the Duke multi-agent BT-RADS system (`jabal2026`).

## Closest to PRISM

| Paper | What it is | How it is framed | What PRISM can take or contrast |
|---|---|---|---|
| Heras Rivera et al., BTReport, MIDL 2026, arXiv:2602.16006 | Deterministic features from T1 and masks (volumes, proportions, regions); an LLM "only for syntactic structuring"; a dataset and a review tool | "framework" | The precedent for separating measurement from narration. PRISM adds change over time, the treatment history, a cited key in every sentence and a checker that can reject a report. |
| Jabal et al., Duke, arXiv:2603.21494 | A CNN for segmentation and volumes; an "extractor agent" reads steroids, bevacizumab and the RT date from notes; a "scorer agent" applies the BT-RADS rules; 76.0% against 57.5% for the initial reads (509 MRIs) | "end-to-end multi-agent system" | The most direct competitor. Its "agents" are two fixed LLM calls, with no single-agent comparison. PRISM takes the history from the record as data, and adds conformal sets and the separate scores. |
| Bannur et al., MAIRA-2, arXiv:2406.04449 | An image encoder plus an LLM; current and prior images and reports; a box for each finding; RadFact checks each sentence | "model"; "grounded report generation" | The word "grounded", and judging one sentence at a time. PRISM grounds each sentence in a record key, and its check is deterministic and runs on every report. |

## LLM "agents"

| Paper | Architecture | Framing | Note |
|---|---|---|---|
| Ferber et al., Nature Cancer 2025, doi:10.1038/s43018-025-00991-6 | GPT-4 chooses which tools to call (radiology, pathology and mutation models, guideline search); 87.2% decision accuracy with tools against 30.3% without | "autonomous AI agent" | Sets the meaning of "agent": the model chooses its actions. PRISM's language model chooses nothing. |
| Fallahpour et al., MedRAX, arXiv:2502.02673 | A reason-and-act loop over chest X-ray tools | "AI agent" | The same contrast as Ferber. |

## Prediction model, conformal set, then an LLM

| Paper | Architecture | Note |
|---|---|---|
| Li et al., ConMIL, arXiv:2501.16215 | A small multiple-instance model gives conformal sets, which are passed to an LLM for ECG and sleep-stage interpretation | The only precedent found for this chain; it was not in radiology or oncology. No paper was found combining a readable model, conformal sets and a checked LLM report. |

## Multi-agent evidence (for the "agent council" question)

- **MedAgentBoard** (arXiv:2505.12371, NeurIPS 2025 Datasets and Benchmarks): multi-agent setups "do not consistently
  outperform advanced single LLMs", and conventional models stay ahead on EHR prediction.
- **MDAgents** (Kim et al., arXiv:2404.15155): collaboration helps on complex medical QA, but simple cases do best with
  one model. All its gains are on QA benchmarks.
- **Kim et al., MLHC 2025** (PMLR v298; partly verified): role-play agents better approximate tumour-board decisions;
  the abstract gives no effect sizes.
- **Cemri et al.** (arXiv:2503.13657): 14 failure modes of multi-agent systems; gains are "often minimal";
  verification is one of the three failure categories, which is the problem PRISM's checker addresses.

## Glioma progression with clinical and imaging inputs

- Leone et al., Neuro-Oncol Adv 2023, doi:10.1093/noajnl/vdad016 (already cited): clinical data with MGMT gave 0.69,
  adding ADC/nrCBV gave 0.71, and radiomics and deep learning gave 0.52–0.56.
- Guo and Mirzaei, arXiv:2511.18595 (Cancers 2026; partly verified): 11 deep models on Burdenko follow-up MRI reached
  70–74% accuracy, better at the second follow-up.

## Recommendation (adopted)

- **"System"**, not "framework": the "framework" papers offer reusable methods or datasets. PRISM is a whole with a
  defined output.
- **Not "agent"**: in this literature an agent chooses its own actions, and PRISM's language model is a schema-bound
  writer with no tools.
- **No council**: the evidence shows no consistent gain over one model, and a council adds failure modes. The
  measurement → model → record → writer → checker separation is PRISM's answer to the same problem.
