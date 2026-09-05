from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from verify import (  # noqa: E402
    VerifyResult,
    _float_tolerance,
    _outputs_match,
    _run_grader,
    _run_interactor,
    _run_sample_checker,
    record_verification,
)


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

    def test_declared_float_tolerance_preserves_text_labels(self) -> None:
        self.assertTrue(
            _outputs_match(
                "Case #1: 3.2387415020\nCase #2: 4.0000000000",
                "Case #1: 3.23874149472\nCase #2: 4.0",
                1e-4,
            )
        )
        self.assertFalse(_outputs_match("Case #2: 3.0", "Case #1: 3.0", 1e-4))

    def test_problem_sample_checker_validates_non_unique_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            checker = root / "sample_checker.py"
            checker.write_text(
                "import pathlib,sys\n"
                "actual=pathlib.Path(sys.argv[2]).read_text().strip()\n"
                "raise SystemExit(0 if actual=='valid' else 1)\n",
                encoding="utf-8",
            )
            ok, _ = _run_sample_checker(checker, "input\n", "valid\n", "example\n", 5)
            self.assertTrue(ok)
            ok, _ = _run_sample_checker(checker, "input\n", "invalid\n", "example\n", 5)
            self.assertFalse(ok)

    def test_problem_interactor_drives_compiled_program(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            binary = root / "solution"
            binary.write_text("", encoding="utf-8")
            interactor = root / "interactor.py"
            interactor.write_text(
                "import pathlib,sys\n"
                "path=pathlib.Path(sys.argv[1])\n"
                "print('interactive pass')\n"
                "raise SystemExit(0 if path.exists() else 1)\n",
                encoding="utf-8",
            )
            ok, detail = _run_interactor(interactor, binary, 5)
            self.assertTrue(ok)
            self.assertEqual(detail, "interactive pass")

    def test_problem_grader_runs_linked_simulation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            binary = Path(directory) / "grader"
            binary.write_text("#!/bin/sh\necho communication-pass\n", encoding="utf-8")
            binary.chmod(0o755)
            ok, detail = _run_grader(binary, 5)
            self.assertTrue(ok)
            self.assertEqual(detail, "communication-pass")

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
            self.assertIn('"version": 4', text)


if __name__ == "__main__":
    unittest.main()
