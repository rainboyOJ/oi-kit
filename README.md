# OpenCode OJ 学习工具包

一套面向 OJ 题目学习（洛谷/CSP/NOIP 等）的 OpenCode 配置包。把 OpenCode 变成一个"学习教练"：引导学生按 `题意 → 暴力 → 瓶颈 → 优化 → 正解 → 样例 → 对拍 → 复盘` 的顺序解题，并在复盘阶段自动把题目用到的知识点关联到 [rbook 算法电子书](https://rbook2.roj.ac.cn) 的对应章节，沉淀到题目目录的 `index.md`。

本包自包含，可整体拷到任意 rbook 风格的项目使用，不依赖外部项目脚本。

## 目录结构

```text
.
├── AGENTS.md                 # 学习政策与复盘规范（AI 行为约束）
├── opencode.json             # OpenCode 配置
├── commands/                 # /oj-* 斜杠命令
├── skills/
│   ├── oj-student-coach/      # 学习流程教练 skill
│   ├── oj-cpp-rbook-style/   # rbook 风格 C++ 规范 skill
│   └── rbook-http/           # rbook 知识库 HTTP 检索 skill
├── oj-tools/
│   ├── bin/oj                # 自包含 CLI 入口
│   ├── scripts/oj_cli.py     # CLI 实现
│   └── templates/            # 题目骨架模板（main/brute/gen/index）
└── problems/<oj>/<id>/       # 学生题目工作区（gitignore，不随仓库分发）
    ├── problem.md            # 题面
    ├── index.md             # 学习索引 + 复盘（含知识点+rbook 链接）
    ├── main.cpp             # 学生正解
    ├── brute.cpp            # 小数据暴力解
    ├── gen.cpp               # 随机数据生成器
    └── in / out / in1 / out1 # 样例数据
```

## 学习流程

默认按下面顺序推进，不要直接跳到正解代码：

```text
题意 → 暴力 → 瓶颈 → 优化 → main.cpp → 样例 → 对拍 → 复盘
```

复盘阶段只在 `main.cpp` 通过 `oj sample`（有暴力+生成器时建议 `oj duipai`）后才进行，由 `/oj-reference` 触发，自动找 rbook 章节填进 `index.md`。

## 快速开始

### 1. 在 OpenCode 里使用（推荐）

在 OpenCode 会话里直接用斜杠命令，AI 会按 `AGENTS.md` 政策引导学生：

```text
/oj-new luogu P1001          创建题目目录
/oj-fetch luogu P1001         抓取洛谷题面与样例
/oj-status                    查看当前题目状态
/oj-hint                      分层提示，不给完整正解
/oj-brute                     帮你写/改 brute.cpp
/oj-gen                       帮你写/改 gen.cpp
/oj-run                       编译运行 main.cpp
/oj-sample                    跑全部样例
/oj-duipai 100                main.cpp / brute.cpp / gen.cpp 对拍 100 组
/oj-review                    审查你的 main.cpp
/oj-reference                 最后阶段：给参考正解 + 复盘知识点关联
```

完整列表见 `commands/oj-help.md`。

### 2. 在命令行直接用 CLI

CLI 不依赖 OpenCode，可在任何终端跑：

```bash
# 新建题目目录（注意 oj 与题号分开传，不要写 luogu/P1001）
oj new luogu P1001

# 抓取洛谷题面与样例
oj fetch luogu P1001

# 查看状态
oj status problems/luogu/1001

# 编译运行 main.cpp
oj run problems/luogu/1001

# 跑样例
oj sample problems/luogu/1001

# 对拍（需先写好 brute.cpp 和 gen.cpp）
oj duipai problems/luogu/1001 100
```

> 注意：`oj new luogu/P1001`（用斜杠连写）会被解析成 problem_id=`luogu/P1001`，生成 `problems/luogu/luogu/p1006` 双层目录。请用空格分隔 `oj new luogu P1001`。

## 复盘与 rbook 知识点关联

`/oj-reference` 在给出参考代码后会进入复盘，按下列流程把本题知识点匹配到 rbook 章节：

1. 前置校验：`oj status` + `oj sample`（建议 `oj duipai`）。未通过则跳过复盘并提示先修代码。
2. 从 `problem.md` + `main.cpp` 提取知识点列表（如 `["组合枚举", "素数判定"]`）。
3. 先调 `rbook_catalog.py --scope visible` 在目录里按 `title`/`description`/`headings`/`tags` 匹配章节。
4. catalog 未命中再降级 `rbook_search.py "<知识点>"` 段落搜索兜底。
5. 每个知识点只取 top-1 篇，不贴模板代码正文。
6. 写入题目目录的 `index.md`：
   - frontmatter `tags` 填知识点名称；
   - frontmatter `rbook` 填数组，每项 `{tag, title, url}`；
   - 正文 `### 知识点` 小节逐个知识点写一两句思想，并附 `[<文章标题>](https://rbook2.roj.ac.cn<url>)` 可点击引用。
7. rbook 中确无对应章节时如实标注，不硬凑。

rbook 默认走线上 `https://rbook2.roj.ac.cn`。本地有 rbook 服务时设 `RBOOK_BASE_URL=http://127.0.0.1:3000` 或脚本传 `--local` 覆盖。

## 示例：跑一遍 P1036

```bash
oj new luogu P1036
oj fetch luogu P1036
# 写好 main.cpp
oj sample problems/luogu/1036
# 可选：再写 brute.cpp + gen.cpp
oj duipai problems/luogu/1036 100
# 在 OpenCode 里：
#   /oj-reference        → 给参考代码 + 复盘，自动填 index.md 的 tags / rbook / 知识点 小节
```

复盘后 `index.md` 形如：

```yaml
tags: [组合枚举, 素数判定]
rbook:
  - tag: 组合枚举
    title: 组合枚举
    url: /recursion/combination.html
  - tag: 素数判定
    title: 素数判定与素数筛
    url: /math/numberTheory/prime/index.html
```

正文 `### 知识点` 节里每条知识点一两句思想 + 可点击的 rbook 链接。

## C++ 风格

- C++17、简单循环、全局数组优先；
- 有用的中文注释；
- 不用 lambda、结构化绑定、C++20 特性、重宏风格；
- 详见 `skills/oj-cpp-rbook-style/SKILL.md`。

## 迁移到别的项目

本包自包含：把整个目录拷到任意 rbook 风格项目即可，无需安装额外依赖（Python 脚本只用标准库）。`problems/` 目录会被 gitignore，工作产出不污染仓库。