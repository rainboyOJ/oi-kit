#!/usr/bin/env python3
from __future__ import annotations

import argparse

from rbook_client import add_common_args, dump_json, get_json, main_guard, resolve_base_url


def summarize(data: dict) -> list[dict]:
    rows = []
    for item in data.get("results", []):
        rows.append(
            {
                "title": item.get("title"),
                "path": item.get("path"),
                "url": item.get("url"),
                "heading": item.get("heading"),
                "score": item.get("score"),
                "text": item.get("text"),
            }
        )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="搜索 rbook 文章片段，适合中文查询")
    add_common_args(parser)
    parser.add_argument("query", help="搜索关键词")
    parser.add_argument("--limit", type=int, default=8, help="返回条数")
    parser.add_argument("--text-length", type=int, default=900, help="每条片段文本长度")
    parser.add_argument("--no-text", action="store_true", help="不返回片段正文")
    parser.add_argument("--raw", action="store_true", help="输出 API 原始响应")
    args = parser.parse_args()

    data = get_json(
        resolve_base_url(args),
        "/api/chunks/search",
        {
            "q": args.query,
            "limit": args.limit,
            "textLength": args.text_length,
            "includeText": not args.no_text,
        },
        timeout=args.timeout,
    )
    dump_json(data if args.raw else summarize(data), pretty=args.pretty)
    return 0


if __name__ == "__main__":
    main_guard(main)
