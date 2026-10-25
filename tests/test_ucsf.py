"""UCSF-ALPTDG loader: sign conventions, date artefacts, surgeries before scan 1 and label candidates (synthetic)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from prism.data import ucsf

#        id   dx_s1  s1_s2 death   prog    rt     chemo  nsx  sx2    sx3   tx1  tx2
ROWS = [("1", 400.0, 60.0, -500.0, 65.0, -370.0, 370.0, 2, 300.0, np.nan, "c", "c"),     # progression at scan 2
        ("2", 300.0, 60.0, np.nan, 400.0, -260.0, 260.0, 3, -400.0, -500.0, "n", "n"),   # negatives verified
        ("3", 41_000.0, 60.0, 43_500.0, -0.4, -100.0, 100.0, 1, np.nan, np.nan, "c", "c"),  # artefacts; prog at s1
        ("4", 200.0, 50.0, np.nan, np.nan, 30.0, np.nan, 1, np.nan, np.nan, "n", "rt"),  # RT after scan 1, no prog
        ("5", 900.0, 70.0, np.nan, -3600.0, -800.0, 800.0, 1, np.nan, np.nan, "n", "n")]  # prior progression


def workbook() -> dict[str, pd.DataFrame]:
    clin = pd.DataFrame(np.nan, index=range(len(ROWS)), columns=ucsf.CLINICAL, dtype=object)
    for i, (sid, dx, s2, death, prog, rt, chemo, nsx, sx2, sx3, tx1, tx2) in enumerate(ROWS):
        clin.loc[i, ["subject_id", "dx_to_s1", "s1_to_s2", "death_raw", "prog_raw", "rt_raw", "chemo_raw",
                     "n_surgeries_total", "sx2_raw", "sx3_raw", "on_tx_1", "on_tx_2"]] = \
            [sid, dx, s2, death, prog, rt, chemo, nsx, sx2, sx3, tx1, tx2]
    clin["who2021"], clin["grade"], clin["idh_raw"], clin["mgmt_raw"] = "Glioblastoma", 4, "WT", "positive"
    clin["chemo_type"] = pd.Series("TMZ", index=clin.index).where(clin.chemo_raw.notna())
    vol = pd.DataFrame([(sid, tp, "Male", 60) for sid, *_ in ROWS for tp in (1, 2)],
                       columns=["subject_id", "timepoint", "sex", "age"])
    vol["et_change"] = pd.Series("Increased", index=vol.index).where(vol.timepoint.eq(2))
    for c in ("snfh_change", "snfh_inc_mm3", "snfh_dec_mm3", "snfh_overall_mm3", "et_inc_mm3", "et_dec_mm3",
              "et_overall_mm3"):
        vol[c] = np.nan
    split = pd.DataFrame({"subject_id": [r[0] for r in ROWS], "split": "TRAIN"})
    return {"clinical": clin, "volumes": vol, "split": split, "pdgm": pd.DataFrame({"subject_id": ["1"], "pdgm_id": ["P"]})}


class Ucsf(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        s, cls.flags = ucsf.build_scans(workbook())
        cls.s = s.set_index("scan_id")

    def test_signs(self):
        s = self.s
        self.assertEqual(s.loc["1_time1", "days_from_diagnosis_to_mri"], 400)
        self.assertEqual(s.loc["1_time2", "days_from_rt_start_to_mri"], 430)     # RT 370 d before scan 1
        self.assertEqual(s.loc["1_time1", "days_from_chemo_start_to_mri"], 370)
        self.assertEqual(s.loc["1_time2", "days_to_progression"], 5)
        self.assertEqual(s.loc["1_time1", "days_to_death"], 500)
        self.assertEqual(s.loc["4_time1", "rt_started"], 0)                        # RT 30 d after scan 1
        self.assertEqual(s.loc["4_time2", "rt_phase"], "during_rt")

    def test_artefacts(self):
        s = self.s
        self.assertTrue(np.isnan(s.loc["3_time1", "days_from_diagnosis_to_mri"]))
        self.assertFalse(s.loc["3_time1", "death_listed"])
        self.assertEqual(set(self.flags[self.flags.subject_id == "3"].flag),
                         {"surgery1_date_artefact", "death_date_artefact"})

    def test_surgeries_before_scan1(self):
        self.assertEqual(self.s.loc["1_time1", "n_surgeries_before_scan1"], 2)
        self.assertEqual(self.s.loc["2_time1", "n_surgeries_before_scan1"], 1)    # 2nd and 3rd after scan 1

    def test_labels(self):
        s = self.s
        self.assertEqual(s.loc["1_time2", "pos_s2_pm30"], 1)
        self.assertTrue(np.isnan(s.loc["1_time1", "pos_s2_pm30"]))                # progression within 120 d
        self.assertEqual(s.loc["2_time1", "neg_class"], "verified_by_later_progression")
        self.assertEqual(s.loc["2_time2", "neg_class"], "verified_by_later_progression")
        self.assertEqual(s.loc["3_time1", "pos_s1_at"], 1)
        self.assertEqual(s.loc["3_time2", "neg_class"], "not_negative")           # after the progression
        self.assertEqual(s.loc["4_time2", "neg_class"], "no_progression_follow_up_unknown")
        self.assertTrue(s.loc[["5_time1", "5_time2"], "label_excluded_prior_progression"].all())
        self.assertTrue(s.loc[["5_time1", "5_time2"], "neg_class"].eq("not_negative").all())
        self.assertEqual(s.loc["1_time2", "et_increased"], 1)
        self.assertTrue(np.isnan(s.loc["1_time1", "et_increased"]))

    def test_duplicated_et_header(self):
        cols = ["SubjectID", "Timepoint"] + [f"c{i}" for i in range(2, 23)] + ["SNFH_OverallChange_Volume"]
        cols[18] = "SNFH_OverallChange_Volume"
        row = list(range(24))
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "wb.xlsx"
            clin = pd.DataFrame([[1] + [0] * 21], columns=[f"k{i}" for i in range(22)])
            with pd.ExcelWriter(p) as w:
                pd.DataFrame([row], columns=cols).to_excel(w, sheet_name="UCSF-LPTDG", index=False)
                clin.to_excel(w, sheet_name="Clinical Info", index=False)
                pd.DataFrame({"a": [1], "b": ["TRAIN"]}).to_excel(w, sheet_name="TrainTestSplit", index=False)
                pd.DataFrame({"a": [1], "b": ["P"]}).to_excel(w, sheet_name="UCSF-PDGM Mapping", index=False)
            v = ucsf.read_workbook(p)["volumes"]
        self.assertEqual(v.snfh_overall_mm3[0], 18)
        self.assertEqual(v.et_overall_mm3[0], 23)


if __name__ == "__main__":
    unittest.main()
