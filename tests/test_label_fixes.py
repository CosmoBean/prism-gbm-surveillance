"""Label/cohort fixes (docs/results/FIX_LABELS.md): death censoring, composite and alt-date labels, progression-flag
conflicts, death-date conflicts, implausible MRI days, hazard intervals."""

from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from prism.data.mu import add_outcomes, eligible_scans, patient_dates
from prism.models.formulations import person_period

DEATH = "clinical_number_of_days_from_diagnosis_to_death_days"
PROG = "clinical_number_of_days_from_diagnosis_to_date_of_first_progression"
ALT = "clinical_time_to_first_progression_days"


def index(rows):
    """rows: (patient, timepoint, mri day, progression flag, progression date, alt date, died, death day)."""
    df = pd.DataFrame(rows, columns=["patient_id", "timepoint_number", "days_from_diagnosis_to_mri",
                                     "clinical_progression", PROG, ALT, "clinical_overall_survival_death", DEATH])
    df["scan_id"] = df.patient_id + "_" + df.timepoint_number.astype(str)
    df["complete"] = True
    df[["label1_voxels", "label2_voxels", "label3_voxels"]] = 100
    return df


IDX = index([
    ("flag0_date", 1, 70, 0, 168, np.nan, 0, np.nan),     # flag 0 but dated progression -> progressor
    ("flag0_date", 2, 168, 0, 168, np.nan, 0, np.nan),    # on the progression day -> not an index scan
    ("bad_mri", 1, 24, 1, 200, 200, 0, np.nan),
    ("bad_mri", 2, -965, 1, 200, 200, 0, np.nan),         # before diagnosis and before TP1 -> excluded
    ("one_after", 1, 10, 0, np.nan, np.nan, 1, 60),
    ("one_after", 2, 80, 0, np.nan, np.nan, 1, 60),       # single scan after death -> scan excluded
    ("many_after", 1, 20, 0, np.nan, np.nan, 1, 30),
    ("many_after", 2, 90, 0, np.nan, np.nan, 1, 30),      # 2 scans after death -> death date ignored
    ("many_after", 3, 300, 0, np.nan, np.nan, 1, 30),
    ("alt", 1, 50, 1, 300, 100, 0, np.nan),               # fields disagree: 250 d vs 50 d after the scan
])


class CohortRuleTests(unittest.TestCase):
    def setUp(self):
        self.scans, self.flow = eligible_scans(IDX)

    def test_exclusions(self):
        kept = set(self.scans.scan_id)
        self.assertIn("flag0_date_1", kept)
        self.assertNotIn("flag0_date_2", kept)
        self.assertNotIn("bad_mri_2", kept)
        self.assertNotIn("one_after_2", kept)
        self.assertTrue({"many_after_2", "many_after_3"} <= kept)

    def test_patient_dates(self):
        p = patient_dates(IDX)
        self.assertTrue(p.at["flag0_date", "progressor"] and p.at["flag0_date", "progression_flag_conflict"])
        self.assertTrue(p.at["many_after", "death_date_conflict"] and np.isnan(p.at["many_after", "death_day"]))
        self.assertEqual(p.at["one_after", "death_day"], 60)
        self.assertEqual((p.at["alt", "progression_day"], p.at["alt", "progression_day_alt"]), (300, 100))

    def test_outcomes(self):
        last = pd.Series({"flag0_date": 168, "bad_mri": 200, "one_after": 80, "many_after": 300, "alt": 300})
        d = add_outcomes(self.scans, last, horizons=(120,)).set_index("scan_id")
        self.assertEqual(d.at["flag0_date_1", "label_120"], 1.0)        # progression 98 d after the scan
        self.assertTrue(np.isnan(d.at["one_after_1", "label_120"]))      # censored at death (50 d)
        self.assertEqual(d.at["one_after_1", "label_120_composite"], 1.0)
        self.assertEqual(d.at["one_after_1", "time_to_event"], 50)
        self.assertEqual(d.at["many_after_1", "label_120"], 0.0)         # death ignored: follow-up 280 d
        self.assertEqual(d.at["alt_1", "label_120"], 0.0)
        self.assertEqual(d.at["alt_1", "label_120_altdate"], 1.0)
        self.assertFalse(d["status_known_indefinitely"].any())


class CompositeTests(unittest.TestCase):
    def test_death_after_horizon_needs_follow_up(self):
        s = pd.DataFrame({"patient_id": ["a", "b"], "days_from_diagnosis_to_mri": [0, 0], "clinical_progression": 0,
                          "progression_day": np.nan, "death_day": [200.0, np.nan]})
        d = add_outcomes(s, pd.Series({"a": 50, "b": 50}), horizons=(120,), last_mri=pd.Series({"a": 50, "b": 50}))
        self.assertEqual(d["label_120"].tolist()[0], 0.0)                 # MU: follow-up runs to death (200 d)
        self.assertEqual(d["label_120_composite"].tolist()[0], 0.0)
        self.assertTrue(np.isnan(d["label_120_imgfu"].iat[0]))            # imaging follow-up only 50 d
        self.assertTrue(np.isnan(d["label_120"].iat[1]))


class HazardIntervalTests(unittest.TestCase):
    def test_mid_interval_censoring_not_counted(self):
        d = pd.DataFrame({"patient_id": ["c75", "e75"], "event": [False, True], "time_to_event": [75.0, 75.0],
                          "status_known_indefinitely": False})
        _, y, _, g = person_period(np.zeros((2, 1)), d, 120)
        per = pd.Series(y).groupby(g).agg(["size", "sum"])
        self.assertEqual(per.loc["c75"].tolist(), [2, 0])   # intervals (0,30], (30,60] fully observed; (60,90] not
        self.assertEqual(per.loc["e75"].tolist(), [3, 1])


if __name__ == "__main__":
    unittest.main()
