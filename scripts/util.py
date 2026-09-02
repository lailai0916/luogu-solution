"""Shared configuration, cache, credential, Markdown, and comparison helpers."""
from __future__ import annotations

import logging
import os
import re
import sys
from pathlib import Path
from typing import Any

import yaml

SCRIPT_DIR = Path(__file__).resolve().parent


def config_home() -> Path:
    """Return the machine-local configuration directory outside repositories."""
    env = os.environ.get("LUOGU_SOLUTION_HOME")
    if env and env.strip():
        return Path(env).expanduser()
    return Path.home() / ".config" / "luogu-solution"


def cache_root() -> Path:
    """Return the external problem-work cache root."""
    env = os.environ.get("LUOGU_CACHE_HOME")
    root = Path(env).expanduser() if env and env.strip() else Path.home() / ".cache" / "luogu"
    root.mkdir(parents=True, exist_ok=True)
    return root


def pid_normalize(pid: str) -> str:
    pid = pid.strip()
    if pid and pid[0].islower():
        pid = pid[0].upper() + pid[1:]
    if not re.fullmatch(r"[A-Za-z0-9_-]+", pid):
        raise ValueError(f"非法题号: {pid!r}")
    return pid


def cache_dir(pid: str) -> Path:
    path = cache_root() / pid_normalize(pid)
    path.mkdir(parents=True, exist_ok=True)
    return path


def compat_dir() -> Path:
    return SCRIPT_DIR / "compat"


def tasks_file() -> Path:
    return cache_root() / "tasks.yaml"


_DEFAULT_CONFIG: dict[str, Any] = {
    "luogu": {
        "base_url": "https://www.luogu.com.cn",
        "csrf_url": "https://www.luogu.com.cn/user/setting",
        "request_delay": 1.0,
        "write_request_delay": 2.0,
        "max_solutions": 8,
        "article": {
            "category": 2,
            "status": 2,
        },
    },
    "verify": {
        "cxx": "g++",
        "std": "c++17",
        "optimization": "O2",
        "compile_timeout": 60,
        "run_timeout": 10,
    },
    "stress": {"rounds": 1000, "run_timeout": 5},
}


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


_config_cache: dict[str, Any] | None = None


def load_config() -> dict[str, Any]:
    global _config_cache
    if _config_cache is not None:
        return _config_cache
    config = _DEFAULT_CONFIG
    path = config_home() / "config.yaml"
    if path.exists():
        with path.open("r", encoding="utf-8") as file:
            config = _deep_merge(config, yaml.safe_load(file) or {})
    _config_cache = config
    return config


def load_cookie() -> str | None:
    env = os.environ.get("LUOGU_COOKIE")
    if env and env.strip():
        return env.strip()
    path = config_home() / "cookie.txt"
    if path.exists():
        text = path.read_text(encoding="utf-8").strip()
        if text:
            return text
    return None


def shield_path_text(text: str) -> str:
    """Escape text for a Shields static-badge path segment."""
    return text.replace("-", "--").replace("_", "__").replace(" ", "_")


def render_luogu_article(pid: str, body: str) -> str:
    """Render the Luogu-only envelope around a platform-neutral solution body."""
    badge_pid = shield_path_text(pid)
    badges = (
        f"[![](https://img.shields.io/badge/Luogu-{badge_pid}-blue?style=for-the-badge&logo=luogu)]"
        f"(https://www.luogu.com.cn/problem/{pid})\n\n"
    )
    return badges + normalize_transport(body) + "\n"


_SECRET_PAT = re.compile(r"(_uid=|__client_id=|csrf|cookie|token)[^;\s]*", re.IGNORECASE)


def redact(text: str | None) -> str:
    if not text:
        return ""
    return _SECRET_PAT.sub(lambda match: match.group(0)[:6] + "***REDACTED***", str(text))


def get_logger(name: str = "luogu") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S")
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.propagate = False
    return logger


_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


def parse_markdown(text: str) -> dict[str, Any]:
    """Remove optional YAML frontmatter and return metadata plus body."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return {"frontmatter": {}, "body": text}
    frontmatter = yaml.safe_load(match.group(1)) or {}
    if not isinstance(frontmatter, dict):
        raise ValueError("frontmatter 必须是映射")
    return {"frontmatter": frontmatter, "body": text[match.end():]}


def publishable_body(text: str) -> str:
    """Return standalone Markdown, starting at H2 when a target wrapper precedes it."""
    body = parse_markdown(text)["body"]
    lines = body.split("\n")
    start = next((index for index, line in enumerate(lines) if line.startswith("## ")), None)
    if start is not None:
        body = "\n".join(lines[start:])
    return normalize_transport(body) + "\n"


def normalize_transport(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n").strip("\n")


def _collapse_ws(text: str) -> str:
    return "\n".join(line.rstrip() for line in text.split("\n") if line.strip())


def classify(expected: str, actual: str) -> str:
    expected = normalize_transport(expected)
    actual = normalize_transport(actual)
    if expected == actual:
        return "identical"
    if _collapse_ws(expected) == _collapse_ws(actual):
        return "whitespace"
    return "substantive"
