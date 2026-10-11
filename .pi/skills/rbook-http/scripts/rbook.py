#!/usr/bin/env python3
import argparse
import json
import os
import re
import sys
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


DEFAULT_BASE_URL = "https://rbook2.roj.ac.cn"


class RbookClientError(RuntimeError):
    def __init__(self, code, message, exit_status=1):
        super().__init__(message)
        self.code = code
        self.message = message
        self.exit_status = exit_status


class RbookArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        payload = {"error": "ARGUMENT_ERROR", "message": message}
        if "--json" in sys.argv[1:]:
            print_json(payload, file=sys.stderr, pretty=False)
        else:
            print(f"ARGUMENT_ERROR: {message}", file=sys.stderr)
        self.exit(2)


def load_config_baseurl():
    config_path = Path.home() / ".rbookrc"
    if not config_path.exists():
        return None
    try:
        text = config_path.read_text(encoding="utf-8").strip()
        if not text:
            return None
        if text.startswith("{"):
            data = json.loads(text)
            return data.get("baseurl") or data.get("base_url") or data.get("RBOOK_BASE_URL")
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                if key.strip().lower() in {"baseurl", "base_url", "rbook_base_url"}:
                    return value.strip().strip('"').strip("'")
            else:
                return line
    except Exception:
        return None
    return None


def resolve_baseurl(cli_value):
    if cli_value:
        return cli_value.rstrip("/")
    env_value = os.environ.get("RBOOK_BASE_URL")
    if env_value:
        return env_value.rstrip("/")
    config_value = load_config_baseurl()
    if config_value:
        return config_value.rstrip("/")
    return DEFAULT_BASE_URL


def request_json(baseurl, path, params=None):
    query = urllib.parse.urlencode(params or {}, doseq=True)
    url = f"{baseurl}{path}"
    if query:
        url = f"{url}?{query}"
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8")
            return json.loads(body)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            data = json.loads(body)
        except Exception:
            data = {}
        error = data.get("error") if isinstance(data, dict) else None
        message = data.get("message") if isinstance(data, dict) else None
        raise RbookClientError(
            str(error or "HTTP_ERROR"),
            str(message or f"HTTP {exc.code}: {body}"),
        ) from exc
    except Exception as exc:
        raise RbookClientError("REQUEST_FAILED", str(exc)) from exc


def print_json(data, file=sys.stdout, pretty=True):
    if pretty:
        output = json.dumps(data, ensure_ascii=False, indent=2)
    else:
        output = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    print(output, file=file)


def normalize_tsv(value):
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        return ",".join(normalize_tsv(item) for item in value)
    if isinstance(value, bool):
        return "true" if value else "false"
    return re.sub(r"\s+", " ", str(value)).strip()


def print_tsv(headers, rows):
    print("\t".join(headers))
    for row in rows:
        print("\t".join(normalize_tsv(value) for value in row))


def print_numbered_tsv(headers, items, fields):
    rows = []
    for number, item in enumerate(items, start=1):
        rows.append([number, *(item.get(field) for field in fields)])
    print_tsv(["#", *headers], rows)


def display_width(value):
    width = 0
    for char in value:
        if unicodedata.combining(char):
            continue
        width += 2 if unicodedata.east_asian_width(char) in {"W", "F"} else 1
    return width


def normalize_table(value):
    return normalize_tsv(value).replace("|", "\\|")


def print_table(headers, rows):
    normalized_headers = [normalize_table(header) for header in headers]
    normalized_rows = [
        [normalize_table(value) for value in row]
        for row in rows
    ]
    widths = [
        max(display_width(row[index]) for row in [normalized_headers, *normalized_rows])
        for index in range(len(normalized_headers))
    ]

    def render_row(row):
        cells = [
            f" {value}{' ' * (widths[index] - display_width(value))} "
            for index, value in enumerate(row)
        ]
        return "|" + "|".join(cells) + "|"

    border = "+" + "+".join("-" * (width + 2) for width in widths) + "+"
    print(border)
    print(render_row(normalized_headers))
    print(border)
    for row in normalized_rows:
        print(render_row(row))
    print(border)


def print_numbered_table(headers, items, fields):
    rows = []
    for number, item in enumerate(items, start=1):
        rows.append([number, *(item.get(field) for field in fields)])
    print_table(["#", *headers], rows)


def print_error(error, json_output):
    if json_output:
        print_json(
            {"error": error.code, "message": error.message},
            file=sys.stderr,
            pretty=False,
        )
    else:
        print(f"{error.code}: {error.message}", file=sys.stderr)


def positive_int(value):
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return number


def nonnegative_int(value):
    number = int(value)
    if number < 0:
        raise argparse.ArgumentTypeError("must be a non-negative integer")
    return number


def find_pages(items, query, limit=20):
    words = [word.casefold() for word in query.split() if word]
    matches = []

    for item in items:
        page_id = str(item.get("id") or "").casefold()
        title = str(item.get("title") or "").casefold()
        description = str(item.get("description") or "").casefold()
        tags = [str(tag).casefold() for tag in item.get("tags") or []]
        score = 0

        for word in words:
            word_scores = []
            if word in page_id:
                word_scores.append(400 + (100 if word == page_id else 0))
            if word in title:
                word_scores.append(300 + (100 if word == title else 0))
            if any(word in tag for tag in tags):
                word_scores.append(200)
            if word in description:
                word_scores.append(100)
            if not word_scores:
                break
            score += max(word_scores)
        else:
            matches.append((score, title, page_id, item))

    matches.sort(key=lambda match: (-match[0], match[1], match[2]))
    return {
        "query": query,
        "total": len(matches),
        "items": [match[3] for match in matches[:limit]],
    }


def page_summary(item):
    return {
        "id": item.get("id") or "",
        "title": item.get("title") or "",
        "description": item.get("description") or "",
        "tags": item.get("tags") or [],
    }


def page_detail(payload):
    return {
        "id": payload.get("id") or "",
        "title": payload.get("title") or "",
        "description": payload.get("description") or "",
        "path": payload.get("path") or "",
        "url": payload.get("url") or "",
        "tags": payload.get("tags") or [],
        "categories": payload.get("categories") or [],
        "frontMatter": payload.get("frontMatter") or {},
        "headings": payload.get("headings") or [],
        "navTrail": payload.get("navTrail") or [],
        "markdown": require_text(payload, "markdown"),
    }


def code_summary(item):
    return {
        "id": item.get("id") or "",
        "title": item.get("description") or "",
        "language": item.get("language") or "",
        "tags": item.get("tags") or [],
    }


def project_list(payload, projector):
    items = [projector(item) for item in payload.get("items") or []]
    return {
        "total": payload.get("total", len(items)),
        "items": items,
    }


def print_page_list(payload, json_output, table=False):
    projected = project_list(payload, page_summary)
    if json_output:
        print_json(projected)
        return
    if table:
        print_numbered_table(
            ["id", "title", "description", "tags"],
            projected["items"],
            ["id", "title", "description", "tags"],
        )
        return
    print_numbered_tsv(
        ["id", "title", "description", "tags"],
        projected["items"],
        ["id", "title", "description", "tags"],
    )


def print_code_list(payload, json_output, table=False):
    projected = project_list(payload, code_summary)
    if json_output:
        print_json(projected)
        return
    if table:
        print_numbered_table(
            ["id", "title", "language", "tags"],
            projected["items"],
            ["id", "title", "language", "tags"],
        )
        return
    print_numbered_tsv(
        ["id", "title", "language", "tags"],
        projected["items"],
        ["id", "title", "language", "tags"],
    )


def print_health(payload):
    stats = payload.get("stats") or {}
    print_tsv(
        ["key", "value"],
        [
            ["ok", payload.get("ok")],
            ["generatedAt", payload.get("generatedAt")],
            ["pages", stats.get("pages")],
            ["codes", stats.get("codes")],
            ["errors", stats.get("errors")],
        ],
    )


def print_site(payload):
    site = payload.get("site") or {}
    stats = payload.get("stats") or {}
    print_tsv(
        ["key", "value"],
        [
            ["title", site.get("title")],
            ["author", site.get("author")],
            ["description", site.get("description")],
            ["github_repository", site.get("github_repository")],
            ["pages", stats.get("pages")],
            ["codes", stats.get("codes")],
            ["errors", stats.get("errors")],
            ["generatedAt", payload.get("generatedAt")],
        ],
    )


def print_tags(payload, table=False):
    items = [
        *({"type": "article", **item} for item in payload.get("articleTags") or []),
        *({"type": "code", **item} for item in payload.get("codeTags") or []),
    ]
    if table:
        print_numbered_table(["type", "tag", "count"], items, ["type", "tag", "count"])
        return
    print_numbered_tsv(["type", "tag", "count"], items, ["type", "tag", "count"])


def add_json_argument(parser):
    parser.add_argument("--json", action="store_true", help="output JSON instead of TSV or raw content")


def add_list_output_arguments(parser):
    output_group = parser.add_mutually_exclusive_group()
    output_group.add_argument("--json", action="store_true", help="output JSON")
    output_group.add_argument("--table", action="store_true", help="output an ASCII table")


def build_parser():
    parser = RbookArgumentParser(description="rbook HTTP API client")
    parser.add_argument("--baseurl", help="API base url")

    subparsers = parser.add_subparsers(dest="command", required=True)

    add_json_argument(subparsers.add_parser("health"))
    add_json_argument(subparsers.add_parser("site"))
    add_list_output_arguments(subparsers.add_parser("catalog"))

    find_parser = subparsers.add_parser("find")
    find_parser.add_argument("query")
    find_parser.add_argument("--limit", type=positive_int, default=20)
    add_list_output_arguments(find_parser)

    pages_parser = subparsers.add_parser("pages")
    pages_parser.add_argument("--id")
    pages_parser.add_argument("--tag")
    pages_parser.add_argument("--limit", type=positive_int)
    pages_parser.add_argument("--offset", type=nonnegative_int)
    add_list_output_arguments(pages_parser)

    codes_parser = subparsers.add_parser("codes")
    codes_parser.add_argument("--id")
    codes_parser.add_argument("--tag")
    codes_parser.add_argument("--limit", type=positive_int)
    codes_parser.add_argument("--offset", type=nonnegative_int)
    add_list_output_arguments(codes_parser)

    add_list_output_arguments(subparsers.add_parser("tags"))
    return parser


def validate_detail_arguments(args):
    if args.command not in {"pages", "codes"} or not args.id:
        return
    conflicts = [
        option
        for option, value in (
            ("--tag", args.tag),
            ("--limit", args.limit),
            ("--offset", args.offset),
            ("--table", "--table" if getattr(args, "table", False) else None),
        )
        if value is not None
    ]
    if conflicts:
        joined = ", ".join(conflicts)
        raise RbookClientError(
            "ARGUMENT_ERROR",
            f"--id cannot be used with {joined}",
            exit_status=2,
        )


def require_text(payload, field):
    value = payload.get(field)
    if not isinstance(value, str):
        raise RbookClientError("INVALID_RESPONSE", f"response field '{field}' is missing or invalid")
    return value


def execute(args):
    validate_detail_arguments(args)
    baseurl = resolve_baseurl(args.baseurl)

    if args.command == "health":
        payload = request_json(baseurl, "/api/health")
        if args.json:
            print_json(payload)
        else:
            print_health(payload)
    elif args.command == "site":
        payload = request_json(baseurl, "/api/site")
        if args.json:
            print_json(payload)
        else:
            print_site(payload)
    elif args.command == "catalog":
        payload = request_json(baseurl, "/api/catalog", {"compact": "true"})
        print_page_list(payload, args.json, args.table)
    elif args.command == "find":
        catalog = request_json(baseurl, "/api/catalog", {"compact": "true"})
        payload = find_pages(catalog.get("items") or [], args.query, args.limit)
        print_page_list(payload, args.json, args.table)
    elif args.command == "pages":
        params = {}
        if args.id:
            params["id"] = args.id
        if args.tag:
            params["tag"] = args.tag
        if args.limit is not None:
            params["limit"] = str(args.limit)
        if args.offset is not None:
            params["offset"] = str(args.offset)
        payload = request_json(baseurl, "/api/pages", params)
        if args.id:
            if args.json:
                print_json(page_detail(payload))
            else:
                sys.stdout.write(require_text(payload, "markdown"))
        else:
            print_page_list(payload, args.json, args.table)
    elif args.command == "codes":
        params = {}
        if args.id:
            params["id"] = args.id
            params["includeContent"] = "true"
        if args.tag:
            params["tag"] = args.tag
        if args.limit is not None:
            params["limit"] = str(args.limit)
        if args.offset is not None:
            params["offset"] = str(args.offset)
        payload = request_json(baseurl, "/api/codes", params)
        if args.id:
            if args.json:
                print_json(payload)
            else:
                sys.stdout.write(require_text(payload, "content"))
        else:
            print_code_list(payload, args.json, args.table)
    elif args.command == "tags":
        payload = request_json(baseurl, "/api/tags")
        if args.json:
            print_json(payload)
        else:
            print_tags(payload, args.table)


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        execute(args)
        return 0
    except RbookClientError as error:
        print_error(error, args.json)
        return error.exit_status


if __name__ == "__main__":
    raise SystemExit(main())
