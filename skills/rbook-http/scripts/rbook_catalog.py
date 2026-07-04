#!/usr/bin/env python3
from __future__ import annotations

import argparse

from rbook_client import add_common_args, compact_article, dump_json, get_json, main_guard, resolve_base_url


def main() -> int:
    parser = argparse.ArgumentParser(description="获取 rbook AI 文章目录")
    add_common_args(parser)
    parser.add_argument("--scope", choices=["visible", "all"], default="visible", help="目录范围")
    parser.add_argument("--compact", action="store_true", help="只保留 agent 常用字段")
    parser.add_argument("--limit", type=int, default=0, help="最多输出多少篇文章，0 表示不限制")
    args = parser.parse_args()

    data = get_json(resolve_base_url(args), "/api/ai/catalog", {"scope": args.scope}, timeout=args.timeout)
    if args.compact:
        articles = [compact_article(item) for item in data.get("articles", [])]
        if args.limit > 0:
            articles = articles[: args.limit]
        data = {
            "scope": data.get("scope", args.scope),
            "total": len(articles),
            "generatedAt": data.get("generatedAt"),
            "articles": articles,
        }
    elif args.limit > 0:
        data["articles"] = data.get("articles", [])[: args.limit]
        data["total"] = len(data["articles"])

    dump_json(data, pretty=args.pretty)
    return 0


if __name__ == "__main__":
    main_guard(main)
