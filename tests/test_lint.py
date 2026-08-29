from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from lint import lint_text  # noqa: E402


GOOD = """## 解题思路

定义 $f_i$ 表示答案。

## 参考代码

```cpp
#include <bits/stdc++.h>
using namespace std;
int f[10];
int main()
{
\treturn 0;
}
```
"""


class SolutionLintTest(unittest.TestCase):
    def test_good_solution(self) -> None:
        self.assertEqual(lint_text(GOOD), [])

    def test_rejects_structure_comments_dp_and_signature(self) -> None:
        bad = GOOD.replace("## 解题思路", "# 思路").replace(
            "int f[10];", "int dp[10]; // state"
        ) + "\n本文由 AI 生成。\n"
        issues = "\n".join(lint_text(bad))
        self.assertIn("禁止 H1", issues)
        self.assertIn("缺少 ## 解题思路", issues)
        self.assertIn("不写注释", issues)
        self.assertIn("不用 dp", issues)
        self.assertIn("AI 署名", issues)

    def test_structure_only_defers_code_style(self) -> None:
        styled_elsewhere = GOOD.replace("int f[10];", "int dp[10]; // caller style")
        self.assertEqual(lint_text(styled_elsewhere, enforce_default_style=False), [])


if __name__ == "__main__":
    unittest.main()
