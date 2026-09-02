from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from fetch import fetch_references, fetch_statement  # noqa: E402


class FetchPhaseTest(unittest.TestCase):
    def setUp(self) -> None:
        self.client = Mock()
        self.client.get_problem.return_value = {
            "pid": "P1001",
            "title": "A+B Problem",
            "limits": {},
            "samples": [],
        }

    def test_statement_phase_never_reads_existing_solutions(self) -> None:
        with tempfile.TemporaryDirectory() as directory, patch(
            "fetch.cache_dir", return_value=Path(directory)
        ), patch("fetch.load_config", return_value={"luogu": {"base_url": "https://www.luogu.com.cn"}}):
            fetch_statement("P1001", self.client)
            self.assertTrue((Path(directory) / "problem.md").exists())
            self.assertTrue((Path(directory) / "raw" / "problem.json").exists())
        self.client.get_all_solutions.assert_not_called()

    def test_reference_phase_requires_complete_independent_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as directory, patch(
            "fetch.cache_dir", return_value=Path(directory)
        ):
            (Path(directory) / "problem.md").write_text("# A+B Problem\n", encoding="utf-8")
            with self.assertRaisesRegex(Exception, "必须先独立完成 solution.cpp"):
                fetch_references("P1001", self.client)
        self.client.get_all_solutions.assert_not_called()

    def test_reference_phase_snapshots_before_network_read(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "problem.md").write_text("# A+B Problem\n", encoding="utf-8")
            (root / "solution.cpp").write_text("int main(){}\n", encoding="utf-8")
            (root / "solution.md").write_text("## 解题思路\n\n独立推导。\n", encoding="utf-8")

            def read_solutions(_pid: str):
                checkpoint = root / "raw" / "independent.json"
                self.assertTrue(checkpoint.exists())
                data = json.loads(checkpoint.read_text(encoding="utf-8"))
                self.assertIn("solution.cpp", data["artifacts"])
                self.assertIn("solution.md", data["artifacts"])
                return []

            self.client._cookie = "present"
            self.client.get_all_solutions.side_effect = read_solutions
            with patch("fetch.cache_dir", return_value=root), patch(
                "fetch.load_cookie", return_value="present"
            ):
                fetch_references("P1001", self.client)
            self.assertTrue((root / "references.md").exists())
            self.assertTrue((root / "raw" / "solutions.json").exists())

    def test_malformed_checkpoint_never_unlocks_references(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw_dir = root / "raw"
            raw_dir.mkdir()
            (root / "problem.md").write_text("# A+B Problem\n", encoding="utf-8")
            (root / "solution.cpp").write_text("int main(){}\n", encoding="utf-8")
            (root / "solution.md").write_text("## 解题思路\n\n独立推导。\n", encoding="utf-8")
            (raw_dir / "independent.json").write_text("{}\n", encoding="utf-8")
            with patch("fetch.cache_dir", return_value=root):
                with self.assertRaisesRegex(Exception, "检查点格式错误"):
                    fetch_references("P1001", self.client)
        self.client.get_all_solutions.assert_not_called()


if __name__ == "__main__":
    unittest.main()
