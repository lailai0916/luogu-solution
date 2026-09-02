"""Fetch the authoritative statement, then optionally unlock reference solutions.

用法：
    python fetch.py P1001
    python fetch.py P1001 --references

产出：
    ~/.cache/luogu/P1001/problem.md       题面（一级标题）
    ~/.cache/luogu/P1001/references.md     完成独立初稿后才抓取的非可信参考材料
    ~/.cache/luogu/P1001/raw/problem.json
    ~/.cache/luogu/P1001/raw/solutions.json
    ~/.cache/luogu/P1001/raw/independent.json  参考前代码与初稿的哈希检查点
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from gates import checkpoint_independent_draft
from util import cache_dir, load_config, get_logger, pid_normalize, config_home, load_cookie
from luogu_client import LuoguClient, LuoguError, LoginExpiredError

logger = get_logger()


def _section(title: str, body: Any) -> str:
    if body is None:
        return ""
    text = str(body).strip()
    return f"## {title}\n\n{text}\n\n" if text else ""


def render_problem_md(problem: dict[str, Any], pid: str, url: str) -> str:
    parts: list[str] = [f"# {problem.get('title') or pid}（{pid}）\n\n", f"> 题目链接：{url}\n\n"]
    limits = problem.get("limits") or {}
    if isinstance(limits, dict) and limits:
        bits = []
        if limits.get("time"):
            t = limits["time"][0] if isinstance(limits["time"], list) else limits["time"]
            bits.append(f"时间限制 {t} ms")
        if limits.get("memory"):
            m = limits["memory"][0] if isinstance(limits["memory"], list) else limits["memory"]
            bits.append(f"内存限制 {m} KB")
        if bits:
            parts.append("> " + " / ".join(bits) + "\n\n")
    parts.append(_section("题目背景", problem.get("background")))
    parts.append(_section("题目描述", problem.get("description")))
    parts.append(_section("输入格式", problem.get("inputFormat")))
    parts.append(_section("输出格式", problem.get("outputFormat")))
    samples = problem.get("samples") or []
    if samples:
        parts.append("## 输入输出样例\n\n")
        for i, s in enumerate(samples, 1):
            inp, out = (s[0], s[1]) if isinstance(s, (list, tuple)) and len(s) >= 2 else \
                (s.get("input", ""), s.get("output", "")) if isinstance(s, dict) else (None, None)
            if inp is None:
                continue
            parts.append(f"### 样例 #{i}\n\n输入：\n\n```\n{str(inp).rstrip()}\n```\n\n输出：\n\n```\n{str(out).rstrip()}\n```\n\n")
    parts.append(_section("说明 / 提示", problem.get("hint")))
    if problem.get("translation"):
        parts.append(_section("题目翻译", problem["translation"]))
    return "".join(p for p in parts if p)


def render_references_md(solutions: list[dict[str, Any]], pid: str) -> str:
    """Render untrusted material for post-draft adversarial review only."""
    if not solutions:
        return f"# 参考题解（{pid}）\n\n（未抓取到可访问的参考题解。）\n"
    parts = [
        f"<!-- {pid} 的参考题解只用于独立初稿后的纠错。禁止复用其表述、结构、"
        "符号体系、变量组、函数拆分或代码。 -->\n\n"
    ]
    for i, s in enumerate(solutions, 1):
        parts.append(f"# 题解 #{i}\n\n")
        parts.append(f"- 标题: {s.get('title', '')}\n- 作者: {s.get('author', '')}\n")
        parts.append(f"- 链接: {s.get('url', '')}\n- 赞数: {s.get('upvote', 0)}\n\n")
        content = (s.get("content") or "").strip()
        parts.append(content + "\n\n" if content else "（无正文）\n\n")
    return "".join(parts)


def fetch_statement(pid: str, client: LuoguClient | None = None) -> Path:
    pid = pid_normalize(pid)
    base = load_config()["luogu"]["base_url"].rstrip("/")
    url = f"{base}/problem/{pid}"
    out_dir = cache_dir(pid)
    raw_dir = out_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    client = client or LuoguClient()

    logger.info("抓取题面 %s ...", pid)
    problem = client.get_problem(pid)
    (raw_dir / "problem.json").write_text(json.dumps(problem, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "problem.md").write_text(render_problem_md(problem, pid, url), encoding="utf-8")
    logger.info("完成题面 %s -> %s", pid, out_dir)
    return out_dir


def fetch_references(pid: str, client: LuoguClient | None = None) -> Path:
    pid = pid_normalize(pid)
    out_dir = cache_dir(pid)
    raw_dir = out_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_independent_draft(pid, out_dir)
    provided_client = client is not None
    client = client or LuoguClient()

    solutions: list[dict[str, Any]] = []
    if provided_client or load_cookie():
        logger.info("抓取可访问题解列表 %s ...", pid)
        try:
            solutions = client.get_all_solutions(pid)
        except LoginExpiredError as e:
            logger.warning("Cookie 失效：%s（跳过参考题解，仅保存题面）", e)
    else:
        logger.info("未配置 Cookie：跳过参考题解，仅保存题面。")
    (raw_dir / "solutions.json").write_text(json.dumps(solutions, ensure_ascii=False, indent=2), encoding="utf-8")

    (out_dir / "references.md").write_text(render_references_md(solutions, pid), encoding="utf-8")
    logger.info("完成参考复核材料 %s：题解 %d 篇 -> %s", pid, len(solutions), out_dir)
    return out_dir


def fetch(pid: str) -> Path:
    """Backward-compatible statement-only entrypoint."""
    return fetch_statement(pid)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pid")
    parser.add_argument(
        "--references",
        action="store_true",
        help="fetch existing solutions only after independent solution.cpp and solution.md exist",
    )
    return parser


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv[1:])
    try:
        if args.references:
            fetch_references(args.pid)
        else:
            fetch_statement(args.pid)
    except LoginExpiredError as e:
        logger.error("登录失效：%s", e)
        print(f"\nCookie 可能失效，请更新 {config_home() / 'cookie.txt'} 或环境变量 LUOGU_COOKIE。", file=sys.stderr)
        return 3
    except LuoguError as e:
        logger.error("抓取失败：%s", e)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
