"""System records (prism.analyses.system): schema, no outcome label in a record, flags and conformal sets
(synthetic data only)."""

from __future__ import annotations

import json
import unittest

import numpy as np
import pandas as pd

from prism.analyses import system as S
from prism.audit import reliability as R

TABLE = [{"cohort": "mu", "cell": "later_post_rt|et_not_increased", "n_scans": 54, "n_pos": 38, "n_neg": 16,
          "n_patients": 40, "tier": "tested", **{f"{p}_{k}": v for p in R.PATHWAYS
                                                  for k, v in (("auc", 0.7), ("auc_lo", 0.6), ("auc_hi", 0.8))}},
         {"cohort": "mu", "cell": "early_post_rt|et_increased", "n_scans": 9, "n_pos": 1, "n_neg": 8,
          "n_patients": 9, "tier": "few cases", **{f"{p}_{k}": None for p in R.PATHWAYS
                                                    for k in ("auc", "auc_lo", "auc_hi")}}]
TOP = {"schema", "record_id", "cohort", "scan_id", "patient_id", "population", "population_flags", "phase_of_care",
       "situation", "scores", "measurements", "card", "conformal", "flags", "provenance"}


def cohort(n=6, R_=2):
    rng = np.random.default_rng(0)
    y = np.array([1, 0, 1, 0, np.nan, 0][:n])
    d = pd.DataFrame({"scan_id": [f"s{i}" for i in range(n)], "patient_id": [f"p{i // 2}" for i in range(n)],
                      "grade4": True, "intended_use": True, "phase": "later_post_rt", "label_120": y,
                      "label_det": np.nan_to_num(y), "neg_primary": y == 0, "neg_secondary": True})
    Sc = {f"{a}_{p}": rng.uniform(0.05, 0.95, (R_, n)) for a in ("p", "pc") for p in S.PW}
    sets = {}
    for kind in ("std", "mon"):
        for p in S.PW:
            for a in S.ALPHAS:
                h0, h1 = Sc[f"pc_{p}"] <= 0.6, 1 - Sc[f"pc_{p}"] <= 0.6
                sets[(kind, p, a, 0)], sets[(kind, p, a, 1)] = h0, h1
    meas = [S._meas({"et": 2.0, "snfh": 5.0, "necrosis": 1.0, "cavity": 0.0},
                    [({"et": 1.0, "snfh": 6.0, "necrosis": 1.0, "cavity": 0.0}, 60.0),
                     ({"et": 0.5, "snfh": 7.0, "necrosis": 2.0, "cavity": 0.0}, 30.0)], "test")] * n
    c = {"cohort": "mu", "pop": "grade4", "d": d, "scan_id": d.scan_id.to_numpy(), "patient_id": d.patient_id.to_numpy(),
         "y": y, "S": Sc, "sets": sets, "ood": [[[] if i % 2 else ["MGMT status unknown"] for i in range(n)]] * R_,
         "fold": np.zeros((R_, n), int), "card_phase": np.array(["later_post_rt", "early_post_rt"] * (n // 2)),
         "enh": np.array(["et_not_increased", "et_increased"] * (n // 2)), "comp_phase": d.phase.to_numpy(),
         "own": "mu", "eval": {"intended_use": ~np.isnan(y)}, "median_set": ~np.isnan(y), "meas": meas}
    return S.derive(c, TABLE)


class Records(unittest.TestCase):
    def setUp(self):
        self.c = cohort()
        self.recs = [S._clean(S.build_record(self.c, i, TABLE, None)) for i in range(len(self.c["scan_id"]))]

    def test_schema(self):
        for r in self.recs:
            self.assertEqual(set(r), TOP)
            self.assertEqual(r["schema"], S.SCHEMA)
            self.assertEqual(set(r["scores"]), set(S.PW))
            for a in S.ALPHAS:
                self.assertEqual(set(r["conformal"][f"alpha_{a}"]), set(S.PW))
                self.assertTrue(all(v in ("{0}", "{1}", "{0, 1}", "{}") for v in r["conformal"][f"alpha_{a}"].values()))
            self.assertEqual(set(r["flags"]), {"pathways_disagree", "out_of_range", "out_of_range_reasons", "tier_flag",
                                               "tier", "conformal_uncertain", "any_flag"})
            self.assertIn(r["card"]["tier"], R.TIERS)
            json.dumps(r, allow_nan=False)  # strict JSON: no NaN

    def test_no_label(self):
        for r in self.recs:
            S.assert_no_label(r)
            text = json.dumps(r)
            for k in S.LABEL_KEYS:
                self.assertNotIn(f'"{k}"', text)
        with self.assertRaises(AssertionError):
            S.assert_no_label({"a": {"label": 1}})
        with self.assertRaises(AssertionError):
            S.assert_no_label({"a": [{"rating": "PD"}]})

    def test_records_do_not_depend_on_labels(self):
        c2 = cohort()
        c2["y"] = 1 - np.nan_to_num(c2["y"])
        c2["d"]["label_120"] = c2["y"]
        a = [S._clean(S.build_record(self.c, i, TABLE, None)) for i in range(6)]
        b = [S._clean(S.build_record(c2, i, TABLE, None)) for i in range(6)]
        self.assertEqual(a, b)

    def test_flags(self):
        r0, r1 = self.recs[0], self.recs[1]
        self.assertTrue(r0["flags"]["out_of_range"])
        self.assertFalse(r1["flags"]["out_of_range"])
        self.assertEqual(r0["flags"]["tier"], "tested")
        self.assertFalse(r0["flags"]["tier_flag"])
        self.assertEqual(r1["flags"]["tier"], "few cases")
        self.assertTrue(r1["flags"]["tier_flag"])
        for r in self.recs:
            f = r["flags"]
            self.assertEqual(f["any_flag"], f["pathways_disagree"] or f["out_of_range"] or f["tier_flag"]
                             or f["conformal_uncertain"])
            self.assertEqual(f["conformal_uncertain"], r["conformal"]["alpha_0.2"]["combined"] == "{0, 1}")
            self.assertEqual(f["pathways_disagree"], not r["card"]["agreement"]["agree"])

    def test_measurements(self):
        m = self.recs[0]["measurements"]
        self.assertEqual(m["change_from_previous_cc"]["et"], 1.5)       # 2.0 - 0.5 (last earlier scan)
        self.assertEqual(m["earlier_minimum_cc"]["et"], 0.5)
        self.assertEqual(m["earlier_minimum_cc"]["snfh"], 6.0)
        self.assertEqual(m["change_from_earlier_minimum_cc"]["snfh"], -1.0)
        none = S._meas({"et": 1.0}, [], "x")
        self.assertIsNone(none["previous"])
        self.assertIsNone(none["change_from_earlier_minimum_cc"])


class Evaluation(unittest.TestCase):
    def test_auc_and_matched(self):
        y = np.array([1, 1, 0, 0])
        P = np.array([[0.9, 0.8, 0.1, 0.2]])
        self.assertEqual(S.auc_m(y, P, np.ones_like(P, bool)), 1.0)
        rng = np.random.default_rng(0)
        keep = np.array([True, False, True, True])
        ph = np.array(["a", "a", "b", "b"])
        m = S.matched(rng, keep, ph)
        self.assertEqual(m[ph == "a"].sum(), 1)
        self.assertEqual(m[ph == "b"].sum(), 2)


if __name__ == "__main__":
    unittest.main()
