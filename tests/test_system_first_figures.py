from pathlib import Path
import subprocess
import sys
import unittest


class SystemFirstFigureTest(unittest.TestCase):
    def test_generator_writes_all_manuscript_assets(self):
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as directory:
            output = Path(directory)
            result = subprocess.run(
                [sys.executable, "scripts/generate_system_first_figures.py", "--output-dir", str(output)],
                text=True,
                capture_output=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            for name in ("fig1_system", "fig2_transport", "fig3_evidence", "fig4_confidence", "fig5_report"):
                self.assertTrue((output / f"{name}.pdf").is_file())
                self.assertTrue((output / f"{name}.png").is_file())
