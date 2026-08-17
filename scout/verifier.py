# -*- coding: utf-8 -*-
"""并发验证 API 是否真的可用。

验证结果分为五类:
    OK        收到 2xx 响应 —— 可用
    REACHABLE 收到 4xx —— 服务器活着，但可能需要 key/参数，或路径已变
    ERROR     收到 5xx —— 服务端故障
    TIMEOUT   请求超时 —— 可能限流或很慢
    DEAD      无法建立连接 —— DNS 失败/连接被拒/SSL 错误等

要点:
    - 同一个 URL 只请求一次（列表里可能有重复条目）
    - 用 stream=True 只读一小段响应体做摘要，避免下载大文件
    - 并发数可调，避免把免费 API 打挂（做个文明用户）
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import time

import requests

USER_AGENT = "api-scout/1.0 (learning portfolio project)"

OK, REACHABLE, ERROR, TIMEOUT, DEAD = "OK", "REACHABLE", "ERROR", "TIMEOUT", "DEAD"


@dataclass
class VerifyResult:
    status: str
    http_code: int = 0
    ms: float = 0.0
    note: str = ""
    snippet: str = ""  # 响应体开头一小段，方便肉眼判断返回内容


def _read_snippet(resp, limit=120):
    """从流式响应里读一小段正文，压缩空白后返回。

    必须用 iter_content() 而不是 resp.raw.read()：
    iter_content 会自动解压 gzip/br 等压缩内容，raw 读到的是压缩前的字节。
    非 UTF-8 内容用替换字符容错解码，再把替换字符洗成 '?'，
    保证摘要可以安全打印到任何编码的控制台。
    """
    try:
        chunk = next(resp.iter_content(chunk_size=limit), b"")
        text = chunk.decode("utf-8", errors="replace")
        text = text.replace("\ufffd", "?")
        return " ".join(text.split())[:limit]
    except Exception:
        return ""


def check_one(url: str, timeout: float) -> VerifyResult:
    """探测单个 URL，返回分类结果。"""
    t0 = time.perf_counter()
    try:
        with requests.get(
            url,
            timeout=timeout,
            allow_redirects=True,  # 跟随 3xx 跳转
            headers={"User-Agent": USER_AGENT},
            stream=True,
        ) as resp:
            ms = (time.perf_counter() - t0) * 1000
            code = resp.status_code
            if 200 <= code < 300:
                return VerifyResult(OK, code, ms, f"HTTP {code}", _read_snippet(resp))
            if 400 <= code < 500:
                return VerifyResult(
                    REACHABLE, code, ms,
                    f"HTTP {code} (needs key/params or path changed)", _read_snippet(resp),
                )
            return VerifyResult(ERROR, code, ms, f"HTTP {code} (server error)", _read_snippet(resp))
    except requests.exceptions.Timeout:
        ms = (time.perf_counter() - t0) * 1000
        return VerifyResult(TIMEOUT, 0, ms, "request timed out")
    except requests.exceptions.RequestException as e:
        ms = (time.perf_counter() - t0) * 1000
        return VerifyResult(DEAD, 0, ms, type(e).__name__)


def verify_entries(entries, workers: int = 8, timeout: float = 6.0) -> dict:
    """并发验证一批条目，按 URL 去重。返回 {url: VerifyResult}。"""
    urls = list(dict.fromkeys(e.url for e in entries))  # 保序去重
    results = {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(check_one, u, timeout): u for u in urls}
        done = 0
        for fut in as_completed(futures):
            url = futures[fut]
            results[url] = fut.result()
            done += 1
            print(f"\r  verified {done}/{len(urls)}", end="", flush=True)
    print()
    return results


def summarize(results: dict) -> dict:
    """统计各类结果的数量。"""
    counts: dict = {}
    for r in results.values():
        counts[r.status] = counts.get(r.status, 0) + 1
    return counts
