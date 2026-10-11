"""As-of-scan treatment features: nothing about a therapy is visible before its documented start (or end) day."""

from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from prism.features.tabular import timing, treatment

RT_START, RT_END, CHEMO_START = 20.0, 62.0, 21.0


def make(days):
    """One patient (RT 60 Gy / 30 fx on days 20-62, TMZ from day 21, surgery day 0) scanned on each of `days`."""
    ids = [f"s{i}" for i in range(len(days))]
    index = pd.DataFrame({
        "scan_id": ids,
        "clinical_radiation_therapy": "Yes",
        "clinical_number_of_days_from_diagnosis_to_radiation_therapy_start_date": RT_START,
        "clinical_number_of_days_from_diagnosis_to_radiation_therapy_end_date": RT_END,
        "clinical_dose": "60 Gy",
        "clinical_number_of_fractions": 30.0,
        "clinical_initial_chemo_therapy": "Yes",
        "clinical_number_of_days_from_diagnosis_to_initial_chemo_therapy_start_date": CHEMO_START,
        "clinical_number_of_days_from_diagnosis_to_first_surgery_or_procedure": 0.0,
        "clinical_stereotactic_biopsy_before_surgical_resection": 0.0,
        "clinical_previous_brain_tumor": "No",
    })
    days = np.asarray(days, float)
    since_end = days - RT_END
    cohort = pd.DataFrame({"scan_id": ids, "days_from_diagnosis_to_mri": days, "days_since_rt_end": since_end,
                           "early_post_rt": (since_end >= 0) & (since_end <= 84), "mgmt": "methylated",
                           "visit_index": np.arange(1, len(days) + 1)})
    return cohort, index


class TreatmentAsOfTests(unittest.TestCase):
    def setUp(self):
        self.cohort, index = make([10, 40, 100, 300])  # before RT start, during RT, 38 d after RT end, late
        self.t = treatment(self.cohort, index)
        self.time = timing(self.cohort)

    def test_before_rt_start_sees_nothing(self):
        r = self.t.iloc[0]
        self.assertEqual((r.rt_started, r.rt_completed, r.chemo_started), (0.0, 0.0, 0.0))
        for c in ("rt_dose_gy", "rt_fractions", "rt_hypofractionated", "rt_start_day", "rt_duration_days"):
            self.assertTrue(np.isnan(r[c]), c)
        self.assertTrue(np.isnan(self.time.days_since_rt_end.iat[0]))
        self.assertEqual(self.time.rt_date_unknown.iat[0], 1.0)

    def test_during_rt_sees_prescription_not_duration(self):
        r = self.t.iloc[1]
        self.assertEqual((r.rt_started, r.rt_completed, r.chemo_started), (1.0, 0.0, 1.0))
        self.assertEqual((r.rt_dose_gy, r.rt_fractions, r.rt_hypofractionated), (60.0, 30.0, 0.0))
        self.assertTrue(np.isnan(r.rt_duration_days))
        self.assertTrue(np.isnan(self.time.days_since_rt_end.iat[1]))

    def test_after_rt_end_sees_everything(self):
        for i in (2, 3):
            r = self.t.iloc[i]
            self.assertEqual((r.rt_started, r.rt_completed, r.chemo_started), (1.0, 1.0, 1.0))
            self.assertEqual((r.rt_dose_gy, r.rt_start_day, r.rt_duration_days), (60.0, RT_START, RT_END - RT_START))
        self.assertEqual(self.time.days_since_rt_end.tolist()[2:], [38.0, 238.0])

    def test_pseudoprogression_window_and_mgmt(self):
        self.assertEqual(self.time.early_post_rt.tolist(), [0.0, 0.0, 1.0, 0.0])
        self.assertEqual(self.time.early_post_rt_x_mgmt_methylated.tolist(), [0.0, 0.0, 1.0, 0.0])

    def test_missing_start_date_counts_as_started(self):
        cohort, index = make([10])
        index["clinical_number_of_days_from_diagnosis_to_initial_chemo_therapy_start_date"] = np.nan
        self.assertEqual(treatment(cohort, index).chemo_started.iat[0], 1.0)

    def test_no_rt(self):
        cohort, index = make([100])
        index["clinical_radiation_therapy"] = np.nan
        r = treatment(cohort, index).iloc[0]
        self.assertEqual((r.rt_started, r.rt_completed), (0.0, 0.0))
        self.assertTrue(np.isnan(r.rt_dose_gy))


if __name__ == "__main__":
    unittest.main()
