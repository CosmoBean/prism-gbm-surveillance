from pathlib import Path
import subprocess
import sys
import unittest


class ClinicalFigureDraftTest(unittest.TestCase):
    def test_generator_writes_reviewable_figure_one_draft(self):
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as directory:
            output = Path(directory)
            result = subprocess.run(
                [sys.executable, "scripts/generate_clinical_figure_drafts.py", "--output-dir", str(output)],
                text=True,
                capture_output=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            for suffix in (".pdf", ".png"):
                asset = output / f"fig1_clinical_v2{suffix}"
                self.assertTrue(asset.is_file())
                self.assertGreater(asset.stat().st_size, 0)


if __name__ == "__main__":
    unittest.main()
