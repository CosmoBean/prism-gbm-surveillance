"""Repeated patient-grouped stratified folds (D7). Every model reads the same folds.

    uv run python -m prism.folds   # writes outputs/cohort/folds.csv
"""

from __future__ import annotations

import pandas as pd
from sklearn.model_selection import StratifiedGroupKFold

from prism.config import N_FOLDS, N_REPEATS, OUTPUTS, PRIMARY_HORIZON


def make_folds(cohort: pd.DataFrame, n_repeats: int = N_REPEATS, n_folds: int = N_FOLDS) -> pd.DataFrame:
    """Stratify on (120-day status incl. censored, grade 4) so each fold mirrors the cohort; group by patient."""
    status = cohort[f"label_{PRIMARY_HORIZON}"].map({1.0: "pos", 0.0: "neg"}).fillna("cens")
    strata = status + "_" + cohort["grade4"].astype(str)
    rows = []
    for r in range(n_repeats):
        sgkf = StratifiedGroupKFold(n_splits=n_folds, shuffle=True, random_state=r)
        for k, (_, test_idx) in enumerate(sgkf.split(cohort, strata, cohort["patient_id"])):
            rows += [{"scan_id": cohort.scan_id.iat[i], "patient_id": cohort.patient_id.iat[i], "repeat": r, "fold": k}
                     for i in test_idx]
    folds = pd.DataFrame(rows)
    assert folds.groupby(["repeat", "patient_id"]).fold.nunique().max() == 1, "patient split across folds"
    return folds


def main() -> None:
    cohort = pd.read_csv(OUTPUTS / "cohort" / "cohort.csv")
    folds = make_folds(cohort)
    folds.to_csv(OUTPUTS / "cohort" / "folds.csv", index=False)
    print(folds.groupby(["repeat", "fold"]).size().unstack().to_string())


if __name__ == "__main__":
    main()
