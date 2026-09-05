"""验证题解代码：编译 solution.cpp，并运行对应的本地验证器。

用法：
    python verify.py P1001

默认读取 raw/problem.json 的样例；交互题可提供 interactor.py，通信题可提供
grader.cpp。
返回码 0 = 通过；非 0 = 失败。**本地样例过不等于 AC**，不得虚构在线评测结果。
"""
from __future__ import annotations

import json
import math
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from gates import artifact_digest
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


def _load_problem(pid: str) -> dict[str, Any]:
    raw = cache_dir(pid) / "raw" / "problem.json"
    if not raw.exists():
        return {}
    try:
        data = json.loads(raw.read_text(encoding="utf-8"))
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}


def _load_samples(problem: dict[str, Any]) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for s in problem.get("samples") or []:
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


def _float_tolerance(problem: dict[str, Any]) -> float | None:
    output_format = str(problem.get("outputFormat") or "")
    if not re.search(r"absolute|relative|误差", output_format, re.IGNORECASE):
        return None
    match = re.search(r"10\s*\^\s*\{?\s*-(\d+)\s*\}?", output_format)
    return 10 ** -int(match.group(1)) if match else None


def _outputs_match(got: str, expected: str, tolerance: float | None) -> bool:
    if got == expected:
        return True
    if tolerance is None:
        return False
    got_tokens = got.split()
    expected_tokens = expected.split()
    if len(got_tokens) != len(expected_tokens):
        return False
    for got_token, expected_token in zip(got_tokens, expected_tokens):
        if got_token == expected_token:
            continue
        try:
            got_value = float(got_token)
            expected_value = float(expected_token)
        except ValueError:
            return False
        if (
            not math.isfinite(got_value)
            or not math.isfinite(expected_value)
            or abs(got_value - expected_value) > tolerance * max(1.0, abs(expected_value))
        ):
            return False
    return True


def _run_sample_checker(
    checker: Path,
    sample_input: str,
    actual_output: str,
    expected_output: str,
    timeout: int,
) -> tuple[bool, str]:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        input_path = root / "input.txt"
        actual_path = root / "actual.txt"
        expected_path = root / "expected.txt"
        input_path.write_text(sample_input, encoding="utf-8")
        actual_path.write_text(actual_output, encoding="utf-8")
        expected_path.write_text(expected_output, encoding="utf-8")
        try:
            result = subprocess.run(
                [sys.executable, str(checker), str(input_path), str(actual_path), str(expected_path)],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return False, "题目专用样例校验器运行超时"
        detail = (result.stderr or result.stdout or "").strip()
        return result.returncode == 0, detail


def _run_interactor(interactor: Path, binary: Path, timeout: int) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            [sys.executable, str(interactor), str(binary)],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return False, "题目专用交互器运行超时"
    detail = (result.stderr or result.stdout or "").strip()
    return result.returncode == 0, detail


def _run_grader(binary: Path, timeout: int) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            [str(binary)],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return False, "题目专用通信模拟器运行超时"
    detail = (result.stderr or result.stdout or "").strip()
    return result.returncode == 0, detail


def verify(pid: str) -> VerifyResult:
    pid = pid_normalize(pid)
    work_dir = cache_dir(pid)
    res = VerifyResult()

    src = work_dir / "solution.cpp"
    res.add("solution.cpp", src.exists(), "存在" if src.exists() else "缺少（先把代码写到此处）")
    if not src.exists():
        return res

    cfg = load_config()["verify"]
    interactor = work_dir / "interactor.py"
    grader = work_dir / "grader.cpp"
    if interactor.exists() and grader.exists():
        res.add("验证配置", False, "interactor.py 与 grader.cpp 不能同时存在")
        return res
    with tempfile.TemporaryDirectory() as td:
        binary = Path(td) / "sol"
        optimization = str(cfg.get("optimization", "O2"))
        cmd = [cfg["cxx"], f"-std={cfg['std']}", f"-{optimization}", "-o", str(binary), str(src)]
        if grader.exists():
            cmd.append(str(grader))
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
        res.add("编译", True, f"{cfg['cxx']} -std={cfg['std']} -{optimization}")

        problem = _load_problem(pid)
        if grader.exists():
            matched, detail = _run_grader(
                binary,
                max(120, int(cfg.get("run_timeout", 10))),
            )
            res.add(
                "通信模拟",
                matched,
                detail or ("通过" if matched else "题目专用通信模拟器拒绝程序"),
            )
            return res
        if interactor.exists():
            matched, detail = _run_interactor(
                interactor,
                binary,
                max(120, int(cfg.get("run_timeout", 10))),
            )
            res.add(
                "交互模拟",
                matched,
                detail or ("通过" if matched else "题目专用交互器拒绝程序"),
            )
            return res
        samples = _load_samples(problem)
        if not samples:
            res.add("样例运行", True, "无样例，跳过")
            return res
        run_timeout = int(cfg.get("run_timeout", 10))
        sample_checker = work_dir / "sample_checker.py"
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
            if sample_checker.exists():
                matched, detail = _run_sample_checker(
                    sample_checker,
                    inp,
                    rp.stdout,
                    expected,
                    run_timeout,
                )
            else:
                matched = _outputs_match(got, exp, _float_tolerance(problem))
                detail = ""
            if matched:
                passed += 1
                res.add(f"样例 #{i}", True, detail or "通过")
            else:
                if sample_checker.exists():
                    res.add(f"样例 #{i}", False, detail or "题目专用样例校验器拒绝输出")
                else:
                    res.add(f"样例 #{i}", False, f"输出不符\n  期望: {exp[:120]!r}\n  实际: {got[:120]!r}")
        logger.info("样例通过 %d/%d", passed, len(samples))
    return res


def record_verification(pid: str, result: VerifyResult) -> Path:
    pid = pid_normalize(pid)
    work_dir = cache_dir(pid)
    raw_dir = work_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    statement = work_dir / "problem.md"
    source = work_dir / "solution.cpp"
    evidence = {
        "version": 4,
        "pid": pid,
        "status": "pass" if result.ok else "fail",
        "recordedAt": datetime.now(timezone.utc).isoformat(),
        "statement": artifact_digest(statement) if statement.exists() else None,
        "source": artifact_digest(source) if source.exists() else None,
        "checker": artifact_digest(work_dir / "sample_checker.py")
        if (work_dir / "sample_checker.py").exists()
        else None,
        "interactor": artifact_digest(work_dir / "interactor.py")
        if (work_dir / "interactor.py").exists()
        else None,
        "grader": artifact_digest(work_dir / "grader.cpp")
        if (work_dir / "grader.cpp").exists()
        else None,
        "steps": result.steps,
    }
    path = raw_dir / "local-verification.json"
    path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("用法: python verify.py P1001", file=sys.stderr)
        return 2
    res = verify(argv[1])
    path = record_verification(argv[1], res)
    print(res.summary())
    print(f"本地验证记录：{path}")
    return 0 if res.ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
