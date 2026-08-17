# -*- coding: utf-8 -*-
"""解析 public-apis 的 README.md，把 Markdown 表格变成结构化条目。

README 的每个分类是一个 `###` 标题，下面跟着统一格式的表格：
    | [API 名称](文档链接) | 描述 | 认证 | HTTPS | CORS |
本模块只关心这些表格行，天然跳过顶部的广告区和 Index 目录。
"""
import re
from dataclasses import dataclass

# 匹配 [名称](http链接)，链接只允许 http/https
NAME_LINK_RE = re.compile(r"\[(.+?)\]\((https?://[^)]+)\)")


@dataclass
class ApiEntry:
    """一条 API 记录，字段与 README 表格列一一对应。"""
    name: str
    url: str
    description: str
    category: str
    auth: str
    https: str
    cors: str
    line: int = 0  # 在 README 中的行号，便于溯源


def parse_readme(text: str) -> list[ApiEntry]:
    """把 README 全文解析成 ApiEntry 列表。"""
    entries: list[ApiEntry] = []
    category = None
    for lineno, line in enumerate(text.splitlines(), 1):
        # 遇到分类标题，记录当前分类
        m = re.match(r"^### (.+)$", line)
        if m:
            category = m.group(1).strip()
            continue
        # 只处理形如 "| [Name](url) | ..." 的条目行
        if not line.startswith("| ["):
            continue
        parts = [p.strip() for p in line.strip().strip("|").split("|")]
        if len(parts) < 5:  # 至少要有 5 列
            continue
        m2 = NAME_LINK_RE.search(parts[0])
        if not m2:
            continue
        entries.append(
            ApiEntry(
                name=m2.group(1),
                url=m2.group(2),
                description=parts[1],
                category=category or "?",
                auth=parts[2].strip("`"),
                https=parts[3],
                cors=parts[4],
                line=lineno,
            )
        )
    return entries
