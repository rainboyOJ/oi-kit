---
name: oj-cpp-rbook-style
description: Use when writing or reviewing C++17 OJ code for rbook-style learning projects. Enforce clear Chinese competitive-programming style: simple loops, global arrays when useful, no lambda, no structured bindings, no C++20, useful Chinese comments, readable main.cpp/brute.cpp/gen.cpp, and code that students can debug.
---

# OJ C++ rbook Style

Use C++17. Write code as a student can read, trace, and debug.

## Hard Rules

Do not use:

- lambda expressions;
- structured bindings;
- C++20/23 features;
- ranges;
- complex template metaprogramming;
- clever macros like `rep`, `all`, `pb`;
- unnecessary classes or generic abstractions.

Prefer:

- global arrays for main data;
- clear `for` loops;
- simple helper functions such as `read_input()`, `solve()`, `check()`, `dfs()`;
- Chinese comments for state definition, transition, greedy choice, graph meaning, and edge cases.

## main.cpp

`main.cpp` is the optimized solution. It should:

- match the problem input/output exactly;
- use clear variable names;
- include comments at key logic points;
- avoid over-modern C++ tricks;
- be suitable for a Chinese OJ explanation.

## brute.cpp

`brute.cpp` is the small-data trusted solution. It should:

- have the same input/output format as `main.cpp`;
- prioritize direct correctness over speed;
- include a header comment:

```cpp
// brute.cpp：小数据暴力解，用来帮助理解题意并辅助对拍。
```

- make the bottleneck visible.

## gen.cpp

`gen.cpp` is the C++ random data generator for duipai. Use this style:

```cpp
// gen.cpp：随机数据生成器，用于对拍。
#include <bits/stdc++.h>
using namespace std;

const int MAXN = 1000000;

random_device rd;
mt19937 mtrnd(rd());

int rnd(int l, int r) {
    uniform_int_distribution<int> dist(l, r);
    return dist(mtrnd);
}
```

Keep generated constraints small enough for `brute.cpp` unless explicitly stress-testing performance.

## Review Priorities

When reviewing code, report:

1. correctness bugs;
2. missing edge cases;
3. complexity mismatch;
4. implementation risks;
5. style issues.

Do not rewrite the whole program when a local fix is enough.
