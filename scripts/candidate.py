"""Check whether a problem may enter the new-solution workflow."""
from __future__ import annotations

import json
import sys
from typing import Any, Optional

from luogu_client import LoginExpiredError, LuoguClient, LuoguError
from util import get_logger, pid_normalize

logger = get_logger()

MIN_DIFFICULTY = 7
MAX_EXISTING_SOLUTIONS = 3
SEVERE_MIN_DIFFICULTY = 5
SEVERE_MAX_EXISTING_SOLUTIONS = 5


def classify_violation(
    *,
    difficulty: int,
    existing_solutions: int,
    has_prior_own_solution: bool,
    accepts_solution: bool,
) -> dict[str, Any]:
    """Classify one current or reconstructed candidate snapshot."""
    if type(difficulty) is not int:
        raise ValueError("题目难度必须是整数。")
    if type(existing_solutions) is not int or existing_solutions < 0:
        raise ValueError("题解数量必须是非负整数。")

    ordinary: list[str] = []
    severe: list[str] = []

    if difficulty < MIN_DIFFICULTY:
        ordinary.append("difficulty_below_ordinary_minimum")
    if existing_solutions > MAX_EXISTING_SOLUTIONS:
        ordinary.append("solution_count_above_ordinary_limit")
    if difficulty < SEVERE_MIN_DIFFICULTY:
        severe.append("difficulty_below_severe_minimum")
    if existing_solutions > SEVERE_MAX_EXISTING_SOLUTIONS:
        severe.append("solution_count_above_severe_limit")
    if has_prior_own_solution:
        severe.append("prior_own_solution")
    if not accepts_solution:
        severe.append("solution_channel_closed")

    level = "severe" if severe else "ordinary" if ordinary else "compliant"
    return {
        "level": level,
        "ordinaryReasons": ordinary,
        "severeReasons": severe,
    }


def check_candidate(pid: str, client: Optional[LuoguClient] = None) -> dict[str, Any]:
    pid = pid_normalize(pid)
    client = client or LuoguClient()
    problem = client.get_problem(pid)
    if problem.get("type") != "P":
        raise LuoguError(f"{pid} 不是主题库题目，禁止新写题解。")
    difficulty = problem.get("difficulty")
    if type(difficulty) is not int:
        raise LuoguError(f"{pid} 尚无难度，禁止新写题解。")
    if difficulty < MIN_DIFFICULTY:
        raise LuoguError(f"{pid} 难度 {difficulty} 低于下限 {MIN_DIFFICULTY}，禁止新写题解。")
    if problem.get("acceptSolution") is not True:
        raise LuoguError(f"{pid} 当前不接受新题解。")
    count = client.get_solution_count(pid)
    if count > MAX_EXISTING_SOLUTIONS:
        raise LuoguError(
            f"{pid} 已有 {count} 篇题解，超过上限 {MAX_EXISTING_SOLUTIONS}，禁止新写题解。"
        )
    if not client.check_login().get("logged_in"):
        raise LoginExpiredError("无法核对当前账号的历史题解；禁止新写题解。")
    own_articles = client.find_my_solution_articles(pid)
    if own_articles:
        raise LuoguError(f"当前账号已经写过 {pid} 题解，禁止重复新写。")
    return {
        "pid": pid,
        "title": problem.get("title"),
        "difficulty": difficulty,
        "minDifficulty": MIN_DIFFICULTY,
        "existingSolutions": count,
        "maxExistingSolutions": MAX_EXISTING_SOLUTIONS,
        "existingOwnSolutions": len(own_articles),
        "eligible": True,
    }


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("用法: python3 scripts/candidate.py P1001", file=sys.stderr)
        return 2
    try:
        print(json.dumps(check_candidate(argv[1]), ensure_ascii=False, indent=2))
        return 0
    except LoginExpiredError as error:
        logger.error("登录失效：%s", error)
        return 3
    except (LuoguError, ValueError) as error:
        logger.error("候选不合格：%s", error)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
