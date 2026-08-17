# -*- coding: utf-8 -*-
"""api-trove —— Streamlit 云端仪表盘（免费托管，无需银行卡）。

复用 trove 包的全部能力：解析 public-apis 列表、按条件筛选、
并发实测每个 API 是否存活（OK / REACHABLE / ERROR / TIMEOUT / DEAD）。

本地运行:
    pip install -r requirements.txt
    streamlit run streamlit_app.py

云端部署（Streamlit Community Cloud，免费）:
    1. 用 GitHub 账号登录 https://share.streamlit.io
    2. New app -> 选择 beggar11/api-trove 仓库
    3. Main file 填 streamlit_app.py -> Deploy
"""
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

# 保证 trove 包可导入（本地与云端工作目录都是仓库根目录）
sys.path.insert(0, str(Path(__file__).resolve().parent))

from trove.filter import apply as apply_filters
from trove.parser import parse_readme
from trove.verifier import OK, REACHABLE, ERROR, TIMEOUT, DEAD, summarize, verify_entries

MAX_VERIFY = 60   # 单次验证上限，避免云端等待过久
CACHE_TTL = 3600  # README 缓存 1 小时

st.set_page_config(page_title="api-trove", page_icon="🔍", layout="wide")


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def load_entries():
    """本地优先读 public-apis 克隆，云端自动从 GitHub 拉最新 README。"""
    import requests
    for candidate in ["public-apis/README.md", "../public-apis/README.md", "README.md"]:
        p = Path(candidate)
        if p.exists():
            return parse_readme(p.read_text(encoding="utf-8"))
    url = "https://raw.githubusercontent.com/public-apis/public-apis/master/README.md"
    return parse_readme(requests.get(url, timeout=20).text)


def main():
    st.title("🔍 api-trove")
    st.caption(
        "Search and **live-verify** free public APIs from the "
        "[public-apis](https://github.com/public-apis/public-apis) list. "
        "Entries are community-curated and can go stale — verify before you integrate."
    )

    entries = load_entries()

    # ---- 侧边栏筛选 ----
    with st.sidebar:
        st.header("Filters")
        keyword = st.text_input("Keyword", placeholder="e.g. weather, joke, stock")
        cats = sorted({e.category for e in entries})
        category = st.selectbox("Category", ["All"] + cats)
        auth = st.selectbox("Auth", ["Any", "No", "apiKey", "OAuth", "X-Mashape-Key", "User-Agent"])
        cors = st.selectbox("CORS", ["Any", "Yes", "No", "Unknown"])
        limit = st.slider("Max results", 5, 200, 30)
        workers = st.slider("Verify concurrency", 2, 16, 8,
                            help="并发探测数；越大越快，但请对免费 API 保持礼貌")
        verify_btn = st.button("✓ Verify live", type="primary", use_container_width=True)

    hits = apply_filters(
        entries,
        keyword=keyword or None,
        category=None if category == "All" else category,
        auth=None if auth == "Any" else auth.lower(),
        cors=None if cors == "Any" else cors.lower(),
        limit=limit,
    )
    st.success(f"{len(entries)} APIs in list · **{len(hits)}** after filters")

    if not hits:
        st.info("No APIs match your filters.")
        return

    # ---- 可选：并发验证 ----
    results = None
    if verify_btn:
        targets = hits[:MAX_VERIFY]
        if len(hits) > MAX_VERIFY:
            st.warning(f"只验证前 {MAX_VERIFY} 条（共 {len(hits)} 条），避免等待过久")
        with st.spinner(f"Verifying {len(targets)} endpoints (workers={workers}, timeout=6s)... "
                        "这可能需要几十秒"):
            results = verify_entries(targets, workers=workers, timeout=6.0)
        counts = summarize(results)
        cols = st.columns(5)
        for col, status in zip(cols, [OK, REACHABLE, ERROR, TIMEOUT, DEAD]):
            col.metric(status, counts.get(status, 0))

    # ---- 结果表 ----
    rows = []
    for e in hits[:MAX_VERIFY] if results else hits:
        r = results.get(e.url) if results else None
        rows.append({
            "API": e.name,
            "URL": e.url,
            "Category": e.category,
            "Auth": e.auth,
            "HTTPS": e.https,
            "CORS": e.cors,
            "Status": r.status if r else "—",
            "ms": round(r.ms) if r else "—",
            "Note": r.note if r else "",
        })
    df = pd.DataFrame(rows)

    # Status 列上色
    status_colors = {OK: "#2ecc71", REACHABLE: "#f1c40f", ERROR: "#e74c3c",
                     TIMEOUT: "#e67e22", DEAD: "#95a5a6"}

    def color_status(s):
        return [f"background-color: {status_colors.get(v, '')}; color: #fff; "
                f"font-weight: 700; text-align: center" if v in status_colors else ""
                for v in s]

    st.dataframe(
        df.style.apply(color_status, subset=["Status"]),
        use_container_width=True,
        hide_index=True,
        column_config={
            "URL": st.column_config.LinkColumn("URL", display_text="open ↗"),
            "Status": st.column_config.TextColumn("Status", width="small"),
            "ms": st.column_config.NumberColumn("ms", width="small"),
        },
    )

    st.caption(
        "Status legend: **OK** 2xx usable · **REACHABLE** 4xx (may need key/params) · "
        "**ERROR** 5xx · **TIMEOUT** · **DEAD** no connection. "
        f"Verification capped at {MAX_VERIFY} per click."
    )


if __name__ == "__main__":
    main()
