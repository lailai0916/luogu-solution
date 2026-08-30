from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from util import (  # noqa: E402
    _DEFAULT_CONFIG,
    classify,
    parse_markdown,
    pid_normalize,
    publishable_body,
    render_luogu_article,
    shield_path_text,
)


class UtilTest(unittest.TestCase):
    def test_default_verification_matches_luogu_cxx14_o2_target(self) -> None:
        self.assertEqual(_DEFAULT_CONFIG["verify"]["std"], "c++14")
        self.assertEqual(_DEFAULT_CONFIG["verify"]["optimization"], "O2")

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

    def test_luogu_envelope_has_exact_badges(self) -> None:
        self.assertEqual(shield_path_text("AT_arc-1"), "AT__arc--1")
        result = render_luogu_article("P1001", "## 解题思路\n\n正文\n")
        self.assertTrue(result.startswith(
            "[![](https://img.shields.io/badge/Luogu-P1001-blue?style=for-the-badge&logo=luogu)]"
            "(https://www.luogu.com.cn/problem/P1001)\n"
            "[![](https://img.shields.io/badge/Blog-Solution-blue?style=for-the-badge&logo=markdown)]"
            "(https://lailai.one/blog/solution/P1001)\n\n"
        ))
        self.assertEqual(result.count("img.shields.io"), 2)


if __name__ == "__main__":
    unittest.main()
