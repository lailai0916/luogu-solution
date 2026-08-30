from __future__ import annotations

import argparse
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from publish import _with_disclosure, main, publish_live  # noqa: E402


class PublishPolicyTest(unittest.TestCase):
    def test_agent_generated_is_blocked_without_account_exception(self) -> None:
        args = argparse.Namespace(
            eligibility="agent-generated",
            disclosure_file=None,
            confirm_account_exception=False,
        )
        with self.assertRaisesRegex(ValueError, "confirm-account-exception"):
            _with_disclosure({"content": "正文\n"}, args)

    def test_agent_generated_account_exception_is_allowed(self) -> None:
        args = argparse.Namespace(
            eligibility="agent-generated",
            disclosure_file=None,
            confirm_account_exception=True,
        )
        result = _with_disclosure({"content": "正文\n"}, args)
        self.assertEqual(result["content"], "正文\n")

    def test_agent_generated_exception_can_append_required_disclosure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "disclosure.md"
            path.write_text("披露。\n", encoding="utf-8")
            args = argparse.Namespace(
                eligibility="agent-generated",
                disclosure_file=str(path),
                confirm_account_exception=True,
            )
            result = _with_disclosure({"content": "正文\n"}, args)
        self.assertEqual(result["content"], "正文\n\n披露。\n")

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

    def test_account_exception_is_rejected_for_other_origins(self) -> None:
        args = argparse.Namespace(
            eligibility="editorial-ai",
            disclosure_file=None,
            confirm_account_exception=True,
        )
        with self.assertRaisesRegex(ValueError, "仅适用于 agent-generated"):
            _with_disclosure({"content": "正文\n"}, args)

    def test_missing_policy_confirmation_blocks_before_client_creation(self) -> None:
        with patch("publish.LuoguClient") as client:
            with self.assertRaisesRegex(ValueError, "confirm-current-policy"):
                publish_live(
                    {"pid": "P1001"},
                    submit_review=True,
                    policy_checked=False,
                )
        client.assert_not_called()

    def test_main_blocks_missing_policy_before_loading_source(self) -> None:
        with patch("publish.load_source") as load_source, patch("publish.publish_live") as live:
            result = main([
                "publish.py",
                "P1001",
                "--live",
                "--submit-review",
                "--eligibility",
                "agent-generated",
                "--confirm-account-exception",
            ])
        self.assertEqual(result, 2)
        load_source.assert_not_called()
        live.assert_not_called()

    @patch("publish._save_metadata")
    @patch("publish.load_config")
    @patch("publish.LuoguClient")
    def test_publish_forces_top_two_and_verifies_read_back(
        self,
        client_class,
        load_config,
        save_metadata,
    ) -> None:
        load_config.return_value = {
            "luogu": {"article": {"category": 2, "status": 2, "top": 0}}
        }
        client = client_class.return_value
        client.check_login.return_value = {"logged_in": True}
        client.get_article.side_effect = [
            {"title": "旧标题", "category": 2, "status": 2, "top": 0},
            {"content": "正文\n", "contentFull": True, "top": 2},
        ]
        source = {
            "pid": "P1001",
            "lid": "abcdefgh",
            "title": "题解：P1001",
            "title_override": False,
            "content": "正文\n",
        }
        result = publish_live(source, submit_review=False, policy_checked=False)
        self.assertEqual(result, 0)
        payload = client.update_article.call_args.args[1]
        self.assertEqual(payload["top"], 2)
        save_metadata.assert_called_once()


if __name__ == "__main__":
    unittest.main()
