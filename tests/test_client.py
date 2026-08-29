from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import Mock

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from luogu_client import LuoguClient  # noqa: E402


class ClientEndpointTest(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
