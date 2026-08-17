# -*- coding: utf-8 -*-
"""异步验证器的单元测试：用假 session 对象，不发真实请求。"""
import asyncio
import unittest

from scout.async_verifier import check_one_async
from scout.verifier import OK, REACHABLE, ERROR, TIMEOUT, DEAD


class FakeContent:
    """模拟 aiohttp 的响应内容（异步 read）。"""

    def __init__(self, body):
        self._body = body

    async def read(self, n=-1):
        if n == -1:
            return self._body
        return self._body[:n]


class FakeAsyncResponse:
    """模拟 aiohttp 的 ClientResponse（异步上下文管理器）。"""

    def __init__(self, status=200, body=b'{"ok": true}'):
        self.status = status
        self._body = body

    @property
    def content(self):
        return FakeContent(self._body)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False


class FakeErrorResponse:
    """模拟在进入响应上下文时抛异常（对应网络错误场景）。"""

    def __init__(self, exc):
        self._exc = exc

    async def __aenter__(self):
        raise self._exc

    async def __aexit__(self, *args):
        return False


class FakeSession:
    """模拟 aiohttp 的 ClientSession。

    注意：aiohttp 的 session.get 是普通方法，返回一个支持
    `async with` 的对象（_RequestContextManager），所以这里也用普通方法。
    """

    def __init__(self, status=200, body=b'{"ok": true}', exc=None):
        self._resp = FakeAsyncResponse(status, body)
        self._exc = exc

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    def get(self, *args, **kwargs):
        if self._exc:
            return FakeErrorResponse(self._exc)
        return self._resp


class TestAsyncVerifier(unittest.TestCase):

    def test_2xx_is_ok(self):
        r = asyncio.run(check_one_async(FakeSession(200), "https://x.example", 5))
        self.assertEqual(r.status, OK)
        self.assertEqual(r.http_code, 200)

    def test_4xx_is_reachable(self):
        r = asyncio.run(check_one_async(FakeSession(401), "https://x.example", 5))
        self.assertEqual(r.status, REACHABLE)

    def test_5xx_is_error(self):
        r = asyncio.run(check_one_async(FakeSession(503), "https://x.example", 5))
        self.assertEqual(r.status, ERROR)

    def test_timeout(self):
        r = asyncio.run(check_one_async(
            FakeSession(exc=asyncio.TimeoutError()), "https://x.example", 5))
        self.assertEqual(r.status, TIMEOUT)

    def test_connection_error_is_dead(self):
        import aiohttp
        r = asyncio.run(check_one_async(
            FakeSession(exc=aiohttp.ClientError("boom")), "https://x.example", 5))
        self.assertEqual(r.status, DEAD)

    def test_snippet_captured(self):
        r = asyncio.run(check_one_async(
            FakeSession(200, body=b'{"fact": "async cats"}'), "https://x.example", 5))
        self.assertIn("async cats", r.snippet)


if __name__ == "__main__":
    unittest.main()
