"""Deterministically stress-test solution.cpp against brute.cpp with generator.py."""
from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

from util import cache_dir, compat_dir, load_config, normalize_transport, pid_normalize


class StressError(Exception):
    pass


def _compile(source: Path, binary: Path) -> None:
    config = load_config()["verify"]
    optimization = str(config.get("optimization", "O2"))
    command = [config["cxx"], f"-std={config['std']}", f"-{optimization}", "-o", str(binary), str(source)]
    if compat_dir().exists():
        command[1:1] = ["-I", str(compat_dir())]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=int(config.get("compile_timeout", 60)),
        )
    except FileNotFoundError as error:
        raise StressError(f"找不到编译器 {config['cxx']}") from error
    except subprocess.TimeoutExpired as error:
        raise StressError(f"编译超时：{source.name}") from error
    if result.returncode != 0:
        detail = "\n".join((result.stderr or "").strip().splitlines()[-12:])
        raise StressError(f"编译失败 {source.name}:\n{detail}")


def _run(command: list[str], data: str | None, timeout: float, name: str) -> str:
    try:
        result = subprocess.run(
            command,
            input=data,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as error:
        raise StressError(f"{name} 运行超时") from error
    if result.returncode != 0:
        detail = "\n".join((result.stderr or "").strip().splitlines()[-12:])
        raise StressError(f"{name} 非零退出 {result.returncode}:\n{detail}")
    return result.stdout


def stress(pid: str, *, rounds: int, start_seed: int = 1) -> None:
    pid = pid_normalize(pid)
    work = cache_dir(pid)
    solution = work / "solution.cpp"
    brute = work / "brute.cpp"
    generator = work / "generator.py"
    missing = [path.name for path in (solution, brute, generator) if not path.exists()]
    if missing:
        raise StressError("缺少对拍文件：" + ", ".join(missing))

    timeout = float(load_config()["stress"].get("run_timeout", 5))
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        solution_bin = root / "solution"
        brute_bin = root / "brute"
        _compile(solution, solution_bin)
        _compile(brute, brute_bin)
        for seed in range(start_seed, start_seed + rounds):
            data = _run([sys.executable, str(generator), str(seed)], None, timeout, "generator.py")
            expected = _run([str(brute_bin)], data, timeout, "brute.cpp")
            actual = _run([str(solution_bin)], data, timeout, "solution.cpp")
            if normalize_transport(expected) != normalize_transport(actual):
                failure = work / "stress-failure"
                failure.mkdir(parents=True, exist_ok=True)
                (failure / "input.txt").write_text(data, encoding="utf-8")
                (failure / "expected.txt").write_text(expected, encoding="utf-8")
                (failure / "actual.txt").write_text(actual, encoding="utf-8")
                (failure / "seed.txt").write_text(str(seed) + "\n", encoding="utf-8")
                raise StressError(f"seed={seed} 输出不一致，反例已保存到 {failure}")
    print(f"对拍通过：{rounds} 组，seed={start_seed}..{start_seed + rounds - 1}")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pid")
    parser.add_argument("--rounds", type=int)
    parser.add_argument("--start-seed", type=int, default=1)
    args = parser.parse_args(argv[1:])
    rounds = args.rounds or int(load_config()["stress"].get("rounds", 1000))
    if rounds <= 0:
        parser.error("--rounds must be positive")
    try:
        stress(args.pid, rounds=rounds, start_seed=args.start_seed)
    except StressError as error:
        print(f"对拍失败：{error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
