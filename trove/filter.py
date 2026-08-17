# -*- coding: utf-8 -*-
"""过滤条件：按关键词/分类/认证/HTTPS/CORS 筛选条目。

CLI（main.py）和 Web 后端（web/app.py）共用，避免重复逻辑。
"""
def apply(entries, *, keyword=None, category=None, auth=None, cors=None,
          https=None, limit=None):
    """返回满足所有条件的条目子集；limit 为 0/None 时不过滤数量。"""
    def keep(e):
        if category and e.category.lower() != category.lower():
            return False
        if keyword:
            kw = keyword.lower()
            if kw not in e.name.lower() and kw not in e.description.lower():
                return False
        if auth and e.auth.lower() != auth.lower():
            return False
        if cors and e.cors.lower() != cors.lower():
            return False
        if https and e.https.lower() != https.lower():
            return False
        return True

    hits = [e for e in entries if keep(e)]
    if limit:
        hits = hits[:limit]
    return hits
