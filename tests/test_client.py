from __future__ import annotations

import json
import sys
import unittest
import urllib.parse
from pathlib import Path
from unittest.mock import Mock, patch

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from luogu_client import (  # noqa: E402
    MIN_REQUEST_INTERVAL,
    MIN_WRITE_REQUEST_INTERVAL,
    LuoguClient,
    LuoguError,
)


class ClientEndpointTest(unittest.TestCase):
    def test_article_deletion_is_not_exposed(self) -> None:
        self.assertFalse(hasattr(LuoguClient, "delete_article"))

    def setUp(self) -> None:
        self.client = LuoguClient(cookie="_uid=x")
        self.client.base_url = "https://www.luogu.com.cn"
        self.client.get_csrf_token = Mock(return_value="csrf")
        self.client._post_json = Mock(return_value={"article": {"lid": "abc"}})

    def test_create_article_endpoint(self) -> None:
        self.client._post_json.return_value = {"data": {"article": {"lid": "abc"}}}
        result = self.client.create_article({"title": "x"})
        self.assertEqual(result["lid"], "abc")
        self.client._post_json.assert_called_once_with(
            "https://www.luogu.com.cn/article/_newSubmit",
            {"title": "x"},
            csrf="csrf",
            referer="https://www.luogu.com.cn/article/_new",
        )

    def test_request_solution_review_endpoint(self) -> None:
        self.client.request_solution_review("abc")
        self.client._post_json.assert_called_once_with(
            "https://www.luogu.com.cn/article/abc/requestPromotion",
            {},
            csrf="csrf",
            referer="https://www.luogu.com.cn/article/abc/edit",
        )

    def test_classic_page_data_is_decoded(self) -> None:
        payload = {"code": 200, "currentData": {"record": {"id": 123}}}
        encoded = urllib.parse.quote(json.dumps(payload))
        response = Mock(
            status_code=200,
            text=(
                '<script>window._feInjection = JSON.parse(decodeURIComponent("'
                f'{encoded}"))</script>'
            ),
        )
        self.client.session.get = Mock(return_value=response)
        self.client.request_delay = 0
        result = self.client._get_fe_data("https://www.luogu.com.cn/record/123")
        self.assertEqual(result, {"record": {"id": 123}})

    def test_hard_rate_limit_cannot_be_disabled(self) -> None:
        self.client.request_delay = 0
        self.client.write_request_delay = 0
        LuoguClient._last_request_at = 0
        monotonic = [100.0, 100.0, 100.2, 101.0, 101.1, 103.0]
        with patch("luogu_client.time.monotonic", side_effect=monotonic):
            with patch("luogu_client.time.sleep") as sleep:
                with self.client._request_slot():
                    pass
                with self.client._request_slot():
                    pass
                with self.client._request_slot(write=True):
                    pass
        self.assertEqual(sleep.call_count, 2)
        self.assertAlmostEqual(sleep.call_args_list[0].args[0], MIN_REQUEST_INTERVAL - 0.2)
        self.assertAlmostEqual(sleep.call_args_list[1].args[0], MIN_WRITE_REQUEST_INTERVAL - 0.1)

    def test_matching_accepted_record_requires_same_account_pid_and_source(self) -> None:
        self.client._uid = "12345"
        self.client.get_record_page = Mock(return_value={
            "result": [{
                "id": 456,
                "status": 12,
                "problem": {"pid": "P1001"},
                "user": {"uid": 12345},
            }],
            "count": 1,
            "perPage": 20,
        })
        self.client.get_record = Mock(return_value={
            "id": 456,
            "status": 12,
            "problem": {"pid": "P1001"},
            "user": {"uid": 12345},
            "sourceCode": "int main() {}\r\n",
        })
        record = self.client.find_matching_accepted_record("P1001", "int main() {}\n")
        self.assertEqual(record["id"], 456)

    def test_different_source_does_not_satisfy_accepted_gate(self) -> None:
        self.client._uid = "12345"
        self.client.get_record_page = Mock(return_value={
            "result": [{
                "id": 456,
                "status": 12,
                "problem": {"pid": "P1001"},
                "user": {"uid": 12345},
            }],
            "count": 1,
            "perPage": 20,
        })
        self.client.get_record = Mock(return_value={
            "id": 456,
            "status": 12,
            "problem": {"pid": "P1001"},
            "user": {"uid": 12345},
            "sourceCode": "int main() { return 0; }\n",
        })
        record = self.client.find_matching_accepted_record("P1001", "int main() {}\n")
        self.assertIsNone(record)

    def test_solution_list_parse_failure_is_not_treated_as_zero(self) -> None:
        self.client._get_json = Mock(return_value={"solutions": "broken"})
        with self.assertRaisesRegex(LuoguError, "题解列表解析失败"):
            self.client.get_solution_count("P1001")

    def test_incomplete_article_history_fails_closed(self) -> None:
        self.client.get_my_article_page = Mock(return_value={
            "result": [],
            "count": 1,
            "perPage": 25,
        })
        with self.assertRaisesRegex(LuoguError, "分页内容不完整"):
            self.client.find_my_solution_articles("P1001")

    def test_partial_article_history_page_fails_closed(self) -> None:
        self.client.get_my_article_page = Mock(return_value={
            "result": [{"solutionFor": {"pid": "P2000"}}],
            "count": 30,
            "perPage": 25,
        })
        with self.assertRaisesRegex(LuoguError, "分页内容不完整"):
            self.client.find_my_solution_articles("P1001")

    def test_article_history_requires_pagination_metadata(self) -> None:
        self.client.get_my_article_page = Mock(return_value={
            "result": [],
        })
        with self.assertRaisesRegex(LuoguError, "分页字段异常"):
            self.client.find_my_solution_articles("P1001")


if __name__ == "__main__":
    unittest.main()
