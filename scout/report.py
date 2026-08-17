# -*- coding: utf-8 -*-
"""结果渲染：终端表格 / JSON / Markdown 三种输出。"""
from scout.verifier import VerifyResult


def _row_for(entry, result):
    """把一条条目（+可选验证结果）转成字典，供 JSON 输出。"""
    row = {
        "name": entry.name,
        "url": entry.url,
        "description": entry.description,
        "category": entry.category,
        "auth": entry.auth,
        "https": entry.https,
        "cors": entry.cors,
    }
    if result:
        row["status"] = result.status
        row["http_code"] = result.http_code
        row["ms"] = round(result.ms)
        row["note"] = result.note
        row["snippet"] = result.snippet
    return row


def _rows_for(entries, results):
    """构建表格行（验证模式/列表模式共用）。返回 (headers, rows)。"""
    if results:
        headers = ["Name", "Category", "Status", "ms", "Note"]
        rows = [
            [
                e.name, e.category, results[e.url].status,
                f"{results[e.url].ms:.0f}", results[e.url].note,
            ]
            for e in entries
        ]
    else:
        headers = ["Name", "Category", "Auth", "HTTPS", "CORS"]
        rows = [[e.name, e.category, e.auth, e.https, e.cors] for e in entries]
    return headers, rows


def render_json(entries, results) -> list:
    """JSON 输出：完整的结构化数据。"""
    return [_row_for(e, results.get(e.url) if results else None) for e in entries]


def _table(headers, rows):
    """手写等宽表格（避免引入 tabulate 依赖）。"""
    widths = [len(h) for h in headers]
    for r in rows:
        for i, cell in enumerate(r):
            widths[i] = max(widths[i], len(str(cell)))
    lines = ["  ".join(h.ljust(widths[i]) for i, h in enumerate(headers))]
    lines.append("  ".join("-" * widths[i] for i in range(len(headers))))
    for r in rows:
        lines.append("  ".join(str(c).ljust(widths[i]) for i, c in enumerate(r)))
    return "\n".join(lines)


def render_table(entries, results) -> str:
    """终端表格输出。"""
    headers, rows = _rows_for(entries, results)
    return _table(headers, rows)


def render_markdown(entries, results) -> str:
    """Markdown 表格输出，可直接粘贴进 README。"""
    headers, rows = _rows_for(entries, results)
    md = "| " + " | ".join(headers) + " |\n"
    md += "| " + " | ".join("---" for _ in headers) + " |\n"
    for r in rows:
        md += "| " + " | ".join(str(c) for c in r) + " |\n"
    return md
