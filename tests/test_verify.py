from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from verify import VerifyResult, _float_tolerance, _outputs_match, record_verification  # noqa: E402


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

    def test_verification_record_contains_hash_bound_pass_result(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            problem = root / "P1001"
            problem.mkdir()
            (problem / "problem.md").write_text("# A+B\n", encoding="utf-8")
            (problem / "solution.cpp").write_text("int main(){}\n", encoding="utf-8")
            result = VerifyResult()
            result.add("编译", True, "C++17")
            with patch("verify.cache_dir", return_value=problem):
                path = record_verification("P1001", result)
            text = path.read_text(encoding="utf-8")
            self.assertIn('"status": "pass"', text)
            self.assertIn('"sha256"', text)


if __name__ == "__main__":
    unittest.main()
