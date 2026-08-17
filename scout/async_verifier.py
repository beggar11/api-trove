# -*- coding: utf-8 -*-
"""异步验证引擎（aiohttp）：比线程池更快、更省资源。

与 scout/verifier.py 的 check_one 分类规则完全一致（OK / REACHABLE /
ERROR / TIMEOUT / DEAD），只是底层 IO 换成 aiohttp + asyncio.Semaphore
限流。aiohttp 默认自动解压 gzip/br，且单连接复用（keep-alive）。

用法（由 main.py --engine async 调用）:
    from scout.async_verifier import verify_entries_async
    results = verify_entries_async(entries, workers=16, timeout=6.0)
"""
import asyncio
import time

import aiohttp

from scout.verifier import OK, REACHABLE, ERROR, TIMEOUT, DEAD, VerifyResult

USER_AGENT = "api-scout/async/1.0 (learning portfolio project)"


async def _read_snippet(resp, limit=120):
    """读响应体开头一小段（aiohttp 自动处理压缩）。"""
    try:
        chunk = await resp.content.read(limit)
        text = chunk.decode("utf-8", errors="replace")
        text = text.replace("\ufffd", "?")
        return " ".join(text.split())[:limit]
    except Exception:
        return ""


async def check_one_async(session, url: str, timeout: float) -> VerifyResult:
    """探测单个 URL（异步版），分类规则与线程版一致。"""
    t0 = time.perf_counter()
    try:
        async with session.get(
            url,
            timeout=aiohttp.ClientTimeout(total=timeout),
            allow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        ) as resp:
            ms = (time.perf_counter() - t0) * 1000
            code = resp.status
            if 200 <= code < 300:
                return VerifyResult(OK, code, ms, f"HTTP {code}", await _read_snippet(resp))
            if 400 <= code < 500:
                return VerifyResult(
                    REACHABLE, code, ms,
                    f"HTTP {code} (needs key/params or path changed)", await _read_snippet(resp),
                )
            return VerifyResult(ERROR, code, ms, f"HTTP {code} (server error)", await _read_snippet(resp))
    except asyncio.TimeoutError:
        ms = (time.perf_counter() - t0) * 1000
        return VerifyResult(TIMEOUT, 0, ms, "request timed out")
    except aiohttp.ClientError as e:
        ms = (time.perf_counter() - t0) * 1000
        return VerifyResult(DEAD, 0, ms, type(e).__name__)
    except Exception as e:  # 兜底：任何意外错误都按 DEAD 处理，不让单个失败中断整体
        ms = (time.perf_counter() - t0) * 1000
        return VerifyResult(DEAD, 0, ms, type(e).__name__)


async def _run(entries, workers: int, timeout: float) -> dict:
    """核心异步逻辑：信号量限流 + 并发探测，按 URL 去重。"""
    sem = asyncio.Semaphore(workers)
    urls = list(dict.fromkeys(e.url for e in entries))  # 保序去重

    async def one(url: str):
        async with sem:
            return url, await check_one_async(session, url, timeout)

    results = {}
    async with aiohttp.ClientSession() as session:
        tasks = [asyncio.create_task(one(u)) for u in urls]
        done = 0
        for coro in asyncio.as_completed(tasks):
            url, result = await coro
            results[url] = result
            done += 1
            print(f"\r  verified {done}/{len(urls)}", end="", flush=True)
    print()
    return results


def verify_entries_async(entries, workers: int = 16, timeout: float = 6.0) -> dict:
    """asyncio.run 包装，供同步代码直接调用。返回 {url: VerifyResult}。"""
    return asyncio.run(_run(entries, workers, timeout))
