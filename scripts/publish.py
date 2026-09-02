"""Preview, compare, create, update, and optionally request review for a Luogu solution article."""
from __future__ import annotations

import argparse
import difflib
import json
import sys
from pathlib import Path
from typing import Any

from candidate import check_candidate
from gates import (
    require_article_code_matches_source,
    require_local_verification,
    require_matching_accepted_record,
    require_originality_audit,
)
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
    render_luogu_article,
)

logger = get_logger()
HIDDEN_ARTICLE_STATUS = 1
PUBLIC_ARTICLE_STATUS = 2
UNPUBLISHED_PROMOTE_STATUSES = {0, 3}


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
        "time": article.get("time"),
        "status": article.get("status"),
        "top": article.get("top"),
        "promoteStatus": article.get("promoteStatus"),
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
    body = publishable_body(raw)
    if not body.strip():
        raise ValueError("题解正文为空")
    content = render_luogu_article(pid, body)
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
    account_exception = getattr(args, "confirm_account_exception", False)
    if account_exception and args.eligibility != "agent-generated":
        raise ValueError("--confirm-account-exception 仅适用于 agent-generated。")
    if args.eligibility == "agent-generated" and not getattr(args, "confirm_account_exception", False):
        raise ValueError(
            "Agent 生成了关键思路、论证或代码：真实发布须有账号专项授权，"
            "并传入 --confirm-account-exception。"
        )
    if args.eligibility == "editorial-ai":
        if not args.disclosure_file:
            raise ValueError("editorial-ai 必须提供 --disclosure-file，且内容须准确说明允许范围内的贡献。")
    if args.eligibility == "human-authored" and args.disclosure_file:
        raise ValueError("human-authored 不应提供 --disclosure-file；请如实选择内容来源。")
    if args.disclosure_file:
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
    if not source.get("lid"):
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
    if submit_review and not policy_checked:
        raise ValueError("投稿审核前必须重新核验官方规则，并传入 --confirm-current-policy。")

    problem_dir = cache_dir(source["pid"])
    require_originality_audit(source["pid"], problem_dir)
    require_local_verification(source["pid"], problem_dir)
    require_article_code_matches_source(source["pid"], problem_dir, source["content"])
    client = LuoguClient()
    if not client.check_login().get("logged_in"):
        raise LoginExpiredError("未登录或 Cookie 失效，请更新 Cookie 后重试。")
    accepted_record: dict[str, Any] | None = None
    if submit_review:
        accepted_record = require_matching_accepted_record(
            source["pid"],
            cache_dir(source["pid"]),
            source["content"],
            client,
        )
    lid_bound = source.get("lid")
    if not lid_bound:
        check_candidate(source["pid"], client)
    elif submit_review:
        problem = client.get_problem(source["pid"])
        if problem.get("acceptSolution") is not True:
            raise LuoguError(f"{source['pid']} 当前不接受新题解；已在文章写入前停止。")

    config = load_config()["luogu"]["article"]
    current: dict[str, Any] | None = None
    if lid_bound:
        current = client.get_article(str(lid_bound))
        _require_bound_article(source["pid"], str(lid_bound), current)
    payload = {
        "title": source["title"] if source["title_override"] else (current or {}).get("title") or source["title"],
        "category": (current or {}).get("category") or config.get("category", 2),
        "content": source["content"],
        "solutionFor": source["pid"],
        "status": (current or {}).get("status") or config.get("status", 2),
        "top": 2,
    }

    if lid_bound:
        client.update_article(str(lid_bound), payload)
        lid = str(lid_bound)
        logger.info("文章更新成功 %s -> lid=%s", source["pid"], lid)
    else:
        created = client.create_article(payload)
        lid = _article_lid(created)
        logger.info("文章新建成功 %s -> lid=%s", source["pid"], lid)

    read_back = client.get_article(lid)
    result = classify(source["content"], read_back.get("content") or "")
    print(f"=== 发布并回读 {source['pid']} lid={lid}：{result} ===")
    if (
        read_back.get("contentFull") is False
        or result != "identical"
        or read_back.get("title") != payload["title"]
        or read_back.get("category") != payload["category"]
        or _solution_pid(read_back) != source["pid"]
        or read_back.get("status") != payload["status"]
        or read_back.get("top") != payload["top"]
    ):
        logger.error("回读正文、标题、分类、题号、公开度或置顶量不一致；停止投稿审核。")
        return 1
    read_back["lid"] = lid
    _save_metadata(source["pid"], read_back)

    if submit_review:
        client.request_solution_review(lid)
        review_back = client.get_article(lid)
        review_result = classify(source["content"], review_back.get("content") or "")
        if (
            review_back.get("contentFull") is False
            or review_result != "identical"
            or _solution_pid(review_back) != source["pid"]
            or review_back.get("promoteStatus") in UNPUBLISHED_PROMOTE_STATUSES
            or review_back.get("promoteStatus") is None
        ):
            logger.error("题解审核请求回读未确认生效；停止后续操作，不自动重试。")
            return 1
        review_back["lid"] = lid
        _save_metadata(source["pid"], review_back)
        print(
            f"=== 已凭 Accepted 记录 {accepted_record['id']} 提交题解审核请求 "
            f"{source['pid']} lid={lid} ==="
        )
    return 0


def _solution_pid(article: dict[str, Any]) -> str | None:
    solution = article.get("solutionFor")
    value = solution.get("pid") if isinstance(solution, dict) else solution
    return str(value) if value is not None else None


def _require_bound_article(pid: str, lid: str, article: dict[str, Any]) -> None:
    current_pid = _solution_pid(article)
    if current_pid != pid:
        displayed_pid = current_pid if current_pid is not None else "未知题号"
        raise LuoguError(f"文章 {lid} 绑定的是 {displayed_pid}，不是 {pid}；停止写入。")
    if article.get("contentFull") is False:
        raise LuoguError(f"文章 {lid} 回读正文不完整；停止写入。")


def _hidden_payload(pid: str, article: dict[str, Any], content: str) -> dict[str, Any]:
    config = load_config()["luogu"]["article"]
    return {
        "title": article.get("title") or _problem_title(pid),
        "category": article.get("category") or config.get("category", 2),
        "content": content,
        "solutionFor": pid,
        "status": HIDDEN_ARTICLE_STATUS,
        "top": 2,
    }


def _public_payload(pid: str, article: dict[str, Any], content: str) -> dict[str, Any]:
    config = load_config()["luogu"]["article"]
    return {
        "title": article.get("title") or _problem_title(pid),
        "category": article.get("category") or config.get("category", 2),
        "content": content,
        "solutionFor": pid,
        "status": PUBLIC_ARTICLE_STATUS,
        "top": 2,
    }


def _require_unpublished_article(pid: str, lid: str, article: dict[str, Any]) -> int:
    promote_status = article.get("promoteStatus")
    if promote_status not in UNPUBLISHED_PROMOTE_STATUSES:
        raise LuoguError(
            f"{pid} lid={lid} 的题解审核状态为 {promote_status}，不是未投稿或已拒绝；"
            "停止公开度写入。"
        )
    return int(promote_status)


def _verify_public_read_back(
    pid: str,
    lid: str,
    payload: dict[str, Any],
    promote_status: int,
    read_back: dict[str, Any],
) -> int:
    result = classify(payload["content"], read_back.get("content") or "")
    print(f"=== 公开未发表保存并回读 {pid} lid={lid}：{result} ===")
    if read_back.get("contentFull") is False or result != "identical":
        logger.error("回读不完整或正文不一致；停止后续操作。")
        return 1
    if (
        read_back.get("title") != payload["title"]
        or read_back.get("category") != payload["category"]
        or _solution_pid(read_back) != pid
        or read_back.get("status") != PUBLIC_ARTICLE_STATUS
        or read_back.get("top") != 2
        or read_back.get("promoteStatus") != promote_status
    ):
        logger.error("回读标题、分类、题号、公开度、审核状态或置顶量不一致；停止后续操作。")
        return 1
    read_back["lid"] = lid
    _save_metadata(pid, read_back)
    return 0


def _verify_hidden_read_back(
    pid: str,
    lid: str,
    payload: dict[str, Any],
    read_back: dict[str, Any],
) -> int:
    result = classify(payload["content"], read_back.get("content") or "")
    print(f"=== 隐藏保存并回读 {pid} lid={lid}：{result} ===")
    if read_back.get("contentFull") is False or result != "identical":
        logger.error("回读不完整或正文不一致；停止后续操作。")
        return 1
    if (
        read_back.get("title") != payload["title"]
        or read_back.get("category") != payload["category"]
        or _solution_pid(read_back) != pid
        or read_back.get("status") != HIDDEN_ARTICLE_STATUS
        or read_back.get("top") != 2
    ):
        logger.error("回读标题、分类、题号、公开度或置顶量不一致；停止后续操作。")
        return 1
    read_back["lid"] = lid
    _save_metadata(pid, read_back)
    return 0


def hide_live(
    pid: str,
    lid: str,
    *,
    client: LuoguClient | None = None,
) -> int:
    """Make one bound article personal-hidden without changing its content."""
    pid = pid_normalize(pid)
    client = client or LuoguClient()
    if not client.check_login().get("logged_in"):
        raise LoginExpiredError("未登录或 Cookie 失效，请更新 Cookie 后重试。")
    current = client.get_article(lid)
    _require_bound_article(pid, lid, current)
    payload = _hidden_payload(pid, current, current.get("content") or "")
    try:
        client.update_article(lid, payload)
    except LuoguError:
        if _verify_hidden_read_back(pid, lid, payload, client.get_article(lid)) == 0:
            logger.warning("写请求报错，但完整回读确认隐藏保存已经生效：%s lid=%s", pid, lid)
            return 0
        raise
    return _verify_hidden_read_back(pid, lid, payload, client.get_article(lid))


def save_hidden_live(
    source: dict[str, Any],
    *,
    client: LuoguClient | None = None,
) -> int:
    """Update an existing bound article and force personal-hidden visibility."""
    pid = pid_normalize(source["pid"])
    lid = source.get("lid")
    if not lid:
        raise ValueError("隐藏草稿只能更新已有专栏，必须提供既有 lid。")
    problem_dir = cache_dir(pid)
    require_originality_audit(pid, problem_dir)
    require_local_verification(pid, problem_dir)
    require_article_code_matches_source(pid, problem_dir, source["content"])
    client = client or LuoguClient()
    if not client.check_login().get("logged_in"):
        raise LoginExpiredError("未登录或 Cookie 失效，请更新 Cookie 后重试。")
    current = client.get_article(str(lid))
    _require_bound_article(pid, str(lid), current)
    payload = _hidden_payload(pid, current, source["content"])
    if source.get("title_override"):
        payload["title"] = source["title"]
    try:
        client.update_article(str(lid), payload)
    except LuoguError:
        if _verify_hidden_read_back(pid, str(lid), payload, client.get_article(str(lid))) == 0:
            logger.warning("写请求报错，但完整回读确认隐藏草稿已经保存：%s lid=%s", pid, lid)
            return 0
        raise
    return _verify_hidden_read_back(pid, str(lid), payload, client.get_article(str(lid)))


def restore_public_live(
    pid: str,
    lid: str,
    *,
    client: LuoguClient | None = None,
) -> int:
    """Make one unpublished bound article public without changing its content."""
    pid = pid_normalize(pid)
    client = client or LuoguClient()
    if not client.check_login().get("logged_in"):
        raise LoginExpiredError("未登录或 Cookie 失效，请更新 Cookie 后重试。")
    current = client.get_article(lid)
    _require_bound_article(pid, lid, current)
    promote_status = _require_unpublished_article(pid, lid, current)
    payload = _public_payload(pid, current, current.get("content") or "")
    try:
        client.update_article(lid, payload)
    except LuoguError:
        if _verify_public_read_back(
            pid,
            lid,
            payload,
            promote_status,
            client.get_article(lid),
        ) == 0:
            logger.warning("写请求报错，但完整回读确认公开未发表状态已经生效：%s lid=%s", pid, lid)
            return 0
        raise
    return _verify_public_read_back(
        pid,
        lid,
        payload,
        promote_status,
        client.get_article(lid),
    )


def save_public_live(
    source: dict[str, Any],
    *,
    client: LuoguClient | None = None,
) -> int:
    """Update one bound article while keeping it public and out of the solution list."""
    pid = pid_normalize(source["pid"])
    lid = source.get("lid")
    if not lid:
        raise ValueError("公开未发表保存只能更新已有专栏，必须提供既有 lid。")
    problem_dir = cache_dir(pid)
    require_originality_audit(pid, problem_dir)
    require_local_verification(pid, problem_dir)
    require_article_code_matches_source(pid, problem_dir, source["content"])
    client = client or LuoguClient()
    if not client.check_login().get("logged_in"):
        raise LoginExpiredError("未登录或 Cookie 失效，请更新 Cookie 后重试。")
    current = client.get_article(str(lid))
    _require_bound_article(pid, str(lid), current)
    promote_status = _require_unpublished_article(pid, str(lid), current)
    payload = _public_payload(pid, current, source["content"])
    if source.get("title_override"):
        payload["title"] = source["title"]
    try:
        client.update_article(str(lid), payload)
    except LuoguError:
        if _verify_public_read_back(
            pid,
            str(lid),
            payload,
            promote_status,
            client.get_article(str(lid)),
        ) == 0:
            logger.warning("写请求报错，但完整回读确认公开未发表正文已经保存：%s lid=%s", pid, lid)
            return 0
        raise
    return _verify_public_read_back(
        pid,
        str(lid),
        payload,
        promote_status,
        client.get_article(str(lid)),
    )


def retire_live(
    pid: str,
    lid: str,
    *,
    placeholder: str | None = None,
    client: LuoguClient | None = None,
) -> int:
    """Retire an article by clearing its body while preserving the original article."""
    pid = pid_normalize(pid)
    client = client or LuoguClient()
    if not client.check_login().get("logged_in"):
        raise LoginExpiredError("未登录或 Cookie 失效，请更新 Cookie 后重试。")
    current = client.get_article(lid)
    _require_bound_article(pid, lid, current)
    if placeholder is not None:
        placeholder = placeholder.strip()
        if not placeholder or "\n" in placeholder or len(placeholder) > 10:
            raise ValueError("撤回占位正文必须是 1 至 10 个字符的单行文本。")
    content = placeholder if placeholder is not None else ""
    config = load_config()["luogu"]["article"]
    payload = {
        "title": current.get("title") or _problem_title(pid),
        "category": current.get("category") or config.get("category", 2),
        "content": content,
        "solutionFor": pid,
        "status": current.get("status") or config.get("status", 2),
        "top": 2,
    }
    client.update_article(lid, payload)
    read_back = client.get_article(lid)
    result = classify(content, read_back.get("content") or "")
    print(f"=== 清空并回读 {pid} lid={lid}：{result} ===")
    if read_back.get("contentFull") is False or result != "identical":
        logger.error("回读不完整或正文不一致；专栏仍保留，停止后续操作。")
        return 1
    if read_back.get("title") != payload["title"] or read_back.get("top") != 2:
        logger.error("回读标题或置顶量不一致；专栏仍保留，停止后续操作。")
        return 1
    read_back["lid"] = lid
    _save_metadata(pid, read_back)
    if placeholder is None:
        print(f"=== 已保留原专栏并清空正文 {pid} lid={lid} ===")
    else:
        print(f"=== 已保留原专栏并写入最短占位正文 {pid} lid={lid} ===")
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
    parser.add_argument(
        "--hide-only",
        action="store_true",
        help="preserve a bound article verbatim and change it to personal-hidden",
    )
    parser.add_argument(
        "--save-hidden",
        action="store_true",
        help="update a bound article from the local draft and force personal-hidden visibility",
    )
    parser.add_argument(
        "--public-only",
        action="store_true",
        help="preserve a bound unpublished article verbatim and make it publicly visible",
    )
    parser.add_argument(
        "--save-public",
        action="store_true",
        help="update a bound article from the local draft, public but not submitted for review",
    )
    parser.add_argument("--retire", action="store_true", help="clear a bound article without deleting it")
    parser.add_argument(
        "--retire-placeholder",
        help="minimal placeholder used only after Luogu explicitly rejects an empty body",
    )
    parser.add_argument("--submit-review", action="store_true", help="request solution review after live publish")
    parser.add_argument("--confirm-current-policy", action="store_true", help="confirm official rules were rechecked")
    parser.add_argument(
        "--confirm-account-exception",
        action="store_true",
        help="confirm this account has an explicit exception for Agent-generated solution publication",
    )
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
    if args.retire and not args.live:
        logger.error("--retire 必须与 --live 同时使用。")
        return 2
    if (args.hide_only or args.save_hidden or args.public_only or args.save_public) and not args.live:
        logger.error("文章维护模式必须与 --live 同时使用。")
        return 2
    selected_modes = sum(
        bool(value)
        for value in (
            args.retire,
            args.hide_only,
            args.save_hidden,
            args.public_only,
            args.save_public,
        )
    )
    if selected_modes > 1:
        logger.error("--retire、隐藏模式与公开未发表模式互斥。")
        return 2
    if (args.hide_only or args.save_hidden or args.public_only or args.save_public) and args.submit_review:
        logger.error("草稿维护模式绝不允许提交审核。")
        return 2
    if args.retire and (
        args.submit_review
        or args.diff
        or args.title
        or args.disclosure_file
        or args.eligibility
        or args.confirm_account_exception
        or args.confirm_current_policy
    ):
        logger.error("--retire 不能与投稿、diff、改标题、来源分类或披露参数同时使用。")
        return 2
    if args.retire_placeholder is not None and not args.retire:
        logger.error("--retire-placeholder 只能与 --retire 同时使用。")
        return 2
    if args.hide_only and (
        args.diff
        or args.title
        or args.disclosure_file
        or args.eligibility
        or args.confirm_account_exception
        or args.confirm_current_policy
    ):
        logger.error("--hide-only 只能原样隐藏既有文章，不能与其他内容或投稿参数同时使用。")
        return 2
    if args.public_only and (
        args.diff
        or args.title
        or args.disclosure_file
        or args.eligibility
        or args.confirm_account_exception
        or args.confirm_current_policy
    ):
        logger.error("--public-only 只能原样恢复既有未发表文章的公开度。")
        return 2
    if args.live and not args.eligibility and not args.retire and not args.hide_only and not args.public_only:
        logger.error("真实发布必须声明 --eligibility。")
        return 2
    if args.submit_review and not args.confirm_current_policy:
        logger.error("投稿审核前必须重新核验官方规则，并传入 --confirm-current-policy。")
        return 2
    try:
        if args.retire:
            pid = pid_normalize(args.source)
            lid = args.lid or _load_metadata(pid).get("lid")
            if not lid:
                raise ValueError("清空专栏必须提供 --lid，或已有 article.json 绑定。")
            return retire_live(
                pid,
                str(lid),
                placeholder=args.retire_placeholder,
            )
        if args.hide_only:
            pid = pid_normalize(args.source)
            lid = args.lid or _load_metadata(pid).get("lid")
            if not lid:
                raise ValueError("隐藏专栏必须提供 --lid，或已有 article.json 绑定。")
            return hide_live(pid, str(lid))
        if args.public_only:
            pid = pid_normalize(args.source)
            lid = args.lid or _load_metadata(pid).get("lid")
            if not lid:
                raise ValueError("恢复公开必须提供 --lid，或已有 article.json 绑定。")
            return restore_public_live(pid, str(lid))
        source = load_source(args.source, lid=args.lid, title=args.title)
        if args.live:
            source = _with_disclosure(source, args)
            if args.save_hidden:
                return save_hidden_live(source)
            if args.save_public:
                return save_public_live(source)
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
