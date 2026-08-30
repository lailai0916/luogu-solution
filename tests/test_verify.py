from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from verify import _float_tolerance, _outputs_match  # noqa: E402


class VerifyOutputTest(unittest.TestCase):
    def test_exact_output_remains_exact_without_tolerance(self) -> None:
        self.assertTrue(_outputs_match("1\n2", "1\n2", None))
        self.assertFalse(_outputs_match("1.0", "1", None))

    def test_declared_float_tolerance_accepts_equivalent_formatting(self) -> None:
        problem = {
            "outputFormat": "absolute or relative error at most $10^{-6}$.",
        }
        tolerance = _float_tolerance(problem)
        self.assertEqual(tolerance, 1e-6)
        self.assertTrue(_outputs_match("1.0000000000\n2.3000000000", "1\n2.3", tolerance))
        self.assertFalse(_outputs_match("1\n2.31", "1\n2.3", tolerance))


if __name__ == "__main__":
    unittest.main()
