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
/oj-review
/oj-reference
```

## C++ Style

Use C++17, simple loops, global arrays where appropriate, useful Chinese comments, no lambda, no structured bindings, no C++20 features, and no clever macro-heavy style.
