# OpenCode OJ Learning Rules

This `.opencode` package is for students learning OJ problems in rbook-style projects.

## Project Shape

Assume the target project uses:

```text
problems/<oj>/<problem_id>/
  problem.md
  index.md
  main.cpp
  brute.cpp
  gen.cpp
  in / out / in1 / out1
```

Use the self-contained helper:

```bash
.opencode/oj-tools/bin/oj
```

Do not depend on external project scripts.

## Learning Policy

Default to learning-first help:

```text
题意 -> 暴力 -> 瓶颈 -> 优化 -> main.cpp -> 样例 -> 对拍 -> 复盘
```

Do not directly produce full optimized `main.cpp` unless the user explicitly asks for reference/final solution or uses `/oj-reference`.

Allowed by default:

- explain the statement;
- help write `brute.cpp`;
- help write `gen.cpp`;
- review/debug student `main.cpp`;
- run `oj sample` and `oj duipai`.

## Recap Stage: Knowledge and rbook References

复盘闭环在 `/oj-reference` 给出参考代码后追加触发，使用 `skills/rbook-http` skill。
进入复盘前必须先 `oj sample`（有 `brute.cpp`+`gen.cpp` 时建议 `oj duipai`）校验 `main.cpp`，未通过则跳过复盘并提示学生先修复代码。

需要判定内存是否超限（MLE）时，用 `oj judge`（走 cgroup，需装 roj-local-judge-lite，仅 Linux）。
`oj sample` 用 `timeout + subprocess`，看不到真实内存用量，所以它能给 AC 不等于内存安全。

- 从 `problem.md` + `main.cpp` 提取本题涉及的知识点列表；
- 调 `skills/rbook-http/scripts/rbook_match.py "知识点1" "知识点2" ...`：catalog 优先 + 搜索降级 + 天级缓存，命中缓存时通知用户并给出 `--no-cache` 更新方式；
- 每个知识点 top-1 篇文章，不贴模板代码正文；
- 把结果写入题目目录的 `index.md`：
  - `frontmatter.tags` 放知识点名称；
  - `frontmatter.rbook` 放数组 `[{tag, title, url}]`；
  - 正文新增 `### 知识点` 小节，逐个知识点写一两句思想并附 `[<文章标题>](<BASE_URL + url>)` 引用。
- 默认 `BASE_URL=https://rbook2.roj.ac.cn`（线上），`RBOOK_BASE_URL` 或 `--local` 可切本地。
- rbook 中确无对应章节时如实标注，不硬凑。

## Commands

Prefer these commands:

```text
/oj-new
/oj-fetch
/oj-status
/oj-hint
/oj-brute
/oj-gen
/oj-run
/oj-sample
/oj-duipai
/oj-judge
/oj-review
/oj-reference
```

## C++ Style

Use C++17, simple loops, global arrays where appropriate, useful Chinese comments, no lambda, no structured bindings, no C++20 features, and no clever macro-heavy style.
