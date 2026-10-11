#!/usr/bin/env python3
from __future__ import annotations

import argparse

from rbook_client import add_common_args, dump_json, get_json, main_guard, resolve_base_url


def main() -> int:
    parser = argparse.ArgumentParser(description="检查 rbook HTTP 服务健康状态")
    add_common_args(parser)
    args = parser.parse_args()

    data = get_json(resolve_base_url(args), "/api/health", timeout=args.timeout)
    dump_json(data, pretty=args.pretty)
    return 0


if __name__ == "__main__":
    main_guard(main)
