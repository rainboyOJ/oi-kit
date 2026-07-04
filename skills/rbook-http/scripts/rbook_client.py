#!/usr/bin/env python3
"""rbook HTTP API 的轻量客户端。

这些脚本故意只使用 Python 标准库，方便 agent 在没有额外依赖的环境中运行。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


DEFAULT_BASE_URL = "https://rbook2.roj.ac.cn"
LOCAL_BASE_URL = "http://127.0.0.1:3000"
ONLINE_BASE_URL = "https://rbook2.roj.ac.cn"


class RbookHttpError(RuntimeError):
    def __init__(self, message: str, status: int | None = None, body: str | None = None) -> None:
        super().__init__(message)
        self.status = status
        self.body = body


def default_base_url() -> str:
    return os.environ.get("RBOOK_BASE_URL", DEFAULT_BASE_URL).rstrip("/")


def add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--base-url",
        default=default_base_url(),
        help=f"rbook 服务地址，默认读取 RBOOK_BASE_URL，否则使用线上 {DEFAULT_BASE_URL}",
    )
    parser.add_argument(
        "--online",
        action="store_true",
        help=f"显式指定线上服务 {ONLINE_BASE_URL}（默认即为线上）",
    )
    parser.add_argument(
        "--local",
        action="store_true",
        help=f"使用本地服务 {LOCAL_BASE_URL}",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="格式化 JSON 输出",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=15.0,
        help="HTTP 超时时间，单位秒",
    )


def resolve_base_url(args: argparse.Namespace) -> str:
    if getattr(args, "local", False):
        return LOCAL_BASE_URL
    if getattr(args, "online", False):
        return ONLINE_BASE_URL
    return str(args.base_url).rstrip("/")


def build_url(base_url: str, path: str, params: dict[str, Any] | None = None) -> str:
    query = ""
    clean_params: dict[str, str] = {}
    for key, value in (params or {}).items():
        if value is None:
            continue
        if isinstance(value, bool):
            clean_params[key] = "true" if value else "false"
        else:
            clean_params[key] = str(value)
    if clean_params:
        query = "?" + urllib.parse.urlencode(clean_params)
    return base_url.rstrip("/") + path + query


def get_json(base_url: str, path: str, params: dict[str, Any] | None = None, timeout: float = 15.0) -> Any:
    url = build_url(base_url, path, params)
    request = urllib.request.Request(url, headers={"accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RbookHttpError(f"HTTP {exc.code}: {url}", status=exc.code, body=body) from exc
    except urllib.error.URLError as exc:
        raise RbookHttpError(f"无法连接 rbook 服务: {url}: {exc.reason}") from exc

    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise RbookHttpError(f"响应不是合法 JSON: {url}", body=body[:500]) from exc


def dump_json(data: Any, pretty: bool = False) -> None:
    if pretty:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(data, ensure_ascii=False, separators=(",", ":")))


def fail(error: Exception) -> int:
    if isinstance(error, RbookHttpError):
        print(str(error), file=sys.stderr)
        if error.body:
            print(error.body[:1200], file=sys.stderr)
        return 2
    print(str(error), file=sys.stderr)
    return 1


def compact_article(article: dict[str, Any]) -> dict[str, Any]:
    return {
        "path": article.get("path"),
        "url": article.get("url"),
        "title": article.get("title"),
        "description": article.get("description"),
        "tags": article.get("tags", []),
        "categories": article.get("categories", []),
        "visible": article.get("visible"),
        "codeTemplates": article.get("codeTemplates", []),
        "citation": article.get("citation"),
    }


def main_guard(fn) -> None:
    try:
        raise SystemExit(fn())
    except Exception as exc:  # pragma: no cover - 命令行兜底
        raise SystemExit(fail(exc))
