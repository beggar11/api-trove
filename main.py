# -*- coding: utf-8 -*-
"""api-trove 命令行入口。

Usage examples:
  python main.py --keyword weather --limit 10        # 本地检索（秒回）
  python main.py --category Weather --verify         # 检索 + 实测可用性
  python main.py --auth no --cors yes --verify       # 筛出可直接前端调用的
  python main.py --verify --format json --output verified.json
"""
import argparse
import json
import sys
from pathlib import Path

from trove.parser import parse_readme
from trove.filter import apply as apply_filters
from trove.verifier import verify_entries, summarize
from trove.report import render_json, render_markdown, render_table


def find_source(explicit: str | None) -> Path:
    """定位 public-apis 的 README：优先 --source，其次自动探测。"""
    if explicit:
        return Path(explicit)
    for candidate in [Path("../public-apis/README.md"), Path("README.md")]:
        if candidate.exists():
            return candidate
    sys.exit("README.md not found. Use --source to point at the public-apis README.")


def main():
    # 让程序在任何控制台编码（如 Windows GBK）下都能安全打印，避免 UnicodeEncodeError
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    ap = argparse.ArgumentParser(
        description="api-trove: search and live-verify free public APIs from the public-apis list"
    )
    ap.add_argument("--source", help="path to public-apis README.md (auto-detected by default)")
    ap.add_argument("--keyword", help="filter by keyword in name/description")
    ap.add_argument("--category", help="filter by category, e.g. Weather")
    ap.add_argument("--auth", choices=["no", "apikey", "oauth", "x-mashape-key", "user-agent"],
                    help="filter by auth type")
    ap.add_argument("--cors", choices=["yes", "no", "unknown"], help="filter by CORS support")
    ap.add_argument("--https", choices=["yes", "no"], help="filter by HTTPS support")
    ap.add_argument("--limit", type=int, help="show at most N entries")
    ap.add_argument("--verify", action="store_true", help="live-check each API (concurrent)")
    ap.add_argument("--engine", choices=["threads", "async"], default="threads",
                    help="verification engine: threads (requests, default) or async (aiohttp, faster)")
    ap.add_argument("--workers", type=int, default=16, help="verify concurrency (default 16)")
    ap.add_argument("--timeout", type=float, default=6.0, help="per-request timeout in seconds")
    ap.add_argument("--format", choices=["table", "json", "markdown"], default="table")
    ap.add_argument("--output", help="write result to a file")
    args = ap.parse_args()

    src = find_source(args.source)
    entries = parse_readme(src.read_text(encoding="utf-8"))
    hits = apply_filters(
        entries,
        keyword=args.keyword,
        category=args.category,
        auth=args.auth,
        cors=args.cors,
        https=args.https,
        limit=args.limit,
    )
    print(f"{len(entries)} APIs in list, {len(hits)} after filters\n")

    results = None
    if args.verify:
        print(f"Verifying {len(hits)} APIs "
              f"(engine={args.engine}, workers={args.workers}, timeout={args.timeout}s)...")
        if args.engine == "async":
            from trove.async_verifier import verify_entries_async
            results = verify_entries_async(hits, workers=args.workers, timeout=args.timeout)
        else:
            results = verify_entries(hits, workers=args.workers, timeout=args.timeout)
        counts = summarize(results)
        summary = ", ".join(f"{k}={counts.get(k, 0)}" for k in
                            ["OK", "REACHABLE", "ERROR", "TIMEOUT", "DEAD"])
        print(f"Result: {summary}\n")

    if args.format == "json":
        text = json.dumps(render_json(hits, results), ensure_ascii=False, indent=2)
    elif args.format == "markdown":
        text = render_markdown(hits, results)
    else:
        text = render_table(hits, results)

    print(text)
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
        print(f"\n[written to {args.output}]")


if __name__ == "__main__":
    main()
