# -*- coding: utf-8 -*-
"""api-trove Web UI —— Flask 后端 + 静态前端。

本地开发:
    pip install -r requirements.txt
    python web/app.py          # http://127.0.0.1:5055

生产部署（Render，见根目录 render.yaml）:
    gunicorn web.app:app --timeout 120
    # Render 会注入 PORT 环境变量；gunicorn 默认绑定 0.0.0.0

接口:
    GET  /                前端页面
    GET  /api/categories  分类列表（含数量）
    GET  /api/apis        按条件检索（keyword/category/auth/cors/https/limit）
    POST /api/verify      并发验证一批 URL（单次上限 100 个）
"""
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests as http
from flask import Flask, jsonify, request, send_from_directory

# 让 web/app.py 能找到上一级的 trove 包
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from trove.filter import apply as apply_filters
from trove.parser import parse_readme
from trove.verifier import check_one

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


def _warmup():
    """后台预热 README 缓存，避免部署后第一次请求卡在网络拉取上。"""
    try:
        load_entries()
        print("[api-trove] README cache warmed up")
    except Exception as e:
        print(f"[api-trove] warmup failed (will retry lazily): {e}")


# 进程启动即预热（gunicorn 导入本模块时也会执行）
threading.Thread(target=_warmup, daemon=True).start()


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
    # 仅本地开发用 Flask 开发服务器；生产环境由 gunicorn 启动（见 render.yaml）
    port = int(os.environ.get("PORT", 5055))
    host = os.environ.get("HOST", "127.0.0.1")
    print(f"api-trove Web UI -> http://{host}:{port}")
    app.run(host=host, port=port, debug=False)
