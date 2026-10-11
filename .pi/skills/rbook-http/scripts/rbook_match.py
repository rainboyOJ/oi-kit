#!/usr/bin/env python3
"""按知识点匹配 rbook 章节。

对一个或多个知识点，先在 rbook 目录（catalog）里做模糊打分，每个知识点取 top-1。
catalog 未命中时降级到片段搜索（chunks/search）兜底，仍取 top-1。
最终输出 JSON 数组，每项形如：
    {"tag": <知识点>, "title": <文章标题>, "url": <文章相对 url>,
     "score": <打分>, "source": "catalog" | "search" | "none"}

为减少远程拉取，catalog 默认按天缓存到项目目录下
    .pi/oj-tools/.cache/rbook-catalog-YYYY-MM-DD.json
命中缓存时会在 stderr 通知用户，并给出更新方法。
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any

from rbook_client import (
    ONLINE_BASE_URL,
    add_common_args,
    compact_article,
    dump_json,
    get_json,
    main_guard,
    resolve_base_url,
)


def find_project_root(start: Path | None = None) -> Path:
    cur = (start or Path.cwd()).resolve()
    for path in [cur, *cur.parents]:
        if (path / "problems").is_dir():
            return path
        if (path / ".pi").is_dir():
            return path
        if (path / "oj-tools").is_dir():
            return path
    return cur


def cache_path(root: Path, scope: str, date: dt.date) -> Path:
    return root / ".pi" / "oj-tools" / ".cache" / f"rbook-catalog-{scope}-{date.isoformat()}.json"


def load_cache(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and "articles" in data:
            return data
    except Exception:
        return None
    return None


def save_cache(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def fetch_catalog(base_url: str, scope: str, timeout: float) -> dict[str, Any]:
    data = get_json(base_url, "/api/ai/catalog", {"scope": scope}, timeout=timeout)
    articles = [compact_article(item) for item in data.get("articles", [])]
    return {
        "scope": data.get("scope", scope),
        "generatedAt": data.get("generatedAt"),
        "articles": articles,
    }


def get_catalog(args: argparse.Namespace, base_url: str) -> tuple[dict[str, Any], str]:
    """返回 (catalog_dict, 来源标签)。来源: 'cache' | 'cache-refreshed' | 'remote'."""
    root = find_project_root()
    today = dt.date.today()
    cpath = cache_path(root, args.scope, today)
    use_cache_read = not args.no_cache

    if use_cache_read:
        cached = load_cache(cpath)
        if cached is not None:
            print(
                f"[cache] 使用缓存 {cpath}\n"
                f"[cache] 如需最新数据：删除该文件，或重新运行并加 --no-cache 更新缓存。",
                file=sys.stderr,
            )
            return cached, "cache"

    data = fetch_catalog(base_url, args.scope, args.timeout)
    # 无论 --no-cache 与否，都写回缓存，避免下一次又重拉。
    save_cache(cpath, data)
    print(f"[cache] 已更新缓存 {cpath}", file=sys.stderr)
    return data, "cache-refreshed"


def score_article(article: dict[str, Any], kw: str) -> float:
    """简单加权打分：标题命中权重最高，其次 tags/categories，再 description，最后 headings。"""
    if not kw:
        return 0.0
    kw_l = kw.lower()
    title = (article.get("title") or "").lower()
    score = 0.0
    if kw_l == title:
        score += 100.0
    elif kw_l in title:
        score += 60.0
    elif title and title in kw_l:
        score += 30.0

    for tag in article.get("tags", []) or []:
        if kw_l == (tag or "").lower():
            score += 40.0
            break
        if kw_l in (tag or "").lower():
            score += 25.0
            break

    for cat in article.get("categories", []) or []:
        if kw_l == (cat or "").lower():
            score += 30.0
            break
        if kw_l in (cat or "").lower():
            score += 15.0
            break

    desc = (article.get("description") or "").lower()
    if kw_l in desc:
        score += 8.0

    for h in article.get("headings", []) or []:
        text = (h.get("text") if isinstance(h, dict) else str(h)) or ""
        if kw_l in text.lower():
            score += 5.0
            break
    return score


def match_in_catalog(catalog: dict[str, Any], kw: str, min_score: float) -> dict[str, Any] | None:
    best: dict[str, Any] | None = None
    best_score = 0.0
    for art in catalog.get("articles", []) or []:
        s = score_article(art, kw)
        if s > best_score:
            best_score = s
            best = art
    if best is not None and best_score >= min_score:
        citation = best.get("citation") or {}
        return {
            "tag": kw,
            "title": best.get("title") or citation.get("title"),
            "url": best.get("url") or citation.get("url"),
            "score": round(best_score, 2),
            "source": "catalog",
        }
    return None


def fallback_search(base_url: str, kw: str, timeout: float, limit: int) -> dict[str, Any] | None:
    data = get_json(
        base_url,
        "/api/chunks/search",
        {"q": kw, "limit": limit, "textLength": 0, "includeText": False},
        timeout=timeout,
    )
    results = data.get("results", []) or []
    if not results:
        return None
    top = results[0]
    return {
        "tag": kw,
        "title": top.get("title"),
        "url": top.get("url"),
        "score": round(float(top.get("score") or 0.0), 2),
        "source": "search",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="按知识点匹配 rbook 章节，目录优先、搜索兜底，带天级缓存")
    add_common_args(parser)
    parser.add_argument("keywords", nargs="+", help="一个或多个知识点，每个取 top-1")
    parser.add_argument("--scope", choices=["visible", "all"], default="visible", help="catalog 范围")
    parser.add_argument("--no-cache", action="store_true", help="忽略并刷新缓存，重新拉取 catalog")
    parser.add_argument("--min-score", type=float, default=10.0, help="catalog 命中阈值，低于此分判为未命中")
    parser.add_argument("--search-limit", type=int, default=5, help="降级搜索时取前若干条再选 top-1")
    args = parser.parse_args()

    base_url = resolve_base_url(args)
    catalog, _source = get_catalog(args, base_url)

    results: list[dict[str, Any]] = []
    for kw in args.keywords:
        hit = match_in_catalog(catalog, kw, args.min_score)
        if hit is not None:
            results.append(hit)
            continue
        # 降级搜索
        try:
            s_hit = fallback_search(base_url, kw, args.timeout, args.search_limit)
        except Exception as exc:
            print(f"[warn] 知识点「{kw}」降级搜索失败：{exc}", file=sys.stderr)
            s_hit = None
        if s_hit is not None:
            results.append(s_hit)
        else:
            results.append({"tag": kw, "title": None, "url": None, "score": 0.0, "source": "none"})

    dump_json(results, pretty=args.pretty)
    return 0


if __name__ == "__main__":
    main_guard(main)