"""Report v3.2: renamed facts and prompt, and the adapter to the frozen checker. Synthetic records only."""

import re
import unittest

from prism.analyses.checker_mutation import correct, records, to_v3_2
from prism.report import checker
from prism.report.facts_v3_1 import facts_v3_1
from prism.report.facts_v3_2 import back_claims, check_v3_2, facts_v3_2, new_key
from prism.report.prompts_v3_2 import system_prompt


class V32(unittest.TestCase):
    def test_no_old_names_and_same_numbers(self):
        for _, rec, _ in records():
            F1, F2 = facts_v3_1(rec), facts_v3_2(rec)
            self.assertFalse([k for k, v in F2.items() if re.search(r"timeline|pathway", f"{k} {v}", re.I)])
            self.assertFalse(re.search(r"timeline|pathway", system_prompt(F2), re.I))
            for k, v in F1.items():
                if not isinstance(v, str):
                    self.assertEqual(F2[new_key(k)], v)
                else:
                    self.assertEqual(checker.NUM.findall(F2[new_key(k)]), checker.NUM.findall(v))

    def test_adapter_agrees_with_frozen_checker(self):
        for _, rec, is_lum in records():
            F1 = facts_v3_1(rec)
            C = correct(F1, is_lum)
            self.assertTrue(checker.check(C, F1, card=True)["pass"])
            self.assertTrue(check_v3_2(to_v3_2(C), rec)["pass"])

    def test_side_rule_still_applies(self):
        rec = next(r for _, r, _ in records())
        F2 = facts_v3_2(rec)
        side = F2["model.imaging.side"]
        wrong = "below" if side == "above" else "above"
        bad = [{"text": f"The imaging model score is {wrong} its median.", "fields": ["model.imaging.side"]}]
        self.assertIn("image model", back_claims(bad, facts_v3_1(rec))[0]["text"])
        r = check_v3_2(bad, rec)
        self.assertFalse(r["pass"])
        self.assertTrue(r["agreement"]["side_wrong"])


if __name__ == "__main__":
    unittest.main()
