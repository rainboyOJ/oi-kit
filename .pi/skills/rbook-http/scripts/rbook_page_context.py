#!/usr/bin/env python3
from __future__ import annotations

import argparse

from rbook_client import add_common_args, dump_json, get_json, main_guard, resolve_base_url


def compact_context(data: dict) -> dict:
    article = data.get("article", {})
    return {
        "article": {
            "path": article.get("path"),
            "url": article.get("url"),
            "title": article.get("title"),
            "description": article.get("description"),
            "tags": article.get("tags", []),
            "categories": article.get("categories", []),
            "headings": article.get("headings", []),
            "citation": article.get("citation"),
            "markdown": article.get("markdown"),
        },
        "codeTemplates": data.get("codeTemplates", []),
        "includedCode": data.get("includedCode", []),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="读取单篇文章的 AI 上下文")
    add_common_args(parser)
    parser.add_argument("path", help="文章 Markdown 路径，例如 graph/bcc/index.md")
    parser.add_argument("--include-code", action="store_true", help="包含模板代码正文")
    parser.add_argument("--include-html", action="store_true", help="包含渲染 HTML")
    parser.add_argument("--compact", action="store_true", help="只保留常用字段")
    args = parser.parse_args()

    data = get_json(
        resolve_base_url(args),
        "/api/ai/page-context",
        {
            "path": args.path,
            "includeCode": args.include_code,
            "includeHtml": args.include_html,
        },
        timeout=args.timeout,
    )
    dump_json(compact_context(data) if args.compact else data, pretty=args.pretty)
    return 0


if __name__ == "__main__":
    main_guard(main)
