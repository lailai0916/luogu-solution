from __future__ import annotations

import argparse
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from publish import _with_disclosure  # noqa: E402


class PublishPolicyTest(unittest.TestCase):
    def test_agent_generated_is_blocked(self) -> None:
        args = argparse.Namespace(eligibility="agent-generated", disclosure_file=None)
        with self.assertRaisesRegex(ValueError, "不得执行真实发布"):
            _with_disclosure({"content": "正文\n"}, args)

    def test_editorial_ai_requires_disclosure(self) -> None:
        args = argparse.Namespace(eligibility="editorial-ai", disclosure_file=None)
        with self.assertRaisesRegex(ValueError, "disclosure-file"):
            _with_disclosure({"content": "正文\n"}, args)

    def test_editorial_ai_appends_exact_disclosure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "disclosure.md"
            path.write_text("披露。\n", encoding="utf-8")
            args = argparse.Namespace(eligibility="editorial-ai", disclosure_file=str(path))
            result = _with_disclosure({"content": "正文\n"}, args)
        self.assertEqual(result["content"], "正文\n\n披露。\n")


if __name__ == "__main__":
    unittest.main()
