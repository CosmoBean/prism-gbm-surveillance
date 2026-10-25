"""Segmentation figure: slice choice, display orientation and the no-later-scans rule (synthetic data only)."""

from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from prism.report.seg_figure import choose_slice, past_only, to_display


def comps(shape=(20, 20, 10)):
    return {c: np.zeros(shape, bool) for c in ("et", "netc", "rc", "snfh")}


class SliceChoice(unittest.TestCase):
    def setUp(self):
        self.brain = np.ones((20, 20, 10), bool)

    def test_largest_et_area(self):
        c = comps()
        c["et"][5:8, 5:8, 2] = True    # 9 voxels
        c["et"][2:6, 2:6, 7] = True    # 16 voxels: the largest ET section
        c["snfh"][:, :, 4] = True      # larger lesion elsewhere must not win while ET exists
        k, rule, area = choose_slice(c, self.brain)
        self.assertEqual((k, area), (7, 16.0))
        self.assertEqual(rule, "largest ET area")

    def test_no_et_falls_back_to_lesion_then_cavity_then_brain(self):
        c = comps()
        c["netc"][1:3, 1:3, 3] = True
        c["snfh"][0:5, 0:5, 6] = True
        c["rc"][:, :, 1] = True        # cavity is not lesion
        k, rule, _ = choose_slice(c, self.brain)
        self.assertEqual((k, rule), (6, "largest lesion (no ET)"))
        c = comps()
        c["rc"][0:2, 0:2, 8] = True
        self.assertEqual(choose_slice(c, self.brain)[:2], (8, "largest cavity (no lesion)"))
        b = np.zeros((20, 20, 10), bool)
        b[:, :, 5] = True
        self.assertEqual(choose_slice(comps(), b)[:2], (5, "largest brain section"))

    def test_ties_take_the_lowest_index(self):
        c = comps()
        c["et"][0:2, 0:2, 3] = True
        c["et"][5:7, 5:7, 6] = True
        self.assertEqual(choose_slice(c, self.brain)[0], 3)


class Orientation(unittest.TestCase):
    def test_radiological_display(self):
        sl = np.zeros((4, 5))          # RAS slice: x (left -> right), y (posterior -> anterior)
        sl[3, 4] = 1                   # most right, most anterior voxel
        d = to_display(sl)
        self.assertEqual(d.shape, (5, 4))
        self.assertEqual(d[0, 0], 1)   # top row = anterior, left column = patient's right


class NoLaterScans(unittest.TestCase):
    def hist(self):
        return pd.DataFrame({"scan_id": ["s1", "s2", "s3", "s4"], "order": [10.0, 30.0, 20.0, 40.0],
                             "et_cc": [1.0, 2.0, 3.0, 4.0]})

    def test_drops_later_scans_and_orders(self):
        h = past_only(self.hist(), "s2")
        self.assertEqual(h.scan_id.tolist(), ["s1", "s3", "s2"])
        self.assertTrue((h.order <= 30).all())
        self.assertEqual(past_only(self.hist(), "s1").scan_id.tolist(), ["s1"])

    def test_current_scan_must_be_present_once(self):
        with self.assertRaises(AssertionError):
            past_only(self.hist(), "s9")
        dup = pd.concat([self.hist(), self.hist().iloc[[1]]])
        with self.assertRaises(AssertionError):
            past_only(dup, "s2")


if __name__ == "__main__":
    unittest.main()
