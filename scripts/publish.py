"""Preview, compare, create, update, and optionally request review for a Luogu solution article."""
from __future__ import annotations

import argparse
import difflib
import json
import sys
from pathlib import Path
from typing import Any

from luogu_client import LoginExpiredError, LuoguClient, LuoguError
from lint import lint_text
from util import (
    cache_dir,
    classify,
    config_home,
    get_logger,
    load_config,
    normalize_transport,
    parse_markdown,
    pid_normalize,
    publishable_body,
)

logger = get_logger()


def _metadata_path(pid: str) -> Path:
    return cache_dir(pid) / "article.json"


def _load_metadata(pid: str) -> dict[str, Any]:
    path = _metadata_path(pid)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def _save_metadata(pid: str, article: dict[str, Any]) -> None:
    path = _metadata_path(pid)
    data = {
        "pid": pid,
        "lid": str(article.get("lid") or ""),
        "title": article.get("title") or "",
        "url": article.get("url") or "",
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _problem_title(pid: str) -> str:
    path = cache_dir(pid) / "raw" / "problem.json"
    if path.exists():
        try:
            problem = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(problem, dict) and problem.get("title"):
                return f"题解：{pid} {problem['title']}"
        except (ValueError, OSError):
            pass
    return f"题解：{pid}"


def load_source(value: str, *, lid: str | None = None, title: str | None = None) -> dict[str, Any]:
    candidate = Path(value).expanduser()
    if candidate.suffix.lower() in {".md", ".mdx"} or candidate.exists() or "/" in value:
        path = candidate.resolve()
        pid = pid_normalize(path.stem)
    else:
        pid = pid_normalize(value)
        path = cache_dir(pid) / "solution.md"
    if not path.exists():
        raise FileNotFoundError(f"题解源文件不存在：{path}")

    raw = path.read_text(encoding="utf-8")
    lint_issues = lint_text(raw)
    if lint_issues:
        raise ValueError("题解结构检查失败：" + "；".join(lint_issues))
    parsed = parse_markdown(raw)
    frontmatter = parsed["frontmatter"]
    metadata = _load_metadata(pid)
    content = publishable_body(raw)
    if not content.strip():
        raise ValueError("题解正文为空")
    return {
        "pid": pid,
        "path": path,
        "lid": lid or frontmatter.get("lid") or metadata.get("lid") or None,
        "title": title or frontmatter.get("title") or metadata.get("title") or _problem_title(pid),
        "title_override": title is not None,
        "content": content,
    }


def _with_disclosure(source: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    source = dict(source)
    if args.eligibility == "agent-generated":
        raise ValueError("Agent 生成了关键思路、论证或代码：按当前洛谷规则不得执行真实发布或投稿。")
    if args.eligibility == "editorial-ai":
        if not args.disclosure_file:
            raise ValueError("editorial-ai 必须提供 --disclosure-file，且内容须准确说明允许范围内的贡献。")
        disclosure_path = Path(args.disclosure_file).expanduser().resolve()
        disclosure = normalize_transport(disclosure_path.read_text(encoding="utf-8"))
        if not disclosure:
            raise ValueError("披露文件为空")
        source["content"] = normalize_transport(source["content"]) + "\n\n" + disclosure + "\n"
    return source


def preview(source: dict[str, Any]) -> None:
    print("=== 本地预览（未联网、未发布）===")
    print(f"题号: {source['pid']}")
    print(f"源文件: {source['path']}")
    print(f"lid: {source['lid'] or '未绑定，将在允许的 live 新建后记录'}")
    print(f"标题: {source['title']}")
    print(f"正文字数: {len(source['content'])}")
    print("---- 正文前 600 字 ----")
    print(source["content"][:600])


def diff_only(source: dict[str, Any]) -> int:
    if not source["lid"]:
        logger.error("没有 lid，线上尚无可比较的文章。")
        return 2
    article = LuoguClient().get_article(str(source["lid"]))
    actual = article.get("content") or ""
    result = classify(source["content"], actual)
    print(f"=== 只读 diff {source['pid']} lid={source['lid']}：{result} ===")
    print(f"contentFull: {article.get('contentFull')}")
    if result != "identical":
        diff = difflib.unified_diff(
            normalize_transport(actual).split("\n"),
            normalize_transport(source["content"]).split("\n"),
            fromfile=f"luogu/{source['pid']}",
            tofile=f"local/{source['pid']}",
            lineterm="",
        )
        print("\n".join(list(diff)[:300]))
    return 0


def _article_lid(article: dict[str, Any]) -> str:
    lid = article.get("lid") or article.get("id")
    if lid is None and isinstance(article.get("article"), dict):
        lid = article["article"].get("lid") or article["article"].get("id")
    if lid is None:
        raise LuoguError("发布返回中缺少文章 lid，停止后续操作。")
    return str(lid)


def publish_live(source: dict[str, Any], *, submit_review: bool, policy_checked: bool) -> int:
    client = LuoguClient()
    if not client.check_login().get("logged_in"):
        raise LoginExpiredError("未登录或 Cookie 失效，请更新 Cookie 后重试。")

    config = load_config()["luogu"]["article"]
    current: dict[str, Any] | None = None
    if source["lid"]:
        current = client.get_article(str(source["lid"]))
    payload = {
        "title": source["title"] if source["title_override"] else (current or {}).get("title") or source["title"],
        "category": (current or {}).get("category") or config.get("category", 2),
        "content": source["content"],
        "solutionFor": source["pid"],
        "status": (current or {}).get("status") or config.get("status", 2),
        "top": (current or {}).get("top") if (current or {}).get("top") is not None else config.get("top", 0),
    }

    if source["lid"]:
        client.update_article(str(source["lid"]), payload)
        lid = str(source["lid"])
        logger.info("文章更新成功 %s -> lid=%s", source["pid"], lid)
    else:
        created = client.create_article(payload)
        lid = _article_lid(created)
        logger.info("文章新建成功 %s -> lid=%s", source["pid"], lid)

    read_back = client.get_article(lid)
    result = classify(source["content"], read_back.get("content") or "")
    print(f"=== 发布并回读 {source['pid']} lid={lid}：{result} ===")
    if read_back.get("contentFull") is False or result == "substantive":
        logger.error("回读不完整或存在实质差异；停止投稿审核。")
        return 1
    read_back["lid"] = lid
    _save_metadata(source["pid"], read_back)

    if submit_review:
        if not policy_checked:
            raise ValueError("投稿审核前必须重新核验官方规则，并传入 --confirm-current-policy。")
        client.request_solution_review(lid)
        print(f"=== 已提交题解审核请求 {source['pid']} lid={lid} ===")
    return 0


def check_login() -> int:
    status = LuoguClient().check_login()
    if status.get("logged_in"):
        print("已登录，Cookie 有效。")
        return 0
    print(f"未登录 / Cookie 失效：{status.get('message')}")
    print(f"请将整段 Cookie 存到 {config_home() / 'cookie.txt'}，并设置权限为 0600。")
    return 3


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", nargs="?", help="PID or Markdown/MDX path")
    parser.add_argument("--check", action="store_true", help="check login without publishing")
    parser.add_argument("--diff", action="store_true", help="read-only comparison with bound article")
    parser.add_argument("--live", action="store_true", help="create or update the article")
    parser.add_argument("--submit-review", action="store_true", help="request solution review after live publish")
    parser.add_argument("--confirm-current-policy", action="store_true", help="confirm official rules were rechecked")
    parser.add_argument("--lid", help="existing article ID")
    parser.add_argument("--title", help="article title override")
    parser.add_argument(
        "--eligibility",
        choices=("human-authored", "editorial-ai", "agent-generated"),
        help="truthful content-origin classification required for live writes",
    )
    parser.add_argument("--disclosure-file", help="required disclosure for editorial-ai")
    return parser


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv[1:])
    if args.check:
        return check_login()
    if not args.source:
        build_parser().print_usage(sys.stderr)
        return 2
    if args.submit_review and not args.live:
        logger.error("--submit-review 必须与 --live 同时使用。")
        return 2
    try:
        source = load_source(args.source, lid=args.lid, title=args.title)
        if args.live:
            if not args.eligibility:
                raise ValueError("真实发布必须声明 --eligibility。")
            source = _with_disclosure(source, args)
            return publish_live(
                source,
                submit_review=args.submit_review,
                policy_checked=args.confirm_current_policy,
            )
        if args.diff:
            return diff_only(source)
        preview(source)
        return 0
    except LoginExpiredError as error:
        logger.error("登录失效：%s", error)
        return 3
    except (LuoguError, FileNotFoundError, KeyError, OSError, ValueError) as error:
        logger.error("失败：%s", error)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
