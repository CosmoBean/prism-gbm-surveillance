"""Auditable decision-support layer around the clinical + timing + treatment ridge baseline.

model       design matrix, pipeline fit (identical to c3.fit_predict for the baseline), exact log-odds contributions,
            patient-cluster bootstrap refits, out-of-distribution ranges, the locked artifact
conformal   patient-level split-conformal prediction sets for the binary 120-d label
record      per-scan audit record (inputs with source and as-of day, phase, risk + interval, contributions, flags)
provenance  feature card (unit, source column), file hashes, git state, package versions

See docs/results/AUDIT_SYSTEM.md.
"""
