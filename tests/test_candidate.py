from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import Mock

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from candidate import (  # noqa: E402
    MAX_EXISTING_SOLUTIONS,
    MIN_DIFFICULTY,
    SEVERE_MAX_EXISTING_SOLUTIONS,
    SEVERE_MIN_DIFFICULTY,
    check_candidate,
    classify_violation,
)


class CandidatePolicyTest(unittest.TestCase):
    def setUp(self) -> None:
        self.client = Mock()
        self.client.get_problem.return_value = {
            "pid": "P1001",
            "title": "A+B Problem",
            "type": "P",
            "difficulty": 7,
            "acceptSolution": True,
        }
        self.client.check_login.return_value = {"logged_in": True}
        self.client.find_my_solution_articles.return_value = []

    def test_three_existing_solutions_and_no_own_article_is_eligible(self) -> None:
        self.client.get_solution_count.return_value = 3
        result = check_candidate("P1001", self.client)
        self.assertTrue(result["eligible"])
        self.assertEqual(result["difficulty"], 7)
        self.assertEqual(result["existingSolutions"], 3)

    def test_difficulty_below_purple_is_blocked_before_reference_reads(self) -> None:
        self.client.get_problem.return_value["difficulty"] = 6
        with self.assertRaisesRegex(Exception, "难度 6 低于下限 7"):
            check_candidate("P1001", self.client)
        self.client.get_solution_count.assert_not_called()

    def test_four_existing_solutions_is_blocked(self) -> None:
        self.client.get_solution_count.return_value = 4
        with self.assertRaisesRegex(Exception, "超过上限 3"):
            check_candidate("P1001", self.client)
        self.client.find_my_solution_articles.assert_not_called()

    def test_existing_own_solution_is_blocked(self) -> None:
        self.client.get_solution_count.return_value = 2
        self.client.find_my_solution_articles.return_value = [{"lid": "abcdefgh"}]
        with self.assertRaisesRegex(Exception, "已经写过 P1001"):
            check_candidate("P1001", self.client)

    def test_history_check_fails_closed_without_login(self) -> None:
        self.client.get_solution_count.return_value = 0
        self.client.check_login.return_value = {"logged_in": False}
        with self.assertRaisesRegex(Exception, "无法核对当前账号"):
            check_candidate("P1001", self.client)

    def test_violation_classification_uses_severe_override(self) -> None:
        purple = classify_violation(
            difficulty=7,
            existing_solutions=3,
            has_prior_own_solution=False,
            accepts_solution=True,
        )
        self.assertEqual(purple["level"], "compliant")

        blue = classify_violation(
            difficulty=6,
            existing_solutions=3,
            has_prior_own_solution=False,
            accepts_solution=True,
        )
        self.assertEqual(blue["level"], "ordinary")
        self.assertEqual(
            blue["ordinaryReasons"],
            ["difficulty_below_ordinary_minimum"],
        )
        self.assertEqual(blue["severeReasons"], [])

        cyan = classify_violation(
            difficulty=5,
            existing_solutions=3,
            has_prior_own_solution=False,
            accepts_solution=True,
        )
        self.assertEqual(cyan["level"], "ordinary")
        self.assertEqual(
            cyan["ordinaryReasons"],
            ["difficulty_below_ordinary_minimum"],
        )
        self.assertEqual(cyan["severeReasons"], [])

        severe = classify_violation(
            difficulty=4,
            existing_solutions=6,
            has_prior_own_solution=True,
            accepts_solution=False,
        )
        self.assertEqual(severe["level"], "severe")
        self.assertEqual(
            severe["severeReasons"],
            [
                "difficulty_below_severe_minimum",
                "solution_count_above_severe_limit",
                "prior_own_solution",
                "solution_channel_closed",
            ],
        )

    def test_hard_thresholds_are_not_runtime_configuration(self) -> None:
        self.assertEqual(MIN_DIFFICULTY, 7)
        self.assertEqual(MAX_EXISTING_SOLUTIONS, 3)
        self.assertEqual(SEVERE_MIN_DIFFICULTY, 5)
        self.assertEqual(SEVERE_MAX_EXISTING_SOLUTIONS, 5)


if __name__ == "__main__":
    unittest.main()
