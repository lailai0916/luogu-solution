"""Record or validate the hash-bound five-axis originality audit."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from gates import (
    checkpoint_independent_draft,
    record_originality_audit,
    require_originality_audit,
)
from luogu_client import LuoguError
from util import cache_dir, get_logger, pid_normalize


logger = get_logger()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pid")
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument(
        "--checkpoint",
        action="store_true",
        help="seal the independent statement, code, and full draft before public reference access",
    )
    action.add_argument("--report", type=Path, help="JSON object with one nonempty finding per axis")
    action.add_argument("--check", action="store_true", help="validate the current recorded audit")
    return parser


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv[1:])
    pid = pid_normalize(args.pid)
    problem_dir = cache_dir(pid)
    try:
        if args.checkpoint:
            path = checkpoint_independent_draft(pid, problem_dir)
            print(f"已记录参考前独立初稿检查点：{path}")
        elif args.report:
            findings = json.loads(args.report.expanduser().read_text(encoding="utf-8"))
            if not isinstance(findings, dict):
                raise ValueError("原创性审计报告必须是 JSON 对象。")
            path = record_originality_audit(pid, problem_dir, findings)
            print(f"已记录原创性审计：{path}")
        else:
            require_originality_audit(pid, problem_dir)
            print(f"{pid} 当前原创性审计有效。")
        return 0
    except (LuoguError, OSError, ValueError) as error:
        logger.error("原创性审计失败：%s", error)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
