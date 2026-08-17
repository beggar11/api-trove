# -*- coding: utf-8 -*-
"""全量验证 public-apis 列表，生成周报 report.md + 完整数据 verified.json。

供 GitHub Actions 每周自动运行（见 .github/workflows/weekly_verify.yml），
也可本地手动跑：

  python weekly_report.py --source ../public-apis/README.md
  python weekly_report.py --limit 30      # 快速试跑（只验证前 30 条）
"""
import argparse
import json
import sys
import time
from pathlib import Path

from trove.parser import parse_readme
from trove.report import render_json
from trove.verifier import OK, REACHABLE, ERROR, TIMEOUT, DEAD, summarize, verify_entries

STATUS_ORDER = [OK, REACHABLE, ERROR, TIMEOUT, DEAD]


def find_source(explicit):
    if explicit:
        return Path(explicit)
    for candidate in [Path("../public-apis/README.md"), Path("README.md")]:
        if candidate.exists():
            return candidate
    sys.exit("README.md not found. Use --source.")


def markdown_table(headers, rows):
    md = "| " + " | ".join(headers) + " |\n"
    md += "| " + " | ".join("---" for _ in headers) + " |\n"
    for r in rows:
        md += "| " + " | ".join(str(c) for c in r) + " |\n"
    return md


def main():
    ap = argparse.ArgumentParser(description="Verify all APIs and write a weekly report")
    ap.add_argument("--source", help="path to public-apis README.md")
    ap.add_argument("--limit", type=int, default=0,
                    help="verify only the first N entries (for quick runs)")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--timeout", type=float, default=6.0)
    ap.add_argument("--out", default="report.md")
    args = ap.parse_args()

    src = find_source(args.source)
    entries = parse_readme(src.read_text(encoding="utf-8"))
    targets = entries[: args.limit] if args.limit else entries
    print(f"{len(entries)} entries parsed, verifying {len(targets)} ...")

    t0 = time.time()
    results = verify_entries(targets, workers=args.workers, timeout=args.timeout)
    elapsed = time.time() - t0
    counts = summarize(results)

    # 按状态分类，供报告分区展示
    dead_rows, reachable_rows, ok_rows = [], [], []
    for e in targets:
        r = results.get(e.url)
        if r is None:
            continue
        if r.status in (DEAD, ERROR, TIMEOUT):
            dead_rows.append([e.name, e.category, e.url, r.status, f"{r.ms:.0f}", r.note])
        elif r.status == REACHABLE:
            reachable_rows.append([e.name, e.category, e.url, f"{r.ms:.0f}", r.note])
        else:
            ok_rows.append([e.name, e.category, e.url, f"{r.ms:.0f}"])

    md = [
        "# Public APIs Weekly Verification Report",
        "",
        f"- **Generated at:** {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}",
        f"- **Entries verified:** {len(targets)} (of {len(entries)} in list)",
        f"- **Elapsed:** {elapsed:.0f} s",
        "",
        "## Summary",
        "",
    ]
    md.append(markdown_table(
        ["Status", "Count", "Ratio"],
        [[s, counts.get(s, 0),
          f"{counts.get(s, 0) / len(targets) * 100:.1f}%" if targets else "-"]
         for s in STATUS_ORDER],
    ))
    md += ["", "## 🔴 Dead or broken (needs attention)", ""]
    md.append(markdown_table(
        ["API", "Category", "URL", "Status", "ms", "Note"], dead_rows)
        if dead_rows else "_None - everything reachable._")
    md += ["", "## 🟡 Reachable but may need auth (4xx)", ""]
    md.append(markdown_table(
        ["API", "Category", "URL", "ms", "Note"], reachable_rows)
        if reachable_rows else "_None._")
    md += ["", "## ✅ Sample of working APIs (first 25)", ""]
    md.append(markdown_table(
        ["API", "Category", "URL", "ms"], ok_rows[:25])
        if ok_rows else "_None._")
    md.append("")

    text = "\n".join(md)
    Path(args.out).write_text(text, encoding="utf-8")
    json_rows = render_json(targets, results)
    Path("verified.json").write_text(
        json.dumps(json_rows, ensure_ascii=False, indent=2), encoding="utf-8")

    summary = ", ".join(f"{k}={counts.get(k, 0)}" for k in STATUS_ORDER)
    print(f"Done in {elapsed:.0f}s: {summary}")
    print(f"Wrote {args.out} and verified.json")


if __name__ == "__main__":
    main()
