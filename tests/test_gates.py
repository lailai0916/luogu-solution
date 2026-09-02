from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from gates import (  # noqa: E402
    ORIGINALITY_AXES,
    artifact_digest,
    checkpoint_independent_draft,
    record_originality_audit,
    require_article_code_matches_source,
    require_independent_checkpoint,
    require_local_verification,
    require_originality_audit,
)


class WorkflowGateTest(unittest.TestCase):
    def make_problem(self, root: Path) -> None:
        (root / "problem.md").write_text("# A+B Problem（P1001）\n", encoding="utf-8")
        (root / "solution.cpp").write_text("int main(){}\n", encoding="utf-8")
        (root / "solution.md").write_text("## 解题思路\n\n独立推导。\n", encoding="utf-8")

    def findings(self) -> dict[str, str]:
        return {axis: f"{axis} 已逐项比较，未继承参考题解的私有结构。" for axis in ORIGINALITY_AXES}

    def test_checkpoint_requires_statement_and_both_independent_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaisesRegex(Exception, "必须先抓取官方题面"):
                checkpoint_independent_draft("P1001", root)
            (root / "problem.md").write_text("# A+B Problem（P1001）\n", encoding="utf-8")
            with self.assertRaisesRegex(Exception, "必须先独立完成 solution.cpp"):
                checkpoint_independent_draft("P1001", root)

    def test_valid_checkpoint_is_reused(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_problem(root)
            path = checkpoint_independent_draft("P1001", root)
            self.assertEqual(require_independent_checkpoint("P1001", root)["pid"], "P1001")
            self.assertEqual(checkpoint_independent_draft("P1001", root), path)

    def test_nonempty_references_require_five_axis_audit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_problem(root)
            checkpoint_independent_draft("P1001", root)
            (root / "raw" / "solutions.json").write_text(
                '[{"lid": "abcdefgh", "content": "参考"}]\n',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(Exception, "缺少五轴原创性审计"):
                require_originality_audit("P1001", root)

    def test_audit_is_bound_to_current_draft_and_references(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_problem(root)
            checkpoint_independent_draft("P1001", root)
            (root / "raw" / "solutions.json").write_text(
                '[{"lid": "abcdefgh", "content": "参考"}]\n',
                encoding="utf-8",
            )
            record_originality_audit("P1001", root, self.findings())
            audit = require_originality_audit("P1001", root)
            self.assertEqual(audit["references"]["lids"], ["abcdefgh"])
            self.assertTrue(audit["references"]["present"])
            (root / "solution.md").write_text("## 解题思路\n\n修改。\n", encoding="utf-8")
            with self.assertRaisesRegex(Exception, "solution.md.*重新审计"):
                require_originality_audit("P1001", root)

    def test_audit_rejects_missing_axis(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_problem(root)
            checkpoint_independent_draft("P1001", root)
            (root / "raw" / "solutions.json").write_text("[{}]\n", encoding="utf-8")
            findings = self.findings()
            del findings[ORIGINALITY_AXES[0]]
            with self.assertRaisesRegex(Exception, ORIGINALITY_AXES[0]):
                record_originality_audit("P1001", root, findings)

    def test_audit_file_has_no_untracked_fields_from_report(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_problem(root)
            checkpoint_independent_draft("P1001", root)
            (root / "raw" / "solutions.json").write_text("[{}]\n", encoding="utf-8")
            path = record_originality_audit(
                "P1001",
                root,
                {**self.findings(), "authorization": "must not be copied"},
            )
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertNotIn("authorization", data)

    def test_audit_records_only_valid_public_sources(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_problem(root)
            checkpoint_independent_draft("P1001", root)
            (root / "raw" / "solutions.json").write_text("[{}]\n", encoding="utf-8")
            findings = {
                **self.findings(),
                "public_sources": [
                    {"url": "https://example.com/editorial", "title": "Editorial"},
                    {"url": "https://example.com/editorial", "title": "Duplicate"},
                ],
            }
            path = record_originality_audit("P1001", root, findings)
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(
                data["publicSources"],
                [{"url": "https://example.com/editorial", "title": "Editorial"}],
            )

    def test_public_only_audit_does_not_require_luogu_reference_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_problem(root)
            checkpoint_independent_draft("P1001", root)
            findings = {
                **self.findings(),
                "public_sources": [
                    {"url": "https://example.com/editorial", "title": "Editorial"},
                ],
            }
            record_originality_audit("P1001", root, findings)
            audit = require_originality_audit("P1001", root)
            self.assertFalse(audit["references"]["present"])
            (root / "raw" / "solutions.json").write_text("[]\n", encoding="utf-8")
            with self.assertRaisesRegex(Exception, "参考题解集合.*重新审计"):
                require_originality_audit("P1001", root)

    def test_local_verification_is_bound_to_statement_and_source(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_problem(root)
            (root / "raw").mkdir()
            evidence = {
                "version": 1,
                "pid": "P1001",
                "status": "pass",
                "statement": artifact_digest(root / "problem.md"),
                "source": artifact_digest(root / "solution.cpp"),
                "steps": [{"step": "编译", "ok": True, "detail": "C++17"}],
            }
            (root / "raw" / "local-verification.json").write_text(
                json.dumps(evidence),
                encoding="utf-8",
            )
            self.assertEqual(require_local_verification("P1001", root)["status"], "pass")
            (root / "solution.cpp").write_text("int main(){return 0;}\n", encoding="utf-8")
            with self.assertRaisesRegex(Exception, "solution.cpp.*重新验证"):
                require_local_verification("P1001", root)

    def test_article_code_must_equal_current_source(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_problem(root)
            content = "## 参考代码\n\n```cpp\nint main(){}\n```\n"
            self.assertEqual(
                require_article_code_matches_source("P1001", root, content),
                "int main(){}\n",
            )
            with self.assertRaisesRegex(Exception, "参考代码.*solution.cpp 不一致"):
                require_article_code_matches_source(
                    "P1001",
                    root,
                    "## 参考代码\n\n```cpp\nint main(){return 0;}\n```\n",
                )


if __name__ == "__main__":
    unittest.main()
