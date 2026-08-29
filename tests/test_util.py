from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from util import classify, parse_markdown, pid_normalize, publishable_body  # noqa: E402


class UtilTest(unittest.TestCase):
    def test_pid_normalize(self) -> None:
        self.assertEqual(pid_normalize(" p1001 "), "P1001")
        with self.assertRaises(ValueError):
            pid_normalize("../../cookie")

    def test_publishable_body_removes_frontmatter_and_wrapper(self) -> None:
        source = "---\ntitle: x\n---\nlead\n\n## 解题思路\n\n正文\n"
        self.assertEqual(publishable_body(source), "## 解题思路\n\n正文\n")
        self.assertEqual(parse_markdown(source)["frontmatter"]["title"], "x")

    def test_classify(self) -> None:
        self.assertEqual(classify("a\n", "a"), "identical")
        self.assertEqual(classify("a\n\nb", "a\nb"), "whitespace")
        self.assertEqual(classify("a", "b"), "substantive")


if __name__ == "__main__":
    unittest.main()
