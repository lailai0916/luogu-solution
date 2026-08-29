"""可选的题目清单与状态记录（~/.cache/luogu/tasks.yaml）。

用法：
    python scheduler.py list
    python scheduler.py next
    python scheduler.py set P1001 drafting
"""
from __future__ import annotations

import sys
from typing import Any, Optional

import yaml

from util import tasks_file, get_logger, pid_normalize

logger = get_logger()

STATES = ["queued", "fetched", "drafting", "verified", "published", "done", "failed"]


def load_tasks() -> dict[str, Any]:
    path = tasks_file()
    if not path.exists():
        return {"problems": []}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    data.setdefault("problems", [])
    return data


def save_tasks(data: dict[str, Any]) -> None:
    tasks_file().write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


def _find(data: dict[str, Any], pid: str) -> Optional[dict[str, Any]]:
    pid = pid_normalize(pid)
    for t in data.get("problems", []):
        if pid_normalize(str(t.get("pid", ""))) == pid:
            return t
    return None


def select_next() -> Optional[str]:
    queued = [t for t in load_tasks().get("problems", []) if t.get("status") == "queued"]
    if not queued:
        return None
    queued.sort(key=lambda t: t.get("priority", 0), reverse=True)
    return pid_normalize(str(queued[0]["pid"]))


def set_status(pid: str, status: str, *, error: Optional[str] = None) -> None:
    if status not in STATES:
        raise ValueError(f"未知状态: {status}（可选 {', '.join(STATES)}）")
    data = load_tasks()
    task = _find(data, pid)
    if task is None:
        task = {"pid": pid_normalize(pid), "status": status, "priority": 0}
        data.setdefault("problems", []).append(task)
    task["status"] = status
    if error:
        task["last_error"] = error[:300]
    elif "last_error" in task and status != "failed":
        task.pop("last_error", None)
    save_tasks(data)
    logger.info("状态更新 %s -> %s", pid_normalize(pid), status)


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[1] == "list":
        for t in load_tasks().get("problems", []):
            err = f"  ({t['last_error']})" if t.get("last_error") else ""
            print(f"{t.get('pid'):8} {t.get('status', '?'):12} prio={t.get('priority', 0)}{err}")
        return 0
    if argv[1] == "next":
        print(select_next() or "（无 queued 任务）")
        return 0
    if argv[1] == "set" and len(argv) >= 4:
        set_status(argv[2], argv[3])
        return 0
    print("用法: python scheduler.py [list|next|set <pid> <status>]", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
