"""Luogu web client for statement/reference reads and guarded article writes.

用第三方整理的 lentille 网页 API，读接口核心头 x-lentille-request: content-only。
安全约定：Cookie 只在本模块用，绝不写日志/stdout/文件；异常经 redact 脱敏；解析防御式降级。

写操作实战要点（2026-08，lentille/columba）：
- 新建 POST /article/_newSubmit；编辑 POST /article/<lid>/editSubmit。
- 题解审核请求 POST /article/<lid>/requestPromotion。
- editSubmit 全字段覆盖：title/category/content/solutionFor/status/top 必须齐全，漏则清空。
- solutionFor：题解填 pid 字符串（读出来是对象，回写取 .pid）。
- CC 反爬挑战 C3VK：写请求前 CDN 先 307 + set-cookie C3VK，需带新 cookie 重试。
  靠 cookiejar 自动接收 + allow_redirects 回放；绝不把旧 C3VK 写死在 header（会 307 死循环）。
"""
from __future__ import annotations

import json
import re
import time
from typing import Any, Optional

import requests

from util import load_config, load_cookie, redact, get_logger

logger = get_logger()


class LuoguError(Exception):
    """洛谷请求/解析错误（信息已脱敏）。"""


class LoginExpiredError(LuoguError):
    """Cookie 失效 / 未登录，需要更新 Cookie。"""


def _first(d: dict, *keys: str, default: Any = None) -> Any:
    if not isinstance(d, dict):
        return default
    for k in keys:
        if k in d and d[k] is not None:
            return d[k]
    return default


class LuoguClient:
    def __init__(self, cookie: Optional[str] = None):
        cfg = load_config()["luogu"]
        self.base_url: str = cfg["base_url"].rstrip("/")
        self.csrf_url: str = cfg["csrf_url"]
        self.request_delay: float = float(cfg.get("request_delay", 1.0))
        self._cookie = cookie if cookie is not None else load_cookie()

        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
            ),
            "Accept": "application/json, text/plain, */*",
        })
        self._install_cookie(self._cookie)

    def _install_cookie(self, cookie: Optional[str]) -> None:
        """Cookie 装进 cookiejar（非写死 header），并剔除旧 C3VK，让服务器重新下发。"""
        if not cookie:
            return
        for part in cookie.split(";"):
            part = part.strip()
            if not part or "=" not in part:
                continue
            name, value = part.split("=", 1)
            if name.strip().upper() == "C3VK":
                continue
            self.session.cookies.set(name.strip(), value.strip(), domain=".luogu.com.cn")

    # -- low level ----------------------------------------------------------

    def _get_json(self, url: str, *, content_only: bool = True) -> dict[str, Any]:
        headers = {"x-lentille-request": "content-only"} if content_only else {}
        try:
            resp = self.session.get(url, headers=headers, timeout=30)
        except requests.RequestException as e:
            raise LuoguError(f"请求失败 {url}: {type(e).__name__}") from None
        if self.request_delay:
            time.sleep(self.request_delay)
        if resp.status_code in (401, 403):
            raise LoginExpiredError(f"访问 {url} 返回 {resp.status_code}，可能未登录或 Cookie 失效。")
        if resp.status_code == 404:
            raise LuoguError(f"资源不存在 (404): {url}")
        if resp.status_code != 200:
            raise LuoguError(f"HTTP {resp.status_code}: {url}")
        try:
            data = resp.json()
        except ValueError:
            raise LoginExpiredError(f"{url} 未返回 JSON，可能 Cookie 失效或触发风控。") from None
        code = _first(data, "status", "code")
        if code in (401, 403):
            raise LoginExpiredError(f"{url} status={code}，请更新 Cookie。")
        if code is not None and code not in (200,):
            raise LuoguError(f"{url} 返回 status={code} {redact(str(data.get('message') or ''))}")
        return _first(data, "data", "currentData", default=data)

    # -- 抓题 / 题解（读）---------------------------------------------------

    def get_problem(self, pid: str) -> dict[str, Any]:
        """题面，归一成稳定字段（title/description/inputFormat/samples 等）。"""
        data = self._get_json(f"{self.base_url}/problem/{pid}")
        problem = _first(data, "problem", default=data)
        if not isinstance(problem, dict) or not _first(problem, "pid", "name"):
            raise LuoguError(f"题面解析失败：{pid}")
        content = _first(problem, "content", "contenu", default={}) or {}
        samples = problem.get("samples") or []
        norm = []
        for s in samples:
            if isinstance(s, (list, tuple)) and len(s) >= 2:
                norm.append([str(s[0]), str(s[1])])
            elif isinstance(s, dict):
                norm.append([str(s.get("input", "")), str(s.get("output", ""))])
        return {
            "pid": problem.get("pid", pid),
            "title": _first(content, "name") or problem.get("name") or pid,
            "background": content.get("background"),
            "description": content.get("description"),
            "inputFormat": content.get("formatI"),
            "outputFormat": content.get("formatO"),
            "hint": content.get("hint"),
            "samples": norm,
            "limits": problem.get("limits") or {},
            "difficulty": problem.get("difficulty"),
            "tags": problem.get("tags") or [],
            "translation": None,
        }

    def get_solution_page(self, pid: str, page: int = 1) -> dict[str, Any]:
        data = self._get_json(f"{self.base_url}/problem/solution/{pid}?page={page}")
        solutions = _first(data, "solutions", default=data)
        if not isinstance(solutions, dict):
            return {"count": 0, "perPage": 0, "result": []}
        solutions.setdefault("result", _first(solutions, "result", "data", default=[]))
        return solutions

    def get_all_solutions(self, pid: str, max_solutions: Optional[int] = None) -> list[dict[str, Any]]:
        """翻页抓题解列表（需登录），无正文的按 lid 补全。每项 lid/title/author/upvote/content/url。"""
        cfg = load_config()["luogu"]
        if max_solutions is None:
            max_solutions = cfg.get("max_solutions")
        collected: list[dict[str, Any]] = []
        page, per_page, count = 1, None, None
        while True:
            sol = self.get_solution_page(pid, page=page)
            result = sol.get("result") or []
            if count is None:
                count = _first(sol, "count", default=len(result))
                per_page = _first(sol, "perPage", default=len(result) or 10)
            if not result:
                break
            for item in result:
                collected.append(self._normalize_solution(item))
                if max_solutions and len(collected) >= max_solutions:
                    break
            if max_solutions and len(collected) >= max_solutions:
                break
            if per_page and count and page * per_page >= count:
                break
            if len(result) < (per_page or len(result)):
                break
            page += 1
            if page > 50:
                break
        for item in collected:
            if not item.get("content") and item.get("lid"):
                try:
                    item["content"] = self.get_article(item["lid"]).get("content", "")
                except LuoguError as e:
                    logger.warning("补全题解正文失败 lid=%s: %s", item.get("lid"), redact(str(e)))
                    item.setdefault("content", "")
        return collected

    @staticmethod
    def _extract_content(item: dict[str, Any]) -> str:
        c = item.get("content")
        if isinstance(c, str):
            return c
        if isinstance(c, dict):
            return _first(c, "content", "description", default="") or ""
        return ""

    def _normalize_solution(self, item: dict[str, Any]) -> dict[str, Any]:
        lid = _first(item, "lid", "id")
        author = _first(item, "author", default={}) or {}
        author_name = _first(author, "name", default="") if isinstance(author, dict) else str(author)
        return {
            "lid": str(lid) if lid is not None else "",
            "title": _first(item, "title", default="") or "",
            "author": author_name or "",
            "upvote": _first(item, "upvote", "thumbUp", "thumbup", default=0),
            "content": self._extract_content(item),
            "url": f"{self.base_url}/article/{lid}" if lid is not None else "",
        }

    def get_article(self, lid: str) -> dict[str, Any]:
        """单篇文章正文（补全题解 / 回读核对用）。contentFull 标志正文是否完整未截断。"""
        data = self._get_json(f"{self.base_url}/article/{lid}")
        article = _first(data, "article", default=data)
        if not isinstance(article, dict):
            raise LuoguError(f"文章解析失败 lid={lid}")
        return {
            "lid": str(lid),
            "title": _first(article, "title", "name", default="") or "",
            "content": self._extract_content(article),
            "contentFull": _first(article, "contentFull", "contentFul", default=None),
            "solutionFor": _first(article, "solutionFor"),
            "category": _first(article, "category"),
            "status": _first(article, "status"),
            "top": _first(article, "top"),
            "time": _first(article, "time"),
            "promoteStatus": _first(article, "promoteStatus"),
            "url": f"{self.base_url}/article/{lid}",
        }

    # -- CSRF + 写 ----------------------------------------------------------

    def get_csrf_token(self, page_url: Optional[str] = None) -> str:
        """从已登录页 HTML 的 <meta name="csrf-token"> 取 token（形如 时间戳:base64）。不打印 token。"""
        if not self._cookie:
            raise LoginExpiredError("未配置 Cookie，无法获取 CSRF token。")
        try:
            resp = self.session.get(page_url or self.csrf_url, timeout=30)
        except requests.RequestException as e:
            raise LuoguError(f"获取 CSRF 失败: {type(e).__name__}") from None
        if resp.status_code in (401, 403):
            raise LoginExpiredError("获取 CSRF 被拒，Cookie 可能失效，请更新 Cookie。")
        m = re.search(r'<meta\s+name="csrf-token"\s+content="([^"]+)"', resp.text)
        if not m:
            raise LoginExpiredError("页面找不到 csrf-token，通常是未登录 / Cookie 失效。")
        return m.group(1)

    def _post_json(self, url: str, payload: dict, *, csrf: str, referer: str) -> dict:
        """带 C3VK 处理的 JSON POST。依赖 cookiejar 自动接收 C3VK + allow_redirects 回放。"""
        headers = {
            "content-type": "application/json",
            "x-csrf-token": csrf,
            "x-requested-with": "XMLHttpRequest",
            "referer": referer,
            "origin": self.base_url,
        }
        try:
            resp = self.session.post(
                url, headers=headers,
                data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                timeout=30, allow_redirects=True,
            )
        except requests.RequestException as e:
            raise LuoguError(f"写请求失败 {url}: {type(e).__name__}") from None
        if resp.status_code in (401, 403):
            raise LoginExpiredError("写操作被拒（401/403），Cookie/CSRF 可能失效。")
        if resp.status_code == 404:
            raise LuoguError(f"接口不存在 (404)，端点可能已变更：{url}")
        if resp.status_code not in (200, 201):
            raise LuoguError(f"写操作 HTTP {resp.status_code}: {url}")
        try:
            data = resp.json()
        except ValueError:
            raise LoginExpiredError(f"{url} 写操作未返回 JSON，Cookie 可能失效或被风控。") from None
        if data.get("errorCode") or data.get("errorType"):
            raise LuoguError(f"写操作失败: {redact(json.dumps(data, ensure_ascii=False))}")
        return data

    def update_article(self, lid: str, payload: dict, *, csrf: Optional[str] = None) -> dict:
        """editSubmit 编辑已有文章（全字段覆盖，payload 须含全部字段）。"""
        edit_page = f"{self.base_url}/article/{lid}/edit"
        if csrf is None:
            csrf = self.get_csrf_token(edit_page)
        data = self._post_json(f"{self.base_url}/article/{lid}/editSubmit", payload, csrf=csrf, referer=edit_page)
        content = _first(data, "data", default=data)
        return _first(content, "article", default=content)

    def create_article(self, payload: dict, *, csrf: Optional[str] = None) -> dict:
        """Create an article through the current Columba endpoint."""
        new_page = f"{self.base_url}/article/_new"
        if csrf is None:
            csrf = self.get_csrf_token(new_page)
        data = self._post_json(
            f"{self.base_url}/article/_newSubmit",
            payload,
            csrf=csrf,
            referer=new_page,
        )
        content = _first(data, "data", default=data)
        return _first(content, "article", default=content)

    def request_solution_review(self, lid: str, *, csrf: Optional[str] = None) -> dict:
        """Request promotion; category 2 plus solutionFor makes this a solution review."""
        edit_page = f"{self.base_url}/article/{lid}/edit"
        if csrf is None:
            csrf = self.get_csrf_token(edit_page)
        data = self._post_json(
            f"{self.base_url}/article/{lid}/requestPromotion",
            {},
            csrf=csrf,
            referer=edit_page,
        )
        content = _first(data, "data", default=data)
        return _first(content, "article", default=content)

    def check_login(self) -> dict[str, Any]:
        """检查登录态，返回 {logged_in, message}（不含敏感信息）。"""
        if not self._cookie:
            return {"logged_in": False, "message": "未配置 Cookie"}
        try:
            token = self.get_csrf_token()
            return {"logged_in": True, "message": f"已登录（csrf 长度 {len(token)}）"}
        except LuoguError as e:
            return {"logged_in": False, "message": redact(str(e))}
