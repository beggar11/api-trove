# -*- coding: utf-8 -*-
"""验证器的单元测试：用 mock 模拟网络，不发起真实请求。"""
import unittest
from unittest import mock

import requests

from trove.verifier import check_one, OK, REACHABLE, ERROR, TIMEOUT, DEAD


class FakeResponse:
    """模拟 requests.get 的返回值（支持 with 语法 + stream 读取）。"""

    def __init__(self, status_code, body=b'{"ok": true}'):
        self.status_code = status_code
        self._body = body

    def iter_content(self, chunk_size=1):
        """模拟 requests 流式响应的分块读取。"""
        yield self._body[:chunk_size]

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class TestVerifier(unittest.TestCase):

    @mock.patch("trove.verifier.requests.get")
    def test_2xx_is_ok(self, mock_get):
        mock_get.return_value = FakeResponse(200)
        r = check_one("https://x.example", 5)
        self.assertEqual(r.status, OK)
        self.assertEqual(r.http_code, 200)

    @mock.patch("trove.verifier.requests.get")
    def test_4xx_is_reachable(self, mock_get):
        mock_get.return_value = FakeResponse(401)
        r = check_one("https://x.example", 5)
        self.assertEqual(r.status, REACHABLE)

    @mock.patch("trove.verifier.requests.get")
    def test_5xx_is_error(self, mock_get):
        mock_get.return_value = FakeResponse(503)
        r = check_one("https://x.example", 5)
        self.assertEqual(r.status, ERROR)

    @mock.patch("trove.verifier.requests.get")
    def test_timeout(self, mock_get):
        mock_get.side_effect = requests.exceptions.Timeout
        r = check_one("https://x.example", 5)
        self.assertEqual(r.status, TIMEOUT)

    @mock.patch("trove.verifier.requests.get")
    def test_connection_error_is_dead(self, mock_get):
        mock_get.side_effect = requests.exceptions.ConnectionError
        r = check_one("https://x.example", 5)
        self.assertEqual(r.status, DEAD)

    @mock.patch("trove.verifier.requests.get")
    def test_snippet_captured(self, mock_get):
        mock_get.return_value = FakeResponse(200, body=b'{"fact": "cats are cute"}')
        r = check_one("https://x.example", 5)
        self.assertIn("cats are cute", r.snippet)


if __name__ == "__main__":
    unittest.main()
