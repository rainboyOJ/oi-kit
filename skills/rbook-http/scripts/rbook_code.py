#!/usr/bin/env python3
from __future__ import annotations

import argparse

from rbook_client import add_common_args, dump_json, get_json, main_guard, resolve_base_url


def main() -> int:
    parser = argparse.ArgumentParser(description="读取 book/code 下的单个模板代码")
    add_common_args(parser)
    parser.add_argument("path", help="代码路径，例如 /code/graph/v-bcc.cpp")
    parser.add_argument("--content-only", action="store_true", help="只输出代码正文")
    args = parser.parse_args()

    data = get_json(resolve_base_url(args), "/api/ai/code", {"path": args.path}, timeout=args.timeout)
    if args.content_only:
        print(data.get("content", ""))
    else:
        dump_json(data, pretty=args.pretty)
    return 0


if __name__ == "__main__":
    main_guard(main)
