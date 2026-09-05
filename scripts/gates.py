"""Deterministic workflow gates shared by reference access and review publication."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Protocol

from luogu_client import LuoguError
from util import normalize_transport


ARTIFACT_NAMES = ("solution.cpp", "solution.md")
ORIGINALITY_AXES = (
    "derivation_order",
    "notation",
    "examples_and_correctness",
    "variables_and_helpers",
    "code_control_flow",
)


class AcceptedRecordReader(Protocol):
    def find_matching_accepted_record(
        self,
        pid: str,
        source_code: str,
    ) -> dict[str, Any] | None:
        ...


def artifact_digest(path: Path) -> dict[str, Any]:
    content = path.read_bytes()
    return {"sha256": hashlib.sha256(content).hexdigest(), "size": len(content)}


def _valid_digest(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and isinstance(value.get("sha256"), str)
        and len(value["sha256"]) == 64
        and isinstance(value.get("size"), int)
        and value["size"] > 0
    )


def _read_json(path: Path, *, missing: str, malformed: str) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise LuoguError(missing) from error
    except (OSError, ValueError) as error:
        raise LuoguError(malformed) from error


def require_independent_checkpoint(pid: str, problem_dir: Path) -> dict[str, Any]:
    checkpoint = _read_json(
        problem_dir / "raw" / "independent.json",
        missing=f"{pid} 缺少参考前独立初稿检查点。",
        malformed=f"{pid} 的独立初稿检查点损坏。",
    )
    artifacts = checkpoint.get("artifacts") if isinstance(checkpoint, dict) else None
    if (
        not isinstance(checkpoint, dict)
        or checkpoint.get("version") != 1
        or checkpoint.get("pid") != pid
        or not _valid_digest(checkpoint.get("statement"))
        or not isinstance(artifacts, dict)
        or any(not _valid_digest(artifacts.get(name)) for name in ARTIFACT_NAMES)
    ):
        raise LuoguError(f"{pid} 的独立初稿检查点格式错误。")
    statement = problem_dir / "problem.md"
    if not statement.exists() or checkpoint["statement"] != artifact_digest(statement):
        raise LuoguError(f"{pid} 的官方题面在独立初稿检查点后发生变化，必须重新开始。")
    return checkpoint


def checkpoint_independent_draft(pid: str, problem_dir: Path) -> Path:
    raw_dir = problem_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    path = raw_dir / "independent.json"
    if path.exists():
        require_independent_checkpoint(pid, problem_dir)
        return path

    statement = problem_dir / "problem.md"
    if not statement.exists() or not statement.read_text(encoding="utf-8").strip():
        raise LuoguError(f"{pid} 必须先抓取官方题面，再创建独立初稿检查点。")
    artifacts: dict[str, Any] = {}
    for name in ARTIFACT_NAMES:
        artifact = problem_dir / name
        if not artifact.exists() or not artifact.read_text(encoding="utf-8").strip():
            raise LuoguError(f"{pid} 必须先独立完成 {name}，再抓取已有题解。")
        artifacts[name] = artifact_digest(artifact)
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "pid": pid,
                "statement": artifact_digest(statement),
                "artifacts": artifacts,
            },
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    return path


def _read_references(pid: str, problem_dir: Path) -> list[dict[str, Any]] | None:
    path = problem_dir / "raw" / "solutions.json"
    if not path.exists():
        return None
    references = _read_json(
        path,
        missing=f"{pid} 缺少参考题解记录。",
        malformed=f"{pid} 的参考题解记录损坏。",
    )
    if not isinstance(references, list) or any(not isinstance(item, dict) for item in references):
        raise LuoguError(f"{pid} 的参考题解记录格式错误。")
    return references


def _reference_state(
    references: list[dict[str, Any]] | None,
    problem_dir: Path,
) -> dict[str, Any]:
    if references is None:
        return {"present": False, "lids": []}
    path = problem_dir / "raw" / "solutions.json"
    return {
        "present": True,
        **artifact_digest(path),
        "lids": sorted({str(item.get("lid")) for item in references if item.get("lid")}),
    }


def require_originality_remediation(
    pid: str,
    problem_dir: Path,
    *,
    require_rewritten: bool = True,
) -> dict[str, Any]:
    checkpoint = _read_json(
        problem_dir / "raw" / "remediation.json",
        missing=f"{pid} 缺少污染后重建检查点。",
        malformed=f"{pid} 的污染后重建检查点损坏。",
    )
    baseline = checkpoint.get("baseline") if isinstance(checkpoint, dict) else None
    if (
        not isinstance(checkpoint, dict)
        or checkpoint.get("version") != 1
        or checkpoint.get("pid") != pid
        or not _valid_digest(checkpoint.get("statement"))
        or not isinstance(baseline, dict)
        or any(not _valid_digest(baseline.get(name)) for name in ARTIFACT_NAMES)
        or not isinstance(checkpoint.get("references"), dict)
    ):
        raise LuoguError(f"{pid} 的污染后重建检查点格式错误。")
    statement = problem_dir / "problem.md"
    if not statement.exists() or checkpoint["statement"] != artifact_digest(statement):
        raise LuoguError(f"{pid} 的官方题面在污染后重建检查点后发生变化，必须重新开始。")
    if checkpoint["references"] != _reference_state(_read_references(pid, problem_dir), problem_dir):
        raise LuoguError(f"{pid} 的参考题解集合在污染后重建检查点后发生变化，必须重新开始。")
    if require_rewritten:
        for name in ARTIFACT_NAMES:
            artifact = problem_dir / name
            if not artifact.exists() or baseline[name] == artifact_digest(artifact):
                raise LuoguError(f"{pid} 的 {name} 尚未重写，不能完成污染后原创性审计。")
    return checkpoint


def start_originality_remediation(pid: str, problem_dir: Path) -> Path:
    raw_dir = problem_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    if (raw_dir / "independent.json").exists():
        raise LuoguError(f"{pid} 已有参考前独立初稿检查点，不应改用污染后重建流程。")
    path = raw_dir / "remediation.json"
    if path.exists():
        require_originality_remediation(pid, problem_dir, require_rewritten=False)
        return path
    references = _read_references(pid, problem_dir)
    if not references:
        raise LuoguError(f"{pid} 没有已读取的参考题解，不应启动污染后重建流程。")
    statement = problem_dir / "problem.md"
    if not statement.exists() or not statement.read_text(encoding="utf-8").strip():
        raise LuoguError(f"{pid} 必须先保留官方题面，再启动污染后重建。")
    baseline: dict[str, Any] = {}
    for name in ARTIFACT_NAMES:
        artifact = problem_dir / name
        if not artifact.exists() or not artifact.read_text(encoding="utf-8").strip():
            raise LuoguError(f"{pid} 缺少待重建的 {name}。")
        baseline[name] = artifact_digest(artifact)
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "pid": pid,
                "statement": artifact_digest(statement),
                "baseline": baseline,
                "references": _reference_state(references, problem_dir),
            },
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    return path


def record_originality_audit(
    pid: str,
    problem_dir: Path,
    findings: dict[str, Any],
) -> Path:
    references = _read_references(pid, problem_dir)
    public_sources = findings.get("public_sources", [])
    if not isinstance(public_sources, list):
        raise LuoguError(f"{pid} 的 public_sources 必须是数组。")
    normalized_sources: list[dict[str, str]] = []
    seen_urls: set[str] = set()
    for source in public_sources:
        if not isinstance(source, dict) or not isinstance(source.get("url"), str):
            raise LuoguError(f"{pid} 的公开来源必须包含非空 url。")
        url = source["url"].strip()
        title = source.get("title", "")
        if not url or not isinstance(title, str):
            raise LuoguError(f"{pid} 的公开来源字段格式错误。")
        if url not in seen_urls:
            normalized_sources.append({"url": url, "title": title.strip()})
            seen_urls.add(url)
    if not references and not normalized_sources:
        raise LuoguError(f"{pid} 没有任何参考来源，无需生成原创性审计。")
    remediation_path = problem_dir / "raw" / "remediation.json"
    if remediation_path.exists():
        checkpoint_path = remediation_path
        require_originality_remediation(pid, problem_dir)
        mode = "post-reference-remediation"
    else:
        checkpoint_path = problem_dir / "raw" / "independent.json"
        require_independent_checkpoint(pid, problem_dir)
        mode = "pre-reference-independent"

    axes: dict[str, str] = {}
    for axis in ORIGINALITY_AXES:
        finding = findings.get(axis)
        if not isinstance(finding, str) or not finding.strip():
            raise LuoguError(f"{pid} 的原创性审计缺少 {axis} 结论。")
        axes[axis] = finding.strip()

    draft: dict[str, Any] = {}
    for name in ARTIFACT_NAMES:
        artifact = problem_dir / name
        if not artifact.exists() or not artifact.read_text(encoding="utf-8").strip():
            raise LuoguError(f"{pid} 缺少当前 {name}，不能记录原创性审计。")
        draft[name] = artifact_digest(artifact)
    audit = {
        "version": 2,
        "pid": pid,
        "status": "pass",
        "provenance": {
            "mode": mode,
            "checkpoint": artifact_digest(checkpoint_path),
        },
        "draft": draft,
        "references": _reference_state(references, problem_dir),
        "publicSources": normalized_sources,
        "axes": axes,
    }
    path = problem_dir / "raw" / "originality.json"
    path.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def require_originality_audit(pid: str, problem_dir: Path) -> dict[str, Any] | None:
    references = _read_references(pid, problem_dir)
    audit_path = problem_dir / "raw" / "originality.json"
    if not references and not audit_path.exists():
        return None
    audit = _read_json(
        audit_path,
        missing=f"{pid} 已读取参考题解，却缺少五轴原创性审计。",
        malformed=f"{pid} 的原创性审计损坏。",
    )
    if (
        not isinstance(audit, dict)
        or audit.get("version") not in (1, 2)
        or audit.get("pid") != pid
        or audit.get("status") != "pass"
        or not isinstance(audit.get("draft"), dict)
        or not isinstance(audit.get("references"), dict)
        or not isinstance(audit["references"].get("present"), bool)
        or not isinstance(audit["references"].get("lids"), list)
        or not isinstance(audit.get("publicSources"), list)
        or not isinstance(audit.get("axes"), dict)
    ):
        raise LuoguError(f"{pid} 的原创性审计格式错误。")
    if audit["version"] == 1:
        require_independent_checkpoint(pid, problem_dir)
    else:
        provenance = audit.get("provenance")
        if (
            not isinstance(provenance, dict)
            or provenance.get("mode")
            not in ("pre-reference-independent", "post-reference-remediation")
            or not _valid_digest(provenance.get("checkpoint"))
        ):
            raise LuoguError(f"{pid} 的原创性审计来源记录格式错误。")
        if provenance["mode"] == "pre-reference-independent":
            checkpoint_path = problem_dir / "raw" / "independent.json"
            require_independent_checkpoint(pid, problem_dir)
        else:
            checkpoint_path = problem_dir / "raw" / "remediation.json"
            require_originality_remediation(pid, problem_dir)
        if not checkpoint_path.exists() or provenance["checkpoint"] != artifact_digest(checkpoint_path):
            raise LuoguError(f"{pid} 的原创性检查点在审计后发生变化，必须重新审计。")
    for source in audit["publicSources"]:
        if (
            not isinstance(source, dict)
            or not isinstance(source.get("url"), str)
            or not source["url"].strip()
            or not isinstance(source.get("title"), str)
        ):
            raise LuoguError(f"{pid} 的原创性审计公开来源格式错误。")

    for name in ARTIFACT_NAMES:
        artifact = problem_dir / name
        if not artifact.exists() or audit["draft"].get(name) != artifact_digest(artifact):
            raise LuoguError(f"{pid} 的 {name} 在原创性审计后发生变化，必须重新审计。")
    expected_references = _reference_state(references, problem_dir)
    if audit["references"] != expected_references:
        raise LuoguError(f"{pid} 的参考题解集合在原创性审计后发生变化，必须重新审计。")
    for axis in ORIGINALITY_AXES:
        finding = audit["axes"].get(axis)
        if not isinstance(finding, str) or not finding.strip():
            raise LuoguError(f"{pid} 的原创性审计缺少 {axis} 结论。")
    return audit


def require_local_verification(pid: str, problem_dir: Path) -> dict[str, Any]:
    evidence = _read_json(
        problem_dir / "raw" / "local-verification.json",
        missing=f"{pid} 缺少当前代码的本地编译与样例验证记录。",
        malformed=f"{pid} 的本地验证记录损坏。",
    )
    if (
        not isinstance(evidence, dict)
        or evidence.get("version") not in (1, 2, 3, 4)
        or evidence.get("pid") != pid
        or evidence.get("status") != "pass"
        or not _valid_digest(evidence.get("statement"))
        or not _valid_digest(evidence.get("source"))
        or not isinstance(evidence.get("steps"), list)
        or not evidence["steps"]
        or any(not isinstance(step, dict) or step.get("ok") is not True for step in evidence["steps"])
    ):
        raise LuoguError(f"{pid} 的本地验证记录未通过或格式错误。")
    statement = problem_dir / "problem.md"
    source = problem_dir / "solution.cpp"
    if not statement.exists() or evidence["statement"] != artifact_digest(statement):
        raise LuoguError(f"{pid} 的官方题面在本地验证后发生变化，必须重新验证。")
    if not source.exists() or evidence["source"] != artifact_digest(source):
        raise LuoguError(f"{pid} 的 solution.cpp 在本地验证后发生变化，必须重新验证。")
    checker = problem_dir / "sample_checker.py"
    checker_evidence = evidence.get("checker") if evidence.get("version") in (2, 3, 4) else None
    if checker_evidence is None:
        if checker.exists():
            raise LuoguError(f"{pid} 的样例校验器未绑定到本地验证记录，必须重新验证。")
    elif (
        not _valid_digest(checker_evidence)
        or not checker.exists()
        or checker_evidence != artifact_digest(checker)
    ):
        raise LuoguError(f"{pid} 的样例校验器在本地验证后发生变化，必须重新验证。")
    interactor = problem_dir / "interactor.py"
    interactor_evidence = evidence.get("interactor") if evidence.get("version") in (3, 4) else None
    if interactor_evidence is None:
        if interactor.exists():
            raise LuoguError(f"{pid} 的交互器未绑定到本地验证记录，必须重新验证。")
    elif (
        not _valid_digest(interactor_evidence)
        or not interactor.exists()
        or interactor_evidence != artifact_digest(interactor)
    ):
        raise LuoguError(f"{pid} 的交互器在本地验证后发生变化，必须重新验证。")
    grader = problem_dir / "grader.cpp"
    grader_evidence = evidence.get("grader") if evidence.get("version") == 4 else None
    if grader_evidence is None:
        if grader.exists():
            raise LuoguError(f"{pid} 的通信模拟器未绑定到本地验证记录，必须重新验证。")
    elif (
        not _valid_digest(grader_evidence)
        or not grader.exists()
        or grader_evidence != artifact_digest(grader)
    ):
        raise LuoguError(f"{pid} 的通信模拟器在本地验证后发生变化，必须重新验证。")
    return evidence


def reference_cpp_code(article_content: str) -> str:
    lines = normalize_transport(article_content).split("\n")
    try:
        heading = next(index for index, line in enumerate(lines) if line.strip() == "## 参考代码")
    except StopIteration:
        raise LuoguError("题解缺少 ## 参考代码；禁止提交题解审核。") from None
    blocks: list[str] = []
    index = heading + 1
    while index < len(lines) and not lines[index].startswith("## "):
        if lines[index].strip().lower() == "```cpp":
            start = index + 1
            index = start
            while index < len(lines) and lines[index].strip() != "```":
                index += 1
            if index >= len(lines):
                raise LuoguError("参考代码围栏未闭合；禁止提交题解审核。")
            blocks.append("\n".join(lines[start:index]))
        index += 1
    if len(blocks) != 1:
        raise LuoguError("## 参考代码必须且只能包含一个 cpp 代码块；禁止提交题解审核。")
    return blocks[0]


def require_article_code_matches_source(
    pid: str,
    problem_dir: Path,
    article_content: str,
) -> str:
    code_path = problem_dir / "solution.cpp"
    if not code_path.exists():
        raise LuoguError(f"{pid} 缺少 solution.cpp；停止专栏同步。")
    source_code = code_path.read_text(encoding="utf-8")
    if normalize_transport(reference_cpp_code(article_content)) != normalize_transport(source_code):
        raise LuoguError(f"{pid} 题解中的参考代码与 solution.cpp 不一致；停止专栏同步。")
    return source_code


def require_matching_accepted_record(
    pid: str,
    problem_dir: Path,
    article_content: str,
    client: AcceptedRecordReader,
) -> dict[str, Any]:
    require_originality_audit(pid, problem_dir)
    source_code = require_article_code_matches_source(pid, problem_dir, article_content)
    record = client.find_matching_accepted_record(pid, source_code)
    if record is None:
        raise LuoguError(f"{pid} 未找到与 solution.cpp 源码一致的洛谷 Accepted 记录；禁止提交题解审核。")
    return record
