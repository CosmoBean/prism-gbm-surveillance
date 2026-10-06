"""Invariants for the v2 data layer: labels, censoring, folds and person-period expansion."""

from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from prism.cohort import add_outcomes, idh_status, mgmt_status
from prism.folds import make_folds
from prism.formulations import person_period, predict_risk


def scans(rows):
    df = pd.DataFrame(rows, columns=["patient_id", "days_from_diagnosis_to_mri", "clinical_progression",
                                     "progression_day", "clinical_overall_survival_death"])
    return df


class LabelTests(unittest.TestCase):
    def setUp(self):
        self.d = add_outcomes(scans([
            ("p_pos", 100, 1, 150, 0),     # progresses 50 d after scan
            ("p_late", 100, 1, 400, 0),    # progresses 300 d after scan -> verified negative at 120
            ("n_short", 100, 0, np.nan, 0),  # follow-up 60 d, alive -> censored
            ("n_long", 100, 0, np.nan, 0),   # follow-up 200 d -> verified negative
            ("n_dead", 100, 0, np.nan, 1),   # died at 130 without progression -> verified negative
        ]), pd.Series({"p_pos": 150, "p_late": 400, "n_short": 160, "n_long": 300, "n_dead": 130}), horizons=(120,))

    def test_labels(self):
        self.assertEqual(self.d["label_120"].tolist()[:2], [1.0, 0.0])
        self.assertTrue(np.isnan(self.d["label_120"].iat[2]))
        self.assertEqual(self.d["label_120"].tolist()[3:], [0.0, 0.0])

    def test_naive_counts_censored_as_negative(self):
        self.assertEqual(self.d["naive_label_120"].tolist(), [1, 0, 0, 0, 0])

    def test_person_period(self):
        X = np.zeros((len(self.d), 1))
        Xr, y, _, g = person_period(X, self.d, 120)
        per = pd.Series(y).groupby(g).agg(["size", "sum"])
        self.assertEqual(per.loc["p_pos"].tolist(), [2, 1])   # event in 2nd 30-d interval
        self.assertEqual(per.loc["n_short"].tolist(), [2, 0])  # at risk for 60 d
        self.assertEqual(per.loc["n_long"].tolist(), [4, 0])
        self.assertEqual(per.loc["n_dead"].tolist(), [4, 0])   # death = non-event, full window


class CodebookTests(unittest.TestCase):
    def test_undocumented_codes_unknown(self):
        idh = idh_status(pd.Series([0, 1, 2, 0]), pd.Series([0, 0, 0, 2]))
        self.assertEqual(idh.tolist(), ["wildtype", "mutant", "unknown", "unknown"])
        self.assertEqual(mgmt_status(pd.Series([0, 1, 2, 3, 4])).tolist(),
                         ["unmethylated", "methylated", "unknown", "unknown", "unknown"])


class FoldTests(unittest.TestCase):
    def test_patients_not_split(self):
        rng = np.random.default_rng(0)
        c = pd.DataFrame({"scan_id": [f"s{i}" for i in range(120)], "patient_id": [f"p{i // 3}" for i in range(120)],
                          "label_120": rng.choice([0.0, 1.0, np.nan], 120), "grade4": rng.random(120) > 0.3})
        f = make_folds(c, n_repeats=2, n_folds=5)
        self.assertEqual(f.groupby(["repeat", "patient_id"]).fold.nunique().max(), 1)


class HazardPredictionTests(unittest.TestCase):
    def test_risk_from_constant_hazard(self):
        class Const:
            def predict_proba(self, X):
                return np.column_stack([np.full(len(X), 0.9), np.full(len(X), 0.1)])
        self.assertAlmostEqual(predict_risk("hazard", Const(), np.zeros((1, 2)))[0], 1 - 0.9 ** 4)


if __name__ == "__main__":
    unittest.main()
