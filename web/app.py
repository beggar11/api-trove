# -*- coding: utf-8 -*-
"""api-scout Web UI —— Flask 后端 + 静态前端。

运行:
    pip install flask requests
    python web/app.py
浏览器打开: http://127.0.0.1:5055

接口:
    GET  /                前端页面
    GET  /api/categories  分类列表（含数量）
    GET  /api/apis        按条件检索（keyword/category/auth/cors/https/limit）
    POST /api/verify      并发验证一批 URL（单次上限 100 个）
"""
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests as http
from flask import Flask, jsonify, request, send_from_directory

# 让 web/app.py 能找到上一级的 scout 包
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scout.filter import apply as apply_filters
from scout.parser import parse_readme
from scout.verifier import check_one

app = Flask(__name__, static_folder="static", static_url_path="")

CACHE = {"entries": [], "fetched": 0.0}
CACHE_TTL = 3600          # README 缓存 1 小时
MAX_VERIFY = 100          # 单次验证上限，避免请求太久
MAX_WORKERS = 16


def load_entries():
    """优先读本地 public-apis 克隆，否则从 GitHub 拉最新 README（带缓存）。"""
    if CACHE["entries"] and time.time() - CACHE["fetched"] < CACHE_TTL:
        return CACHE["entries"]
    local = Path(__file__).resolve().parents[2] / "public-apis" / "README.md"
    if local.exists():
        text = local.read_text(encoding="utf-8")
    else:
        url = "https://raw.githubusercontent.com/public-apis/public-apis/master/README.md"
        text = http.get(url, timeout=20).text
    entries = parse_readme(text)
    CACHE["entries"], CACHE["fetched"] = entries, time.time()
    return entries


@app.get("/")
def index():
    return send_from_directory("static", "index.html")


@app.get("/api/categories")
def categories():
    counts = {}
    for e in load_entries():
        counts[e.category] = counts.get(e.category, 0) + 1
    items = [{"name": n, "count": c} for n, c in counts.items()]
    items.sort(key=lambda x: -x["count"])
    return jsonify(items)


@app.get("/api/apis")
def apis():
    entries = load_entries()
    limit = request.args.get("limit", type=int) or None
    hits = apply_filters(
        entries,
        keyword=request.args.get("keyword"),
        category=request.args.get("category"),
        auth=request.args.get("auth"),
        cors=request.args.get("cors"),
        https=request.args.get("https"),
        limit=limit,
    )
    return jsonify([e.__dict__ for e in hits])


@app.post("/api/verify")
def verify():
    payload = request.get_json(silent=True) or {}
    urls = list(dict.fromkeys(payload.get("urls") or []))[:MAX_VERIFY]
    if not urls:
        return jsonify({"error": "no urls provided"}), 400
    workers = min(int(payload.get("workers") or 8), MAX_WORKERS)
    timeout = min(float(payload.get("timeout") or 6.0), 15.0)

    results = {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(check_one, u, timeout): u for u in urls}
        for fut in as_completed(futures):
            u = futures[fut]
            r = fut.result()
            results[u] = {
                "status": r.status,
                "http_code": r.http_code,
                "ms": round(r.ms),
                "note": r.note,
            }
    return jsonify(results)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5055))
    print(f"api-scout Web UI -> http://127.0.0.1:{port}")
    app.run(host="127.0.0.1", port=port, debug=False)
