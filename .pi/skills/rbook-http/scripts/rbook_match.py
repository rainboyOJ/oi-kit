#!/usr/bin/env python3
"""按知识点匹配 rbook 章节（oi-kit 复盘专用）。

输入一个或多个知识点，在 `/api/catalog` 的条目上做加权打分（id / title / tags /
description），每个知识点取 top-1，输出 JSON 数组：

    {"tag": <知识点>, "title": <文章标题>, "url": <文章相对 url>,
     "score": <打分>, "source": "catalog" | "none"}

`source` 为 `none` 表示 rbook 目录里确实没有对应章节，调用方应如实标注，
不要硬凑。注意区分两种“没结果”：

- 知识点未命中 → `source: none`，正常退出；
- catalog 拉取失败（服务不可用、路由变更等）→ 报错退出（exit 2），
  因为此时无法判断 rbook 是否真的没有该章节。

打分与模糊兜底基于目录元数据，不做全文检索：线上 `/api/chunks/search`
与 `/api/ai/*` 已下线，新版 API 只有目录级检索（`rbook.py find`）。
"""

from __future__ import annotations

import argparse
import difflib
import re
import sys
from typing import Any

import rbook


def normalize(text: Any) -> str:
    """小写、压平空白，便于中文/英文知识点比较。"""
    return re.sub(r"\s+", " ", str(text or "")).strip().casefold()


def fuzzy_ratio(token: str, candidate: str) -> float:
    if not token or not candidate:
        return 0.0
    return difflib.SequenceMatcher(None, token, candidate).ratio()


def token_score(item: dict[str, Any], token: str) -> float:
    """单个关键词对单个目录条目的得分；0 表示完全没命中。

    只做单向包含（关键词 ⊆ 条目的 id/title/tags/description/path），
    反过来“条目短标签 ⊆ 关键词”会造成大量假阳性（例如“量子退火算法”
    因为含“算法”二字而命中无关文章），近似写法交给模糊兜底处理。
    """
    item_id = normalize(item.get("id"))
    title = normalize(item.get("title"))
    menu_title = normalize(item.get("menuTitle"))
    tags = [normalize(tag) for tag in item.get("tags") or []]
    description = normalize(item.get("description"))
    path = normalize(item.get("path"))

    scores: list[float] = []

    if token == item_id:
        scores.append(500.0)
    elif token in item_id:
        scores.append(400.0)

    if token == title:
        scores.append(450.0)
    elif token in title:
        scores.append(300.0)

    if menu_title:
        if token == menu_title:
            scores.append(200.0)
        elif token in menu_title:
            scores.append(120.0)

    for tag in tags:
        if token == tag:
            scores.append(220.0)
            break
        if token in tag:
            scores.append(120.0)
            break

    if token in description:
        scores.append(60.0)

    if token in path:
        scores.append(40.0)

    if scores:
        return max(scores)

    # 模糊兜底：处理“组合枚句”这类错字/近似写法。
    # 只在长度相近（差 ≤ 1）时启用，否则短 tag（如“二分”）会与长知识点
    # （如“二分答案”）产生高相似度误命中；单字/双字关键词也不做模糊。
    if len(token) < 3:
        return 0.0
    best = 0.0
    for candidate in [title, item_id, menu_title, *tags]:
        if not candidate or abs(len(candidate) - len(token)) > 1:
            continue
        ratio = fuzzy_ratio(token, candidate)
        if ratio > best:
            best = ratio
    if best >= 0.7:
        return round(30.0 * best, 2)
    return 0.0


def item_score(item: dict[str, Any], keyword: str) -> float:
    """知识点整体得分。

    按空白切成若干关键词，全命中时求和；只命中一部分时按命中比例打折
    （软 AND）。这样“数位DP 记忆化搜索”这种把两个词写在一起的写法仍能
    命中《数位DP》，而完全不命中的知识点依然返回 0。
    """
    tokens = [token for token in normalize(keyword).split(" ") if token]
    if not tokens:
        return 0.0
    hits = [token_score(item, token) for token in tokens]
    matched = [score for score in hits if score > 0.0]
    if not matched:
        return 0.0
    total = sum(matched)
    if len(matched) < len(tokens):
        total *= len(matched) / len(tokens)
    return total


def match_one(
    items: list[dict[str, Any]],
    keyword: str,
    min_score: float,
    explain: bool = False,
) -> dict[str, Any]:
    best_item: dict[str, Any] | None = None
    best_score = 0.0
    for item in items:
        score = item_score(item, keyword)
        if score > best_score:
            best_score = score
            best_item = item

    if best_item is None or best_score < min_score:
        if explain:
            print(
                f"[explain] 「{keyword}」未达阈值 {min_score}（最高分 {round(best_score, 2)}）",
                file=sys.stderr,
            )
        return {"tag": keyword, "title": None, "url": None, "score": 0.0, "source": "none"}

    if explain:
        tokens = [token for token in normalize(keyword).split(" ") if token]
        detail = ", ".join(
            f"{token}={round(token_score(best_item, token), 2)}" for token in tokens
        )
        print(
            f"[explain] 「{keyword}」-> id={best_item.get('id')} "
            f"title={best_item.get('title')} score={round(best_score, 2)} ({detail})",
            file=sys.stderr,
        )

    return {
        "tag": keyword,
        "title": best_item.get("title") or best_item.get("menuTitle") or best_item.get("id"),
        "url": best_item.get("url"),
        "score": round(best_score, 2),
        "source": "catalog",
    }


def fetch_catalog(base_url: str, include_hidden: bool) -> list[dict[str, Any]]:
    params = {"compact": "true"}
    if include_hidden:
        params["includeHidden"] = "true"
    payload = rbook.request_json(base_url, "/api/catalog", params)
    items = payload.get("items")
    if not isinstance(items, list):
        raise rbook.RbookClientError("INVALID_RESPONSE", "catalog 响应缺少 items 数组")
    return items


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="按知识点匹配 rbook 章节，每个知识点取 top-1（catalog 打分 + 模糊兜底）",
    )
    parser.add_argument("keywords", nargs="+", help="一个或多个知识点，每个取 top-1")
    parser.add_argument("--baseurl", help="API 地址，默认读 RBOOK_BASE_URL，否则用线上地址")
    parser.add_argument("--include-hidden", action="store_true", help="包含非 visible 的目录文章")
    parser.add_argument("--min-score", type=float, default=10.0, help="命中阈值，低于此分判为未命中")
    parser.add_argument("--explain", action="store_true", help="把每个知识点的命中/未命中原因打到 stderr")
    parser.add_argument("--pretty", action="store_true", help="输出缩进 JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    base_url = rbook.resolve_baseurl(args.baseurl)

    try:
        items = fetch_catalog(base_url, args.include_hidden)
    except rbook.RbookClientError as error:
        rbook.print_error(error, json_output=True)
        print(
            "[hint] catalog 拉取失败时无法判断 rbook 是否真的没有该章节，"
            "请不要据此写“rbook 暂无对应章节”；先确认服务可用或改用本地服务。",
            file=sys.stderr,
        )
        return 2

    results = []
    for keyword in args.keywords:
        hit = match_one(items, keyword, args.min_score, explain=args.explain)
        results.append(hit)
        if hit["source"] == "none":
            print(f"[warn] 知识点「{keyword}」在 rbook 目录中未命中（source=none）", file=sys.stderr)

    rbook.print_json(results, pretty=args.pretty)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
