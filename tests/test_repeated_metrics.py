"""Repeated-CV estimator: mean over repeats of per-repeat pooled-OOF IPCW AUC, fast IPCW metrics == sksurv."""

from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from prism.models.metrics import (fast_auc_brier, fold_mean_metrics, ipcw_context, point_metrics,
                                  repeated_bootstrap, repeated_point_metrics)

H = 120


def cohort(n_pat=60, seed=0):
    rng = np.random.default_rng(seed)
    rows = []
    for p in range(n_pat):
        for _ in range(rng.integers(1, 4)):
            t = float(rng.integers(10, 400))
            event = bool(rng.random() < 0.5)
            indef = (not event) and rng.random() < 0.1
            label = 1.0 if event and t <= H else (0.0 if t > H or indef else np.nan)
            rows.append({"patient_id": f"p{p}", "event": event, "time_to_event": t, "status_known_indefinitely": indef,
                         f"label_{H}": label, f"naive_label_{H}": int(label == 1.0)})
    return pd.DataFrame(rows)


class RepeatedMetricTests(unittest.TestCase):
    def setUp(self):
        self.d = cohort()
        rng = np.random.default_rng(1)
        signal = self.d[f"label_{H}"].fillna(0.5).to_numpy()
        self.oof = np.clip(0.3 * signal[None] + rng.random((5, len(self.d))) * 0.7, 0.01, 0.99)

    def test_fast_metrics_match_sksurv(self):
        a, b = fast_auc_brier(ipcw_context(self.d, H), self.oof)
        for r in range(5):
            pm = point_metrics(self.d, self.oof[r], H)
            self.assertAlmostEqual(a[r], pm["auc_ipcw"], places=12)
            self.assertAlmostEqual(b[r], pm["brier_ipcw"], places=12)

    def test_headline_is_mean_over_repeats(self):
        manual = np.mean([point_metrics(self.d, o, H)["auc_ipcw"] for o in self.oof])
        averaged = point_metrics(self.d, self.oof.mean(0), H)["auc_ipcw"]
        rp = repeated_point_metrics(self.d, self.oof, H)
        self.assertAlmostEqual(rp["auc_ipcw"], manual, places=12)
        self.assertAlmostEqual(rp["auc_ipcw_averaged"], averaged, places=12)
        bt = repeated_bootstrap(self.d, {"m": self.oof, "ref": self.oof[::-1]}, H, reference="ref", n_boot=50)
        self.assertAlmostEqual(bt.set_index("model").loc["m", "auc_ipcw"], manual, places=12)
        self.assertAlmostEqual(bt.set_index("model").loc["m", "auc_ipcw_averaged"], averaged, places=12)

    def test_paired_difference_is_point_estimate_and_zero_for_identical_models(self):
        bt = repeated_bootstrap(self.d, {"a": self.oof, "b": self.oof.copy()}, H, reference="a", n_boot=50)
        row = bt.set_index("model").loc["b"]
        self.assertEqual(row["d_auc_ipcw_vs_a"], 0.0)
        self.assertEqual((row["d_auc_ipcw_lo"], row["d_auc_ipcw_hi"]), (0.0, 0.0))
        self.assertLessEqual(row["auc_ipcw_lo"], row["auc_ipcw"])
        self.assertGreaterEqual(row["auc_ipcw_hi"], row["auc_ipcw"])

    def test_per_fold_auc_invariant_to_per_fold_monotone_recalibration(self):
        folds = np.tile(np.arange(len(self.d)) % 5, (2, 1))
        p = self.oof[:2]
        recal = p.copy()
        for k in range(5):  # different increasing transform per fold: per-fold AUC must not change
            m = folds[0] == k
            recal[:, m] = p[:, m] ** (k + 1)
        a = fold_mean_metrics(self.d, p, folds, H)["auc_ipcw_fold_mean"]
        b = fold_mean_metrics(self.d, recal, folds, H)["auc_ipcw_fold_mean"]
        self.assertAlmostEqual(a, b, places=12)

    def test_pooled_oe_is_ratio_of_totals(self):
        folds = np.tile(np.arange(len(self.d)) % 5, (3, 1))
        same = np.tile(self.oof[0], (3, 1))  # a locked model: one prediction per scan in every repeat
        fm = fold_mean_metrics(self.d, same, folds, H)
        self.assertAlmostEqual(fm["oe_ratio_pooled"], point_metrics(self.d, self.oof[0], H)["oe_ratio"], places=12)
        doubled = fold_mean_metrics(self.d, same / 2, folds, H)
        self.assertAlmostEqual(doubled["oe_ratio_pooled"], 2 * fm["oe_ratio_pooled"], places=12)


if __name__ == "__main__":
    unittest.main()
