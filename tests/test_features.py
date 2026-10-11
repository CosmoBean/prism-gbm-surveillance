"""Feature-layer fixes: harmonised MU<->LUMIERE volumes, within-cohort normalisation, delta flags, NAWM margin."""

from __future__ import annotations

import unittest
from unittest import mock

import numpy as np
import pandas as pd

from prism.features import measurements, tabular
from prism.features.measurements import PD_MIN_NADIR_CC, add_deltas, reference_mask, volumetric_pd


class SharedVolumes(unittest.TestCase):
    def test_lumiere_necrosis_maps_to_mu_netc_plus_cavity(self):
        self.assertIn("log_necrosis_cavity_cc", tabular.SHARED["volumes"])
        self.assertNotIn("log_netc_cc", tabular.SHARED["volumes"])
        lc = pd.DataFrame({"age": [60.0], "male": [1], "idh": ["wildtype"], "mgmt": ["unknown"], "days_since_surgery": [30],
                           "early_post_rt": [False], "raw_Enhancing_Core": [1000.0], "raw_Necrotic_NonEnhancing": [3000.0],
                           "raw_Edema_Compartment": [5000.0]})
        L = tabular.shared_lumiere(lc)
        self.assertAlmostEqual(L.log_necrosis_cavity_cc[0], np.log1p(3.0))
        self.assertAlmostEqual(L.log_core_cavity_cc[0], np.log1p(4.0))
        self.assertAlmostEqual(L.log_netc_cc[0], np.log1p(3.0))  # kept for reference, not comparable to MU

        mc = pd.DataFrame({"scan_id": ["a"], "age": [60.0], "male": [1], "idh": ["wildtype"], "mgmt": ["unknown"],
                           "days_from_diagnosis_to_mri": [100.0], "early_post_rt": [False]})
        m = pd.DataFrame({"et_cc": [1.0], "netc_cc": [0.0], "snfh_cc": [5.0], "rc_cc": [3.0]})
        tr = pd.DataFrame({"surgery_day": [0.0]})
        with mock.patch.object(tabular, "load_measurements", return_value=m), \
             mock.patch.object(tabular, "treatment", return_value=tr):
            M = tabular.shared_mu(mc)
        self.assertAlmostEqual(M.log_netc_cc[0], 0.0)
        self.assertAlmostEqual(M.log_necrosis_cavity_cc[0], np.log1p(3.0))
        self.assertAlmostEqual(M.log_core_cavity_cc[0], np.log1p(4.0))
        self.assertTrue(set(tabular.SHARED["volumes"]) <= set(M.columns) & set(L.columns))

    def test_within_cohort_normalise(self):
        X = pd.DataFrame({"log_et_cc": [0.0, 0.0, 1.0, 2.0], "age": [1.0, 2.0, 3.0, 4.0]})
        R = tabular.within_cohort_normalise(X, ["log_et_cc"], "rank")
        np.testing.assert_allclose(R.log_et_cc, [0.25, 0.25, 0.625, 0.875])  # ties share the mid-rank
        pd.testing.assert_series_equal(R.age, X.age)
        Z = tabular.within_cohort_normalise(X, ["log_et_cc"], "zscore")
        self.assertAlmostEqual(Z.log_et_cc.mean(), 0.0)
        self.assertAlmostEqual(Z.log_et_cc.std(ddof=0), 1.0)
        # a shifted / rescaled cohort (different segmenter) maps to the same ranks
        R2 = tabular.within_cohort_normalise(X.assign(log_et_cc=3 * X.log_et_cc + 5), ["log_et_cc"], "rank")
        np.testing.assert_allclose(R2.log_et_cc, R.log_et_cc)
        with self.assertRaises(ValueError):
            tabular.within_cohort_normalise(X, ["log_et_cc"], "bogus")


class Deltas(unittest.TestCase):
    def test_volumetric_pd_needs_measurable_nadir(self):
        self.assertEqual(volumetric_pd(2.0, 0.0), {"vol_pd_flag": 0.0, "et_new_from_zero_nadir": 1.0})
        self.assertEqual(volumetric_pd(0.5, 0.0), {"vol_pd_flag": 0.0, "et_new_from_zero_nadir": 0.0})
        self.assertEqual(volumetric_pd(3.0, 1.0), {"vol_pd_flag": 1.0, "et_new_from_zero_nadir": 0.0})
        self.assertEqual(volumetric_pd(1.3, 0.2), {"vol_pd_flag": 1.0, "et_new_from_zero_nadir": 0.0})
        self.assertEqual(volumetric_pd(10.5, 10.0), {"vol_pd_flag": 0.0, "et_new_from_zero_nadir": 0.0})
        self.assertEqual(volumetric_pd(1.0 + PD_MIN_NADIR_CC, PD_MIN_NADIR_CC)["vol_pd_flag"], 1.0)

    def test_add_deltas_past_only(self):
        base = {"netc_cc": 0.0, "snfh_cc": 1.0, "et_n_components": 1.0, "et_max_axial_mm2": 1.0, "flair_snfh_rel": 1.2}
        c = pd.DataFrame([dict(base, scan_id=f"p_{i}", patient_id="p", mri_day=d, et_cc=e, t1c_et_rel=t)
                          for i, (d, e, t) in enumerate([(10, 0.0, np.nan), (50, 2.0, 1.5), (90, 5.0, 1.6)])])
        c["tumor_cc"], c["lesion_cc"] = c.et_cc, c.et_cc + 1
        d = add_deltas(c).set_index("scan_id")
        self.assertEqual(d.loc["p_0", "has_prior"], 0.0)
        self.assertEqual(d.loc["p_1", "vol_pd_flag"], 0.0)
        self.assertEqual(d.loc["p_1", "et_new_from_zero_nadir"], 1.0)
        self.assertTrue(np.isnan(d.loc["p_1", "d_t1c_et_rel"]))
        self.assertEqual(d.loc["p_2", "et_new_from_zero_nadir"], 1.0)  # nadir is still the 0 cc scan

    def test_delta_group_flags_undefined_change(self):
        m = pd.DataFrame({"has_prior": [0.0, 1.0, 1.0], "n_prior_scans": [0.0, 1.0, 2.0],
                          "days_since_prior": [np.nan, 30.0, 30.0], "logratio_et_cc": [np.nan, 0.1, 0.2],
                          "rate_et_cc_per30d": [np.nan, 0.1, 0.2], "d_et_n_components": [np.nan, 0.0, 0.0],
                          "d_t1c_et_rel": [np.nan, np.nan, 0.1], "d_flair_snfh_rel": [np.nan, 0.0, 0.1],
                          "vol_pd_flag": [np.nan, 0.0, 1.0], "new_et_component": [np.nan, 0.0, 0.0],
                          "et_new_from_zero_nadir": [np.nan, 1.0, 0.0]})
        with mock.patch.object(tabular, "load_measurements", return_value=m.assign(
                **{c: 0.0 for c in ("et_cc", "netc_cc", "snfh_cc", "rc_cc", "tumor_cc", "lesion_cc", "et_fraction_of_tumor",
                                    "snfh_to_tumor_ratio", "has_cavity", "et_n_components", "et_largest_component_fraction",
                                    "et_max_axial_mm2", "et_near_cavity_fraction", "et_cavity_distance_mm_p50",
                                    "t1c_et_rel", "t1c_et_p90_rel", "t1c_netc_rel", "flair_snfh_rel", "flair_netc_rel")})):
            d = tabular.measurement_groups(pd.DataFrame({"scan_id": ["a", "b", "c"]}))["delta"]
        np.testing.assert_array_equal(d.d_t1c_et_rel_missing, [0.0, 1.0, 0.0])  # no prior -> has_prior covers it
        np.testing.assert_array_equal(d.d_t1c_et_rel, [0.0, 0.0, 0.1])
        np.testing.assert_array_equal(d.et_new_from_zero_nadir, [0.0, 1.0, 0.0])
        self.assertFalse(d.isna().any().any())


class ReferenceMask(unittest.TestCase):
    def test_euclidean_margin(self):
        brain = np.ones((41, 41, 41), bool)
        abnormal = np.zeros_like(brain)
        abnormal[20, 20, 20] = True
        nab = reference_mask(brain, abnormal, 10)
        self.assertFalse(nab[20, 27, 27])  # Euclidean 9.9 mm: excluded (city-block dilation (L1=14) kept it)
        self.assertTrue(nab[20, 28, 28])   # 11.3 mm: kept
        self.assertFalse(nab[20, 30, 20])  # exactly 10 mm: excluded
        self.assertTrue(nab[20, 31, 20])
        self.assertTrue(reference_mask(brain, np.zeros_like(brain), 10).all())
        self.assertEqual(measurements.NAWM_MARGIN_MM, 10)


if __name__ == "__main__":
    unittest.main()
