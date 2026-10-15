"""Command line entry point: `python -m prism <stage> [options]` (or `prism <stage>` once installed).

Data preparation (run in order; each writes to $PRISM_OUTPUTS):
    mu            MU-Glioma-Post index, surveillance cohort with censoring-aware labels, CV folds
    lumiere       LUMIERE cohort with RANO-derived labels and DeepBraTumIA volumes
    measurements  compartment volumes, morphology, intensity ratios, past-only change features
    radiomics     corrected compartment-wise PyRadiomics features (slow; needed only for c3)
    data          mu + lumiere + measurements

Experiments (read the prepared tables, write to $PRISM_OUTPUTS/results):
    c1            outcome formulation: naive vs censoring-aware labels
    c2            feature-group search with nested selection
    c3            does radiomics add to a clinical + timing + treatment baseline?
    external      train on MU, test on LUMIERE (locked, recalibrated, fine-tuned)

Analyses (read the prepared tables, write to $PRISM_OUTPUTS/results):
    head2head     C3 pipelines vs the PRISM report radiomics model on the PRISM report split (30 test patients)
    splitvar      where the PRISM report split's AUC sits among random splits of the same design
    deep          frozen deep-encoder features vs the C3 baseline (needs features from GPU extraction; see scripts/)
    baselines     literature baselines (persistence, volumetric RANO-style rule, Cox) and a nested hyperparameter grid
    schedule      is the signal a proxy for the surveillance schedule (gap to next scan)?
    utility       calibration, decision curves, NRI/IDI, sample size
    sensitivity   primary comparison under other horizons, labels and subsets
    tables        Table 1, cohort flow, manuscript tables
    phaseladder   phase-of-care ladder: imaging added value per non-imaging base, full and post-RT cohorts
    cleanlabel    imaging-defined MU endpoint (clinical-only progression censored) + LUMIERE imaging vs clinical
    cfbadc        CFB-GBM: does ADC radiomics at t1 add to conventional radiomics for t1->t2 RANO progression?
    audit         auditable decision-support layer on the baseline: locked model + card, per-scan audit records,
                  conformal/selective prediction, referral rules, shortcut/subgroup audit, explanation stability
    figures       manuscript figures 1-4 and tables (re-fits the PRISM report split and the clipped split-variance arm)

Every stage takes -h for its options.
"""

from __future__ import annotations

import importlib
import sys

STAGES = {
    "mu": "prism.data.mu",
    "lumiere": "prism.data.lumiere",
    "measurements": "prism.features.measurements",
    "radiomics": "prism.features.radiomics",
    "c1": "prism.experiments.c1_endpoint",
    "c2": "prism.experiments.c2_feature_search",
    "c3": "prism.experiments.c3_radiomics",
    "external": "prism.experiments.external_lumiere",
    "head2head": "prism.analyses.head_to_head",
    "splitvar": "prism.analyses.split_variance",
    "deep": "prism.analyses.deep_features",
    "baselines": "prism.analyses.baselines",
    "schedule": "prism.analyses.schedule",
    "utility": "prism.analyses.utility",
    "sensitivity": "prism.analyses.sensitivity",
    "tables": "prism.analyses.tables",
    "phaseladder": "prism.analyses.phase_ladder",
    "cleanlabel": "prism.analyses.clean_label",
    "cfbadc": "prism.analyses.cfb_adc",
    "audit": "prism.analyses.audit_system",
    "figures": "prism.analyses.paper_figures",
}
PIPELINES = {"data": ("mu", "lumiere", "measurements")}


def main(argv: list[str] | None = None) -> None:
    argv = sys.argv[1:] if argv is None else argv
    if not argv or argv[0] in ("-h", "--help") or argv[0] not in STAGES.keys() | PIPELINES.keys():
        print(__doc__)
        sys.exit(0 if argv and argv[0] in ("-h", "--help") else 2)
    stage, rest = argv[0], argv[1:]
    for s in PIPELINES.get(stage, (stage,)):
        print(f"== prism {s}", flush=True)
        importlib.import_module(STAGES[s]).main(rest)


if __name__ == "__main__":
    main()
