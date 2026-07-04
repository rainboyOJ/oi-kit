#!/usr/bin/env python3
"""Self-contained OJ helper for rbook-style problem directories.

This tool is intentionally small and deterministic.  It is designed to live
inside .opencode/ so it can be moved to another rbook-style project together
with OpenCode commands and skills.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, asdict
import datetime as dt
import difflib
from html import unescape
from html.parser import HTMLParser
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile
from typing import Any
from http.cookiejar import CookieJar
from urllib.error import URLError
from urllib.request import HTTPCookieProcessor, Request, build_opener


SCRIPT_DIR = Path(__file__).resolve().parent
TOOLS_DIR = SCRIPT_DIR.parent
OPENCODE_DIR = TOOLS_DIR.parent
TEMPLATE_DIR = TOOLS_DIR / "templates"


class OjError(RuntimeError):
    pass


@dataclass
class Sample:
    input: str
    output: str


@dataclass
class ProblemData:
    oj: str
    problem_id: str
    dir_id: str
    title: str
    source: str
    statement_md: str = ""
    samples: list[Sample] | None = None
    fetched: bool = False
    warnings: list[str] | None = None


def print_json(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def shell_join(cmd: list[str]) -> str:
    return " ".join(shlex.quote(x) for x in cmd)


def normalize_output(text: str) -> str:
    lines = [line.rstrip() for line in text.replace("\r\n", "\n").splitlines()]
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines) + ("\n" if lines else "")


def find_project_root(start: Path | None = None) -> Path:
    cur = (start or Path.cwd()).resolve()
    for path in [cur, *cur.parents]:
        if (path / "problems").is_dir():
            return path
        if (path / ".opencode").is_dir():
            return path
    return cur


def real_luogu_id(problem_id: str) -> str:
    raw = problem_id.strip()
    if raw.lower().startswith("p"):
        return "P" + raw[1:]
    if raw.isdigit():
        return "P" + raw
    return raw.upper()


def luogu_dir_id(problem_id: str) -> str:
    real = real_luogu_id(problem_id)
    return real[1:] if real.lower().startswith("p") else real.lower()


def parse_problem_target(args: list[str], *, default_oj: str = "luogu") -> tuple[str, str]:
    if not args:
        raise OjError("缺少题号。例：oj fetch P1001 或 oj fetch luogu P1001")
    if len(args) == 1:
        value = args[0]
        if value.startswith("https://"):
            m = re.search(r"luogu\.com(?:\.cn)?/problem/([^/?#]+)", value)
            if not m:
                raise OjError(f"无法识别题目 URL：{value}")
            return "luogu", m.group(1)
        return default_oj, value
    return args[0].lower(), args[1]


def problem_dir_for(root: Path, oj: str, problem_id: str) -> tuple[Path, str]:
    if oj != "luogu":
        raise OjError("第一版只支持 luogu。")
    dir_id = luogu_dir_id(problem_id)
    return root / "problems" / oj / dir_id, real_luogu_id(problem_id)


def infer_problem_dir(root: Path, explicit: str | None = None) -> Path:
    if explicit:
        path = Path(explicit)
        return path if path.is_absolute() else root / path

    cur = Path.cwd().resolve()
    try:
        rel = cur.relative_to(root / "problems")
    except ValueError:
        raise OjError("当前不在题目目录中，请传入题目目录或先 cd 到 problems/<oj>/<id>。")
    if len(rel.parts) < 2:
        raise OjError("当前不在具体题目目录中，请进入 problems/<oj>/<id>。")
    return root / "problems" / rel.parts[0] / rel.parts[1]


def read_template(name: str) -> str:
    return (TEMPLATE_DIR / name).read_text(encoding="utf-8")


def write_if_missing(path: Path, content: str, *, force: bool = False) -> bool:
    if path.exists() and not force:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def create_problem_skeleton(problem_dir: Path, oj: str, problem_id: str, title: str, source: str) -> dict[str, list[str]]:
    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    created: list[str] = []
    skipped: list[str] = []
    files = {
        "index.md": read_template("index.md").format(
            oj=oj,
            problem_id=problem_id,
            title=title.replace('"', '\\"'),
            source=source,
            date=now,
        ),
        "main.cpp": read_template("main.cpp"),
        "brute.cpp": read_template("brute.cpp"),
        "gen.cpp": read_template("gen.cpp"),
    }
    for filename, content in files.items():
        path = problem_dir / filename
        if write_if_missing(path, content):
            created.append(str(path))
        else:
            skipped.append(str(path))
    workspace = problem_dir / "problem-analysis-workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    stages = [
        ("01-problem-understanding.md", "题意理解"),
        ("02-observation-and-model.md", "关键观察与模型"),
        ("03-solution-derivation.md", "解法推导"),
        ("04-correctness-and-edge-cases.md", "正确性与边界情况"),
        ("05-complexity-and-implementation.md", "复杂度与实现"),
        ("06-final-index-draft.md", "最终题解草稿"),
    ]
    for filename, heading in stages:
        path = workspace / filename
        if write_if_missing(path, f"# {heading}\n\n"):
            created.append(str(path))
        else:
            skipped.append(str(path))
    return {"created": created, "skipped": skipped}


class ElementByIdParser(HTMLParser):
    def __init__(self, target_id: str):
        super().__init__(convert_charrefs=False)
        self.target_id = target_id
        self.capture = False
        self.depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if dict(attrs).get("id") == self.target_id:
            self.capture = True
            self.depth = 1
            return
        if self.capture:
            self.depth += 1

    def handle_endtag(self, tag: str) -> None:
        if self.capture:
            self.depth -= 1
            if self.depth <= 0:
                self.capture = False

    def handle_data(self, data: str) -> None:
        if self.capture:
            self.parts.append(data)

    def content(self) -> str:
        return "".join(self.parts).strip()


def extract_element_by_id(html: str, element_id: str) -> str:
    parser = ElementByIdParser(element_id)
    parser.feed(html)
    return unescape(parser.content())


def markdown_section(title: str, content: Any) -> str:
    if not isinstance(content, str) or not content.strip():
        return ""
    return f"## {title}\n\n{content.strip()}\n"


def fetch_luogu(problem_id: str) -> ProblemData:
    real_id = real_luogu_id(problem_id)
    source = f"https://www.luogu.com.cn/problem/{real_id}"
    warnings: list[str] = []
    try:
        req = Request(
            source,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
                )
            },
        )
        opener = build_opener(HTTPCookieProcessor(CookieJar()))
        with opener.open(req, timeout=15) as resp:
            charset = resp.headers.get_content_charset() or "utf-8"
            html = resp.read().decode(charset, errors="replace")
        raw_json = extract_element_by_id(html, "lentille-context")
        if not raw_json:
            raise OjError("未找到洛谷页面中的 lentille-context 数据。")
        raw = json.loads(raw_json)
        problem = (((raw.get("data") or {}).get("problem")) or {})
        if not isinstance(problem, dict):
            raise OjError("洛谷页面 JSON 中缺少 problem 对象。")
        content = problem.get("content") or problem.get("contenu") or {}
        merged = dict(problem)
        if isinstance(content, dict):
            merged.update(content)
        title = str(problem.get("title") or problem.get("name") or merged.get("name") or real_id).strip()
        samples = parse_luogu_samples(problem.get("samples"))
        statement = build_luogu_statement(real_id, title, merged, samples)
        return ProblemData("luogu", real_id, luogu_dir_id(problem_id), title, source, statement, samples, True, warnings)
    except (URLError, json.JSONDecodeError, OjError) as exc:
        warnings.append(f"题面/样例抓取失败，仅创建 skeleton：{exc}")
        return ProblemData("luogu", real_id, luogu_dir_id(problem_id), real_id, source, "", [], False, warnings)


def parse_luogu_samples(raw_samples: Any) -> list[Sample]:
    samples: list[Sample] = []
    if not isinstance(raw_samples, list):
        return samples
    for item in raw_samples:
        input_data = ""
        output_data = ""
        if isinstance(item, list) and len(item) >= 2:
            input_data = str(item[0])
            output_data = str(item[1])
        elif isinstance(item, dict):
            input_data = str(item.get("input") or "")
            output_data = str(item.get("output") or "")
        if input_data or output_data:
            samples.append(Sample(input_data, output_data))
    return samples


def build_luogu_statement(display_id: str, title: str, problem: dict[str, Any], samples: list[Sample]) -> str:
    sections = [f"# {display_id} {title}".strip(), ""]
    sections.append(markdown_section("题目背景", problem.get("background")))
    sections.append(markdown_section("题目描述", problem.get("description")))
    sections.append(markdown_section("输入格式", problem.get("inputFormat") or problem.get("input")))
    sections.append(markdown_section("输出格式", problem.get("outputFormat") or problem.get("output")))
    if samples:
        parts: list[str] = []
        for index, sample in enumerate(samples, start=1):
            parts.append(
                "\n".join(
                    [
                        f"## 输入输出样例 #{index}",
                        "",
                        f"### 输入 #{index}",
                        "",
                        "```",
                        sample.input.rstrip(),
                        "```",
                        "",
                        f"### 输出 #{index}",
                        "",
                        "```",
                        sample.output.rstrip(),
                        "```",
                    ]
                )
            )
        sections.append("\n\n".join(parts) + "\n")
    sections.append(markdown_section("说明/提示", problem.get("hint")))
    return "\n".join(part for part in sections if part != "").rstrip() + "\n"


def discover_cases(problem_dir: Path) -> list[tuple[str, Path, Path | None]]:
    cases: list[tuple[str, Path, Path | None]] = []
    root_inputs = sorted(
        [p for p in problem_dir.iterdir() if p.is_file() and re.fullmatch(r"in(\d*)", p.name)],
        key=lambda p: (int(re.fullmatch(r"in(\d*)", p.name).group(1) or "0"), p.name),  # type: ignore[union-attr]
    )
    for inp in root_inputs:
        suffix = re.fullmatch(r"in(\d*)", inp.name).group(1)  # type: ignore[union-attr]
        ans = inp.with_name(f"out{suffix}")
        cases.append((inp.name, inp, ans if ans.exists() else None))
    data_dir = problem_dir / "data"
    if data_dir.is_dir():
        for inp in sorted(data_dir.glob("*.in")):
            ans = inp.with_suffix(".out")
            if not ans.exists():
                ans = inp.with_suffix(".ans")
            cases.append((f"data/{inp.name}", inp, ans if ans.exists() else None))
    return cases


def build_dir(root: Path) -> Path:
    path = root / ".opencode" / "oj-tools" / ".build"
    path.mkdir(parents=True, exist_ok=True)
    return path


def compile_cpp(src: Path, root: Path) -> Path:
    if not src.exists():
        raise OjError(f"源文件不存在：{src}")
    digest = hashlib.sha1(str(src.resolve()).encode()).hexdigest()[:12]
    out = build_dir(root) / f"{src.stem}-{digest}.out"
    if out.exists() and out.stat().st_mtime >= src.stat().st_mtime:
        return out
    cmd = ["g++", "-std=c++17", "-O2", "-pipe", str(src), "-o", str(out)]
    result = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        raise OjError("编译失败：\n" + result.stderr)
    return out


def run_executable(exe: Path, input_data: str, timeout: float) -> tuple[int, str, str, bool]:
    try:
        result = subprocess.run(
            [str(exe)],
            input=input_data,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
        )
        return result.returncode, result.stdout, result.stderr, False
    except subprocess.TimeoutExpired as exc:
        return 124, exc.stdout or "", exc.stderr or "", True


def cmd_new(args: argparse.Namespace) -> int:
    root = find_project_root()
    oj, pid = parse_problem_target(args.target)
    problem_dir, display_id = problem_dir_for(root, oj, pid)
    source = f"https://www.luogu.com.cn/problem/{display_id}" if oj == "luogu" else ""
    result = create_problem_skeleton(problem_dir, oj, display_id, args.title or display_id, source)
    output = {"problem_dir": str(problem_dir), **result}
    if args.json:
        print_json(output)
    else:
        print(f"题目目录：{problem_dir}")
        for key, title in [("created", "创建"), ("skipped", "已存在，跳过")]:
            if output[key]:
                print(f"\n{title}：")
                for item in output[key]:
                    print(f"- {item}")
    return 0


def cmd_fetch(args: argparse.Namespace) -> int:
    root = find_project_root()
    oj, pid = parse_problem_target(args.target)
    if oj != "luogu":
        raise OjError("第一版只支持 luogu。")
    data = fetch_luogu(pid)
    problem_dir = root / "problems" / data.oj / data.dir_id
    result = create_problem_skeleton(problem_dir, data.oj, data.problem_id, data.title, data.source)
    written: list[str] = []
    skipped: list[str] = []
    if data.statement_md:
        path = problem_dir / "problem.md"
        if write_if_missing(path, data.statement_md, force=args.force_statement):
            written.append(str(path))
        else:
            skipped.append(str(path))
    for i, sample in enumerate(data.samples or [], start=1):
        for filename, content, force in [
            (f"in{i}", sample.input, args.force_samples),
            (f"out{i}", sample.output, args.force_samples),
        ]:
            path = problem_dir / filename
            if write_if_missing(path, content.rstrip() + "\n", force=force):
                written.append(str(path))
            else:
                skipped.append(str(path))
        if i == 1:
            path = problem_dir / "in"
            if write_if_missing(path, sample.input.rstrip() + "\n", force=args.force_samples):
                written.append(str(path))
            else:
                skipped.append(str(path))
    output = {
        "problem_dir": str(problem_dir),
        "fetched": data.fetched,
        "warnings": data.warnings or [],
        "created": result["created"],
        "skipped": result["skipped"] + skipped,
        "written": written,
    }
    if args.json:
        print_json(output)
    else:
        print(f"题目目录：{problem_dir}")
        print(f"抓取结果：{'成功' if data.fetched else '未抓取到完整题面'}")
        for warning in data.warnings or []:
            print(f"警告：{warning}")
        if written:
            print("\n写入：")
            for item in written:
                print(f"- {item}")
        if result["created"]:
            print("\n创建：")
            for item in result["created"]:
                print(f"- {item}")
        if result["skipped"] or skipped:
            print("\n已存在，跳过：")
            for item in result["skipped"] + skipped:
                print(f"- {item}")
    return 0


def status_data(problem_dir: Path) -> dict[str, Any]:
    expected = ["problem.md", "index.md", "main.cpp", "brute.cpp", "gen.cpp"]
    files = {name: (problem_dir / name).exists() for name in expected}
    cases = discover_cases(problem_dir) if problem_dir.exists() else []
    ready_sample = files["main.cpp"] and bool(cases)
    ready_duipai = files["main.cpp"] and files["brute.cpp"] and files["gen.cpp"]
    suggestions: list[str] = []
    if not files["problem.md"]:
        suggestions.append("缺少 problem.md：先运行 oj fetch Pxxxx。")
    if not files["main.cpp"]:
        suggestions.append("缺少 main.cpp：先写正式代码。")
    if not files["brute.cpp"]:
        suggestions.append("缺少 brute.cpp：先写小数据暴力解。")
    if not files["gen.cpp"]:
        suggestions.append("缺少 gen.cpp：先写 C++ 随机数据生成器。")
    if not cases:
        suggestions.append("缺少样例数据：需要 in/out 或 data/*.in。")
    if ready_duipai:
        suggestions.append("三件套齐全，可以运行 oj duipai 100。")
    return {
        "problem_dir": str(problem_dir),
        "exists": problem_dir.exists(),
        "files": files,
        "sample_cases": [name for name, _, _ in cases],
        "ready_sample": ready_sample,
        "ready_duipai": ready_duipai,
        "suggestions": suggestions,
    }


def cmd_status(args: argparse.Namespace) -> int:
    root = find_project_root()
    problem_dir = infer_problem_dir(root, args.problem_dir)
    data = status_data(problem_dir)
    if args.json:
        print_json(data)
    else:
        print(f"题目目录：{data['problem_dir']}")
        print("\n文件：")
        for name, ok in data["files"].items():
            print(f"- {name:<10} {'OK' if ok else '缺少'}")
        print("\n样例：")
        if data["sample_cases"]:
            for name in data["sample_cases"]:
                print(f"- {name}")
        else:
            print("- 缺少")
        print("\n下一步建议：")
        for item in data["suggestions"]:
            print(f"- {item}")
    return 0 if data["exists"] else 2


def cmd_run(args: argparse.Namespace) -> int:
    root = find_project_root()
    problem_dir = infer_problem_dir(root, args.problem_dir)
    src = problem_dir / args.source
    exe = compile_cpp(src, root)
    input_data = ""
    if args.input:
        input_data = (problem_dir / args.input).read_text(encoding="utf-8")
    elif (problem_dir / "in").exists():
        input_data = (problem_dir / "in").read_text(encoding="utf-8")
    else:
        input_data = sys.stdin.read()
    code, stdout, stderr, timed_out = run_executable(exe, input_data, args.timeout)
    if args.json:
        print_json({"returncode": code, "stdout": stdout, "stderr": stderr, "timed_out": timed_out})
    else:
        if stderr:
            print(stderr, file=sys.stderr, end="")
        print(stdout, end="")
        if timed_out:
            print(f"\nTIMEOUT: 超过 {args.timeout} 秒", file=sys.stderr)
    return 1 if code != 0 or timed_out else 0


def cmd_sample(args: argparse.Namespace) -> int:
    root = find_project_root()
    problem_dir = infer_problem_dir(root, args.problem_dir)
    exe = compile_cpp(problem_dir / args.source, root)
    cases = discover_cases(problem_dir)
    if not cases:
        raise OjError("未找到样例：需要 in/out 或 data/*.in。")
    results: list[dict[str, Any]] = []
    ok_all = True
    for name, inp, ans in cases:
        input_data = inp.read_text(encoding="utf-8")
        code, stdout, stderr, timed_out = run_executable(exe, input_data, args.timeout)
        expected = ans.read_text(encoding="utf-8") if ans else None
        ok = code == 0 and not timed_out
        diff = ""
        if expected is not None:
            ok = ok and normalize_output(stdout) == normalize_output(expected)
            if not ok:
                diff = "".join(
                    difflib.unified_diff(
                        normalize_output(expected).splitlines(True),
                        normalize_output(stdout).splitlines(True),
                        fromfile="expected",
                        tofile="actual",
                    )
                )
        ok_all = ok_all and ok
        results.append(
            {
                "name": name,
                "ok": ok,
                "returncode": code,
                "timed_out": timed_out,
                "stderr": stderr,
                "stdout": stdout,
                "has_answer": expected is not None,
                "diff": diff,
            }
        )
    if args.json:
        print_json({"ok": ok_all, "cases": results})
    else:
        for item in results:
            print(f"[{'OK' if item['ok'] else 'FAIL'}] {item['name']}")
            if item["stderr"]:
                print(item["stderr"], file=sys.stderr, end="")
            if not item["has_answer"]:
                print(item["stdout"], end="")
            if item["diff"]:
                print(item["diff"], end="")
        print("样例检查通过。" if ok_all else "样例检查失败。")
    return 0 if ok_all else 1


def cmd_duipai(args: argparse.Namespace) -> int:
    root = find_project_root()
    problem_dir = infer_problem_dir(root, args.problem_dir)
    missing = [name for name in ["main.cpp", "brute.cpp", "gen.cpp"] if not (problem_dir / name).exists()]
    if missing:
        raise OjError("对拍需要三件套，缺少：" + ", ".join(missing))
    main_exe = compile_cpp(problem_dir / "main.cpp", root)
    brute_exe = compile_cpp(problem_dir / "brute.cpp", root)
    gen_exe = compile_cpp(problem_dir / "gen.cpp", root)
    failed_dir = problem_dir / "duipai-failed"
    results: list[dict[str, Any]] = []
    for i in range(1, args.count + 1):
        g_code, test_input, g_err, g_timeout = run_executable(gen_exe, "", args.timeout)
        if g_code != 0 or g_timeout:
            raise OjError(f"gen.cpp 第 {i} 次运行失败：{g_err}")
        u_code, user_out, user_err, u_timeout = run_executable(main_exe, test_input, args.timeout)
        b_code, brute_out, brute_err, b_timeout = run_executable(brute_exe, test_input, args.timeout)
        ok = (
            u_code == 0
            and b_code == 0
            and not u_timeout
            and not b_timeout
            and normalize_output(user_out) == normalize_output(brute_out)
        )
        results.append({"case": i, "ok": ok})
        if not ok:
            failed_dir.mkdir(parents=True, exist_ok=True)
            (failed_dir / "failed.in").write_text(test_input, encoding="utf-8")
            (failed_dir / "user.out").write_text(user_out, encoding="utf-8")
            (failed_dir / "brute.out").write_text(brute_out, encoding="utf-8")
            (failed_dir / "user.err").write_text(user_err, encoding="utf-8")
            (failed_dir / "brute.err").write_text(brute_err, encoding="utf-8")
            diff = "".join(
                difflib.unified_diff(
                    normalize_output(brute_out).splitlines(True),
                    normalize_output(user_out).splitlines(True),
                    fromfile="brute",
                    tofile="main",
                )
            )
            output = {
                "ok": False,
                "failed_case": i,
                "failed_dir": str(failed_dir),
                "user_returncode": u_code,
                "brute_returncode": b_code,
                "user_timed_out": u_timeout,
                "brute_timed_out": b_timeout,
                "diff": diff,
            }
            if args.json:
                print_json(output)
            else:
                print(f"对拍失败：第 {i} 组")
                print(f"失败数据已保存：{failed_dir}")
                if diff:
                    print(diff, end="")
            return 1
        if not args.json and (i == 1 or i % max(1, args.count // 10) == 0):
            print(f"已通过 {i}/{args.count}")
    if args.json:
        print_json({"ok": True, "count": args.count, "cases": results})
    else:
        print(f"对拍通过：{args.count} 组")
    return 0


def cmd_gen(args: argparse.Namespace) -> int:
    root = find_project_root()
    problem_dir = infer_problem_dir(root, args.problem_dir)
    path = problem_dir / "gen.cpp"
    wrote = write_if_missing(path, read_template("gen.cpp"), force=args.force)
    data = {"path": str(path), "written": wrote}
    if args.json:
        print_json(data)
    else:
        print(f"{'写入' if wrote else '已存在，跳过'}：{path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="oj", description="OpenCode OJ student helper")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("new", help="创建 rbook 风格题目目录")
    p.add_argument("target", nargs="+")
    p.add_argument("--title", default="")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_new)

    p = sub.add_parser("fetch", help="下载洛谷题面和样例，默认不覆盖已有文件")
    p.add_argument("target", nargs="+")
    p.add_argument("--force-statement", action="store_true")
    p.add_argument("--force-samples", action="store_true")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_fetch)

    p = sub.add_parser("status", help="检查当前题目材料状态")
    p.add_argument("problem_dir", nargs="?")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("run", help="编译并运行 main.cpp")
    p.add_argument("problem_dir", nargs="?")
    p.add_argument("--source", default="main.cpp")
    p.add_argument("--input", default="")
    p.add_argument("--timeout", type=float, default=2.0)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_run)

    p = sub.add_parser("sample", help="编译 main.cpp 并检查样例")
    p.add_argument("problem_dir", nargs="?")
    p.add_argument("--source", default="main.cpp")
    p.add_argument("--timeout", type=float, default=2.0)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_sample)

    p = sub.add_parser("duipai", help="对拍 main.cpp / brute.cpp / gen.cpp")
    p.add_argument("count", nargs="?", type=int, default=100)
    p.add_argument("problem_dir", nargs="?")
    p.add_argument("--timeout", type=float, default=2.0)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_duipai)

    p = sub.add_parser("gen", help="创建或重置 gen.cpp 模板")
    p.add_argument("problem_dir", nargs="?")
    p.add_argument("--force", action="store_true")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_gen)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.func(args)
    except OjError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
