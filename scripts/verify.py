"""验证题解代码：编译 solution.cpp + 跑样例。

用法：
    python verify.py P1001

读 ~/.cache/luogu/<PID>/solution.cpp 与 raw/problem.json 的样例。
返回码 0 = 通过；非 0 = 失败。**本地样例过不等于 AC**，不得虚构在线评测结果。
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from util import cache_dir, load_config, get_logger, pid_normalize, compat_dir

logger = get_logger()


class VerifyResult:
    def __init__(self) -> None:
        self.ok = True
        self.steps: list[dict[str, Any]] = []

    def add(self, name: str, ok: bool, detail: str = "") -> None:
        self.steps.append({"step": name, "ok": ok, "detail": detail})
        if not ok:
            self.ok = False

    def summary(self) -> str:
        out = []
        for s in self.steps:
            line = f"{'✅' if s['ok'] else '❌'} {s['step']}"
            if s["detail"]:
                line += f" — {s['detail']}"
            out.append(line)
        return "\n".join(out)


def _load_samples(pid: str) -> list[tuple[str, str]]:
    raw = cache_dir(pid) / "raw" / "problem.json"
    if not raw.exists():
        return []
    try:
        data = json.loads(raw.read_text(encoding="utf-8"))
    except ValueError:
        return []
    out: list[tuple[str, str]] = []
    for s in data.get("samples") or []:
        if isinstance(s, (list, tuple)) and len(s) >= 2:
            out.append((str(s[0]), str(s[1])))
        elif isinstance(s, dict):
            out.append((str(s.get("input", "")), str(s.get("output", ""))))
    return out


def _normalize_output(text: str) -> str:
    lines = [ln.rstrip() for ln in text.replace("\r\n", "\n").split("\n")]
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines)


def verify(pid: str) -> VerifyResult:
    pid = pid_normalize(pid)
    work_dir = cache_dir(pid)
    res = VerifyResult()

    src = work_dir / "solution.cpp"
    res.add("solution.cpp", src.exists(), "存在" if src.exists() else "缺少（先把代码写到此处）")
    if not src.exists():
        return res

    cfg = load_config()["verify"]
    with tempfile.TemporaryDirectory() as td:
        binary = Path(td) / "sol"
        cmd = [cfg["cxx"], f"-std={cfg['std']}", "-O2", "-o", str(binary), str(src)]
        # macOS/Apple clang 无 <bits/stdc++.h>，用垫片头补（不影响 GNU g++）。
        if compat_dir().exists():
            cmd[1:1] = ["-I", str(compat_dir())]
        try:
            cp = subprocess.run(cmd, capture_output=True, text=True, timeout=int(cfg.get("compile_timeout", 60)))
        except subprocess.TimeoutExpired:
            res.add("编译", False, "编译超时")
            return res
        except FileNotFoundError:
            res.add("编译", False, f"找不到编译器 {cfg['cxx']}")
            return res
        if cp.returncode != 0:
            tail = "\n".join((cp.stderr or "").strip().splitlines()[-8:]) or "未知错误"
            res.add("编译", False, f"{cfg['cxx']} 失败:\n{tail}")
            return res
        res.add("编译", True, f"{cfg['cxx']} -std={cfg['std']}")

        samples = _load_samples(pid)
        if not samples:
            res.add("样例运行", True, "无样例，跳过")
            return res
        run_timeout = int(cfg.get("run_timeout", 10))
        passed = 0
        for i, (inp, expected) in enumerate(samples, 1):
            try:
                rp = subprocess.run([str(binary)], input=inp if inp.endswith("\n") else inp + "\n",
                                    capture_output=True, text=True, timeout=run_timeout)
            except subprocess.TimeoutExpired:
                res.add(f"样例 #{i}", False, "运行超时（死循环 / TLE）")
                continue
            if rp.returncode != 0:
                res.add(f"样例 #{i}", False, f"运行非零退出 {rp.returncode}")
                continue
            got, exp = _normalize_output(rp.stdout), _normalize_output(expected)
            if got == exp:
                passed += 1
                res.add(f"样例 #{i}", True, "通过")
            else:
                res.add(f"样例 #{i}", False, f"输出不符\n  期望: {exp[:120]!r}\n  实际: {got[:120]!r}")
        logger.info("样例通过 %d/%d", passed, len(samples))
    return res


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("用法: python verify.py P1001", file=sys.stderr)
        return 2
    res = verify(argv[1])
    print(res.summary())
    return 0 if res.ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
