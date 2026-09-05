from __future__ import annotations

import argparse
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from gates import require_matching_accepted_record  # noqa: E402
from luogu_client import LuoguError  # noqa: E402
from publish import (  # noqa: E402
    _with_disclosure,
    hide_live,
    main,
    publish_live,
    retire_live,
    restore_public_live,
    save_hidden_live,
    save_public_live,
)


class PublishPolicyTest(unittest.TestCase):
    @patch("publish._save_metadata")
    @patch("publish.load_config")
    def test_hide_preserves_content_and_forces_personal_hidden(
        self,
        load_config,
        save_metadata,
    ) -> None:
        load_config.return_value = {"luogu": {"article": {"category": 2}}}
        current = {
            "lid": "abcdefgh",
            "title": "题解：P1001 A+B Problem",
            "content": "旧正文",
            "contentFull": True,
            "solutionFor": {"pid": "P1001"},
            "category": 2,
            "status": 2,
            "top": 0,
        }
        hidden = {**current, "status": 1, "top": 2}
        client = Mock(spec=["check_login", "get_article", "update_article"])
        client.check_login.return_value = {"logged_in": True}
        client.get_article.side_effect = [current, hidden]
        result = hide_live("P1001", "abcdefgh", client=client)
        self.assertEqual(result, 0)
        payload = client.update_article.call_args.args[1]
        self.assertEqual(payload["content"], "旧正文")
        self.assertEqual(payload["status"], 1)
        self.assertEqual(payload["top"], 2)
        save_metadata.assert_called_once()

    def test_hide_rejects_wrong_binding_before_write(self) -> None:
        client = Mock(spec=["check_login", "get_article", "update_article"])
        client.check_login.return_value = {"logged_in": True}
        client.get_article.return_value = {
            "contentFull": True,
            "solutionFor": {"pid": "P2000"},
        }
        with self.assertRaisesRegex(Exception, "P2000"):
            hide_live("P1001", "abcdefgh", client=client)
        client.update_article.assert_not_called()

    @patch("publish._save_metadata")
    @patch("publish.load_config")
    def test_hide_recovers_ambiguous_write_only_after_exact_read_back(
        self,
        load_config,
        save_metadata,
    ) -> None:
        load_config.return_value = {"luogu": {"article": {"category": 2}}}
        current = {
            "lid": "abcdefgh",
            "title": "题解：P1001 A+B Problem",
            "content": "正文",
            "contentFull": True,
            "solutionFor": {"pid": "P1001"},
            "category": 2,
            "status": 2,
            "top": 2,
        }
        hidden = {**current, "status": 1}
        client = Mock(spec=["check_login", "get_article", "update_article"])
        client.check_login.return_value = {"logged_in": True}
        client.get_article.side_effect = [current, hidden]
        client.update_article.side_effect = LuoguError("HTTP 500")
        self.assertEqual(hide_live("P1001", "abcdefgh", client=client), 0)
        client.update_article.assert_called_once()
        self.assertEqual(client.get_article.call_count, 2)
        save_metadata.assert_called_once()

    @patch("publish.load_config")
    def test_hide_does_not_accept_whitespace_only_read_back_mismatch(
        self,
        load_config,
    ) -> None:
        load_config.return_value = {"luogu": {"article": {"category": 2}}}
        current = {
            "lid": "abcdefgh",
            "title": "题解：P1001 A+B Problem",
            "content": "正文",
            "contentFull": True,
            "solutionFor": {"pid": "P1001"},
            "category": 2,
            "status": 2,
            "top": 2,
        }
        hidden = {**current, "content": "正文 ", "status": 1}
        client = Mock(spec=["check_login", "get_article", "update_article"])
        client.check_login.return_value = {"logged_in": True}
        client.get_article.side_effect = [current, hidden]
        client.update_article.side_effect = LuoguError("HTTP 500")
        with self.assertRaisesRegex(LuoguError, "HTTP 500"):
            hide_live("P1001", "abcdefgh", client=client)

    @patch("publish._save_metadata")
    @patch("publish.load_config")
    @patch("publish.require_article_code_matches_source")
    @patch("publish.require_local_verification")
    @patch("publish.require_originality_audit")
    @patch("publish.check_candidate")
    def test_save_hidden_updates_only_bound_article_without_review(
        self,
        candidate_gate,
        originality_gate,
        local_verification_gate,
        article_code_gate,
        load_config,
        save_metadata,
    ) -> None:
        load_config.return_value = {"luogu": {"article": {"category": 2}}}
        current = {
            "lid": "abcdefgh",
            "title": "题解：P1001 A+B Problem",
            "content": "旧正文",
            "contentFull": True,
            "solutionFor": {"pid": "P1001"},
            "category": 2,
            "status": 2,
            "top": 2,
        }
        hidden = {**current, "content": "新正文", "status": 1}
        client = Mock(
            spec=[
                "check_login",
                "get_article",
                "update_article",
                "create_article",
                "request_solution_review",
            ]
        )
        client.check_login.return_value = {"logged_in": True}
        client.get_article.side_effect = [current, hidden]
        source = {
            "pid": "P1001",
            "lid": "abcdefgh",
            "title": "不会覆盖线上标题",
            "title_override": False,
            "content": "新正文",
        }
        result = save_hidden_live(source, client=client)
        self.assertEqual(result, 0)
        payload = client.update_article.call_args.args[1]
        self.assertEqual(payload["status"], 1)
        self.assertEqual(payload["content"], "新正文")
        self.assertEqual(payload["title"], current["title"])
        client.create_article.assert_not_called()
        client.request_solution_review.assert_not_called()
        candidate_gate.assert_not_called()
        originality_gate.assert_called_once()
        local_verification_gate.assert_called_once()
        article_code_gate.assert_called_once()
        save_metadata.assert_called_once()

    def test_save_hidden_requires_existing_lid_before_network(self) -> None:
        with patch("publish.require_originality_audit") as originality_gate, patch(
            "publish.require_local_verification"
        ) as local_verification_gate:
            with self.assertRaisesRegex(ValueError, "既有 lid"):
                save_hidden_live({"pid": "P1001", "lid": None, "content": "正文"})
        originality_gate.assert_not_called()
        local_verification_gate.assert_not_called()

    @patch("publish._save_metadata")
    @patch("publish.load_config")
    def test_restore_public_preserves_unpublished_article_verbatim(
        self,
        load_config,
        save_metadata,
    ) -> None:
        load_config.return_value = {"luogu": {"article": {"category": 2}}}
        current = {
            "lid": "abcdefgh",
            "title": "题解：P1001 A+B Problem",
            "content": "现有正文",
            "contentFull": True,
            "solutionFor": {"pid": "P1001"},
            "category": 2,
            "status": 1,
            "top": 2,
            "promoteStatus": 0,
        }
        public = {**current, "status": 2}
        client = Mock(spec=["check_login", "get_article", "update_article"])
        client.check_login.return_value = {"logged_in": True}
        client.get_article.side_effect = [current, public]
        self.assertEqual(restore_public_live("P1001", "abcdefgh", client=client), 0)
        payload = client.update_article.call_args.args[1]
        self.assertEqual(payload["content"], current["content"])
        self.assertEqual(payload["status"], 2)
        self.assertEqual(payload["top"], 2)
        save_metadata.assert_called_once()

    def test_restore_public_rejects_pending_or_accepted_review(self) -> None:
        client = Mock(spec=["check_login", "get_article", "update_article"])
        client.check_login.return_value = {"logged_in": True}
        client.get_article.return_value = {
            "title": "题解：P1001",
            "content": "正文",
            "contentFull": True,
            "solutionFor": "P1001",
            "category": 2,
            "status": 1,
            "top": 2,
            "promoteStatus": 1,
        }
        with self.assertRaisesRegex(Exception, "不是未投稿或已拒绝"):
            restore_public_live("P1001", "abcdefgh", client=client)
        client.update_article.assert_not_called()

    @patch("publish._save_metadata")
    @patch("publish.load_config")
    @patch("publish.require_article_code_matches_source")
    @patch("publish.require_local_verification")
    @patch("publish.require_originality_audit")
    def test_save_public_updates_bound_article_without_review(
        self,
        originality_gate,
        local_verification_gate,
        article_code_gate,
        load_config,
        save_metadata,
    ) -> None:
        load_config.return_value = {"luogu": {"article": {"category": 2}}}
        current = {
            "lid": "abcdefgh",
            "title": "题解：P1001 A+B Problem",
            "content": "旧正文",
            "contentFull": True,
            "solutionFor": {"pid": "P1001"},
            "category": 2,
            "status": 1,
            "top": 2,
            "promoteStatus": 0,
        }
        public = {**current, "content": "新正文", "status": 2}
        client = Mock(
            spec=[
                "check_login",
                "get_article",
                "update_article",
                "create_article",
                "request_solution_review",
            ]
        )
        client.check_login.return_value = {"logged_in": True}
        client.get_article.side_effect = [current, public]
        source = {
            "pid": "P1001",
            "lid": "abcdefgh",
            "title": "不会覆盖线上标题",
            "title_override": False,
            "content": "新正文",
        }
        self.assertEqual(save_public_live(source, client=client), 0)
        payload = client.update_article.call_args.args[1]
        self.assertEqual(payload["content"], "新正文")
        self.assertEqual(payload["status"], 2)
        self.assertEqual(payload["title"], current["title"])
        client.create_article.assert_not_called()
        client.request_solution_review.assert_not_called()
        originality_gate.assert_called_once()
        local_verification_gate.assert_called_once()
        article_code_gate.assert_called_once()
        save_metadata.assert_called_once()

    @patch("publish._save_metadata")
    @patch("publish.load_config")
    def test_retire_clears_body_and_preserves_original_article(
        self,
        load_config,
        save_metadata,
    ) -> None:
        load_config.return_value = {"luogu": {"article": {"category": 2, "status": 2}}}
        client = Mock()
        client.check_login.return_value = {"logged_in": True}
        client.get_article.side_effect = [
            {
                "lid": "abcdefgh",
                "title": "题解：P1001 A+B Problem",
                "content": "旧正文",
                "contentFull": True,
                "solutionFor": {"pid": "P1001"},
                "category": 2,
                "status": 2,
                "top": 2,
            },
            {
                "lid": "abcdefgh",
                "title": "题解：P1001 A+B Problem",
                "content": "",
                "contentFull": True,
                "solutionFor": {"pid": "P1001"},
                "category": 2,
                "status": 2,
                "top": 2,
            },
        ]
        result = retire_live("P1001", "abcdefgh", client=client)
        self.assertEqual(result, 0)
        payload = client.update_article.call_args.args[1]
        self.assertEqual(payload["content"], "")
        self.assertEqual(payload["title"], "题解：P1001 A+B Problem")
        self.assertEqual(payload["top"], 2)
        save_metadata.assert_called_once()

    @patch("publish._save_metadata")
    @patch("publish.load_config")
    def test_retire_uses_explicit_minimal_placeholder_after_empty_rejection(
        self,
        load_config,
        save_metadata,
    ) -> None:
        load_config.return_value = {"luogu": {"article": {"category": 2, "status": 2}}}
        client = Mock(spec=["check_login", "get_article", "update_article"])
        client.check_login.return_value = {"logged_in": True}
        client.get_article.side_effect = [
            {
                "title": "题解：P1001",
                "solutionFor": "P1001",
                "category": 2,
                "status": 2,
                "top": 2,
            },
            {
                "lid": "abcdefgh",
                "title": "题解：P1001",
                "content": "待修正",
                "contentFull": True,
                "solutionFor": "P1001",
                "category": 2,
                "status": 2,
                "top": 2,
            },
        ]
        result = retire_live(
            "P1001",
            "abcdefgh",
            placeholder="待修正",
            client=client,
        )
        self.assertEqual(result, 0)
        self.assertEqual(client.update_article.call_args.args[1]["content"], "待修正")
        save_metadata.assert_called_once()

    def test_retire_rejects_unbound_or_wrong_article_before_write(self) -> None:
        client = Mock(spec=["check_login", "get_article", "update_article"])
        client.check_login.return_value = {"logged_in": True}
        client.get_article.return_value = {
            "title": "普通文章",
            "solutionFor": None,
        }
        with self.assertRaisesRegex(Exception, "未知题号"):
            retire_live("P1001", "abcdefgh", client=client)
        client.update_article.assert_not_called()

    def test_retire_rejects_nonminimal_placeholder_before_write(self) -> None:
        client = Mock(spec=["check_login", "get_article", "update_article"])
        client.check_login.return_value = {"logged_in": True}
        client.get_article.return_value = {
            "title": "题解：P1001",
            "solutionFor": "P1001",
        }
        with self.assertRaisesRegex(ValueError, "1 至 10"):
            retire_live("P1001", "abcdefgh", placeholder="这不是一个最短占位正文", client=client)
        client.update_article.assert_not_called()

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

    @patch("publish.require_originality_audit")
    def test_originality_gate_runs_before_client_creation(self, originality_gate) -> None:
        originality_gate.side_effect = RuntimeError("原创性审计失效")
        with patch("publish.LuoguClient") as client:
            with self.assertRaisesRegex(RuntimeError, "原创性审计"):
                publish_live(
                    {"pid": "P1001"},
                    submit_review=False,
                    policy_checked=False,
                )
        client.assert_not_called()

    @patch("publish.require_local_verification")
    @patch("publish.require_originality_audit")
    def test_local_verification_gate_runs_before_client_creation(
        self,
        originality_gate,
        local_verification_gate,
    ) -> None:
        local_verification_gate.side_effect = RuntimeError("本地验证失效")
        with patch("publish.LuoguClient") as client:
            with self.assertRaisesRegex(RuntimeError, "本地验证"):
                publish_live(
                    {"pid": "P1001"},
                    submit_review=False,
                    policy_checked=False,
                )
        originality_gate.assert_called_once()
        client.assert_not_called()

    @patch("publish.require_article_code_matches_source")
    @patch("publish.require_local_verification")
    @patch("publish.require_originality_audit")
    def test_article_code_gate_runs_before_client_creation(
        self,
        originality_gate,
        local_verification_gate,
        article_code_gate,
    ) -> None:
        article_code_gate.side_effect = RuntimeError("参考代码不一致")
        with patch("publish.LuoguClient") as client:
            with self.assertRaisesRegex(RuntimeError, "参考代码"):
                publish_live(
                    {"pid": "P1001", "content": "正文\n"},
                    submit_review=False,
                    policy_checked=False,
                )
        originality_gate.assert_called_once()
        local_verification_gate.assert_called_once()
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

    @patch("publish.LuoguClient")
    @patch("publish.require_matching_accepted_record", return_value={"id": 123})
    @patch("publish.require_article_code_matches_source")
    @patch("publish.require_local_verification")
    @patch("publish.require_originality_audit")
    def test_closed_solution_channel_blocks_before_article_write(
        self,
        originality_gate,
        local_verification_gate,
        article_code_gate,
        accepted_gate,
        client_class,
    ) -> None:
        client = client_class.return_value
        client.check_login.return_value = {"logged_in": True}
        client.get_problem.return_value = {
            "pid": "P1001",
            "title": "A+B Problem",
            "type": "P",
            "difficulty": 7,
            "acceptSolution": False,
        }
        with self.assertRaisesRegex(Exception, "当前不接受新题解"):
            publish_live(
                {"pid": "P1001", "content": "正文\n"},
                submit_review=True,
                policy_checked=True,
            )
        client.check_login.assert_called_once()
        client.create_article.assert_not_called()
        client.update_article.assert_not_called()

    @patch("publish.require_matching_accepted_record")
    @patch("publish.LuoguClient")
    @patch("publish.require_article_code_matches_source")
    @patch("publish.require_local_verification")
    @patch("publish.require_originality_audit")
    def test_missing_exact_source_acceptance_blocks_before_article_write(
        self,
        originality_gate,
        local_verification_gate,
        article_code_gate,
        client_class,
        accepted_gate,
    ) -> None:
        client = client_class.return_value
        client.check_login.return_value = {"logged_in": True}
        accepted_gate.side_effect = RuntimeError("没有匹配的 Accepted 记录")
        with self.assertRaisesRegex(RuntimeError, "Accepted"):
            publish_live(
                {"pid": "P1001", "lid": "abcdefgh", "content": "正文\n"},
                submit_review=True,
                policy_checked=True,
            )
        client.get_problem.assert_not_called()
        client.get_article.assert_not_called()
        client.create_article.assert_not_called()
        client.update_article.assert_not_called()
        client.request_solution_review.assert_not_called()

    def test_exact_source_acceptance_helper_uses_cached_solution(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            problem_dir = Path(directory) / "P1001"
            problem_dir.mkdir()
            (problem_dir / "solution.cpp").write_text("int main() {}\n", encoding="utf-8")
            client = Mock()
            client.find_matching_accepted_record.return_value = {"id": 123}
            record = require_matching_accepted_record(
                "P1001",
                problem_dir,
                "## 参考代码\n\n```cpp\nint main() {}\n```\n",
                client,
            )
        self.assertEqual(record["id"], 123)
        client.find_matching_accepted_record.assert_called_once_with(
            "P1001",
            "int main() {}\n",
        )

    def test_exact_source_acceptance_helper_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            problem_dir = Path(directory) / "P1001"
            problem_dir.mkdir()
            (problem_dir / "solution.cpp").write_text("int main() {}\n", encoding="utf-8")
            client = Mock()
            client.find_matching_accepted_record.return_value = None
            with self.assertRaisesRegex(Exception, "源码一致.*Accepted"):
                require_matching_accepted_record(
                    "P1001",
                    problem_dir,
                    "## 参考代码\n\n```cpp\nint main() {}\n```\n",
                    client,
                )

    def test_article_reference_code_must_equal_accepted_source(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            problem_dir = Path(directory) / "P1001"
            problem_dir.mkdir()
            (problem_dir / "solution.cpp").write_text("int main() {}\n", encoding="utf-8")
            client = Mock()
            with self.assertRaisesRegex(Exception, "参考代码.*solution.cpp 不一致"):
                require_matching_accepted_record(
                    "P1001",
                    problem_dir,
                    "## 参考代码\n\n```cpp\nint main() { return 0; }\n```\n",
                    client,
                )
        client.find_matching_accepted_record.assert_not_called()

    @patch("publish.require_article_code_matches_source")
    @patch("publish.require_local_verification")
    @patch("publish.require_originality_audit")
    @patch("publish.LuoguClient")
    def test_publish_rejects_wrong_article_binding_before_write(
        self,
        client_class,
        originality_gate,
        local_verification_gate,
        article_code_gate,
    ) -> None:
        client = client_class.return_value
        client.check_login.return_value = {"logged_in": True}
        client.get_article.return_value = {
            "contentFull": True,
            "solutionFor": {"pid": "P2000"},
        }
        source = {
            "pid": "P1001",
            "lid": "abcdefgh",
            "title": "题解：P1001",
            "title_override": False,
            "content": "正文\n",
        }
        with self.assertRaisesRegex(Exception, "P2000"):
            publish_live(source, submit_review=False, policy_checked=False)
        client.update_article.assert_not_called()
        client.create_article.assert_not_called()

    @patch("publish._save_metadata")
    @patch("publish.load_config")
    @patch("publish.require_article_code_matches_source")
    @patch("publish.require_local_verification")
    @patch("publish.require_originality_audit")
    @patch("publish.LuoguClient")
    def test_publish_read_back_checks_article_binding(
        self,
        client_class,
        originality_gate,
        local_verification_gate,
        article_code_gate,
        load_config,
        save_metadata,
    ) -> None:
        load_config.return_value = {
            "luogu": {"article": {"category": 2, "status": 2}}
        }
        current = {
            "title": "题解：P1001",
            "content": "旧正文",
            "contentFull": True,
            "solutionFor": {"pid": "P1001"},
            "category": 2,
            "status": 2,
            "top": 2,
        }
        client = client_class.return_value
        client.check_login.return_value = {"logged_in": True}
        client.get_article.side_effect = [
            current,
            {
                **current,
                "content": "正文\n",
                "solutionFor": {"pid": "P2000"},
            },
        ]
        source = {
            "pid": "P1001",
            "lid": "abcdefgh",
            "title": "题解：P1001",
            "title_override": False,
            "content": "正文\n",
        }
        self.assertEqual(
            publish_live(source, submit_review=False, policy_checked=False),
            1,
        )
        save_metadata.assert_not_called()

    @patch("publish._save_metadata")
    @patch("publish.load_config")
    @patch("publish.require_matching_accepted_record", return_value={"id": 123})
    @patch("publish.require_article_code_matches_source")
    @patch("publish.require_local_verification")
    @patch("publish.require_originality_audit")
    @patch("publish.LuoguClient")
    def test_review_request_is_confirmed_by_read_back(
        self,
        client_class,
        originality_gate,
        local_verification_gate,
        article_code_gate,
        accepted_gate,
        load_config,
        save_metadata,
    ) -> None:
        load_config.return_value = {
            "luogu": {"article": {"category": 2, "status": 2}}
        }
        current = {
            "title": "题解：P1001",
            "content": "旧正文",
            "contentFull": True,
            "solutionFor": {"pid": "P1001"},
            "category": 2,
            "status": 2,
            "top": 2,
            "promoteStatus": 0,
        }
        published = {**current, "content": "正文\n"}
        pending = {**published, "promoteStatus": 1}
        client = client_class.return_value
        client.check_login.return_value = {"logged_in": True}
        client.get_problem.return_value = {"acceptSolution": True}
        client.get_article.side_effect = [current, published, pending]
        source = {
            "pid": "P1001",
            "lid": "abcdefgh",
            "title": "题解：P1001",
            "title_override": False,
            "content": "正文\n",
        }
        self.assertEqual(
            publish_live(source, submit_review=True, policy_checked=True),
            0,
        )
        client.request_solution_review.assert_called_once_with("abcdefgh")
        self.assertEqual(client.get_article.call_count, 3)
        self.assertEqual(save_metadata.call_count, 2)

    @patch("publish._save_metadata")
    @patch("publish.load_config")
    @patch("publish.LuoguClient")
    @patch("publish.require_article_code_matches_source")
    @patch("publish.require_local_verification")
    @patch("publish.require_originality_audit")
    def test_publish_forces_top_two_and_verifies_read_back(
        self,
        originality_gate,
        local_verification_gate,
        article_code_gate,
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
            {
                "title": "旧标题",
                "content": "旧正文",
                "contentFull": True,
                "solutionFor": {"pid": "P1001"},
                "category": 2,
                "status": 2,
                "top": 0,
            },
            {
                "title": "旧标题",
                "content": "正文\n",
                "contentFull": True,
                "solutionFor": {"pid": "P1001"},
                "category": 2,
                "status": 2,
                "top": 2,
            },
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

    @patch("publish.check_candidate")
    @patch("publish.load_config")
    @patch("publish.LuoguClient")
    @patch("publish.require_article_code_matches_source")
    @patch("publish.require_local_verification")
    @patch("publish.require_originality_audit")
    def test_new_article_runs_candidate_gate_before_write(
        self,
        originality_gate,
        local_verification_gate,
        article_code_gate,
        client_class,
        load_config,
        check_candidate,
    ) -> None:
        load_config.return_value = {
            "luogu": {"article": {"category": 2, "status": 2, "top": 2}}
        }
        client = client_class.return_value
        client.check_login.return_value = {"logged_in": True}
        check_candidate.side_effect = ValueError("候选不合格")
        source = {
            "pid": "P1001",
            "lid": None,
            "title": "题解：P1001",
            "title_override": False,
            "content": "正文\n",
        }
        with self.assertRaisesRegex(ValueError, "候选不合格"):
            publish_live(source, submit_review=False, policy_checked=False)
        client.create_article.assert_not_called()
        client.update_article.assert_not_called()


if __name__ == "__main__":
    unittest.main()
