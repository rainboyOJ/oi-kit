# OI Kit：竞赛训练工具箱

一套面向 OI/OJ 学习的工具包（洛谷/CSP/NOIP 等）：自包含 CLI、Pi 斜杠命令、
学习教练 skill。把 Pi 变成一个"学习教练"：引导学生按 `题意 → 暴力 → 瓶颈 → 优化 → 正解 → 样例 → 对拍 → 复盘` 的顺序解题，并在复盘阶段自动把题目用到的知识点关联到 [rbook 算法电子书](https://rbook2.roj.ac.cn) 的对应章节，沉淀到题目目录的 `index.md`。

本包自包含，可整体拷到任意 rbook 风格的项目使用，不依赖外部项目脚本。

## 目录结构

```text
.
├── AGENTS.md                 # 学习政策与复盘规范（AI 行为约束，Pi 自动加载）
├── .pi/
│   ├── prompts/              # /oj-* 斜杠命令（prompt templates）
│   ├── skills/
│   │   ├── oj-student-coach/     # 学习流程教练 skill
│   │   ├── oj-cpp-rbook-style/   # rbook 风格 C++ 规范 skill
│   │   └── rbook-http/           # rbook 知识库 HTTP 检索 skill
│   └── oj-tools/
│       ├── bin/oj            # 自包含 CLI 入口
│       ├── scripts/oj_cli.py # CLI 实现
│       └── templates/        # 题目骨架模板（main/brute/gen/index）
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

### 1. 在 Pi 里使用（推荐）

在 Pi 会话里直接用斜杠命令（来自 `.pi/prompts/`），AI 会按 `AGENTS.md` 政策引导学生：
修改 `.pi/prompts/` 或 `.pi/skills/` 后执行 `/reload` 即可在本会话生效，无需重启：

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
/oj-judge                     完整评测（走 cgroup，能判 MLE）
/oj-review                    审查你的 main.cpp
/oj-reference                 最后阶段：给参考正解 + 复盘知识点关联
```

完整列表见 `.pi/prompts/oj-help.md`，在会话里执行 `/oj-help` 也会显示。

> **首次使用需信任本项目**：`.pi/prompts` 与 `.pi/skills` 属于受项目信任保护的资源。
> 首次在项目里启动 Pi 时会询问，选信任即可（或用 `/trust` 保存决定）。`AGENTS.md` 不受此限制。
> 改完 `.pi/prompts/` 或 `.pi/skills/` 后执行 `/reload` 即可在本会话生效。

### 2. 在命令行直接用 CLI

CLI 不依赖 Pi，可在任何终端跑（也可用 `oj` 相对路径 `.pi/oj-tools/bin/oj`）：

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

# 完整评测（走 cgroup，能判 MLE；需先装 roj-local-judge-lite）
oj judge problems/luogu/1001
```

> 注意：`oj new luogu/P1001`（用斜杠连写）会被解析成 problem_id=`luogu/P1001`，生成 `problems/luogu/luogu/p1006` 双层目录。请用空格分隔 `oj new luogu P1001`。

## 三个“跑代码”命令的分工

三者不重复，按目的选：

| 命令 | 用途 | 依赖 | 平台 |
| --- | --- | --- | --- |
| `oj run` | 单点快速跑一下，看输出/报错 | 无 | 任意 |
| `oj sample` | 跑题目里的全部样例，比答案 | 无（纯 Python + g++） | 任意 |
| `oj judge` | 完整验收：cgroup 计量内存、能判 MLE/TLE 边界 | `roj-local-judge-lite` | **仅 Linux** |

`oj judge` 不在本仓库内实现评测，而是调用 [roj-local-judge-lite](https://github.com/rainboyOJ/roj-local-judge-lite)
的 `judge.py`（运行时调用，不拷代码，两边各自演进）。先装好：

```bash
git clone https://github.com/rainboyOJ/roj-local-judge-lite
cd roj-local-judge-lite && ./install.sh
```

默认在 `~/.local/share/roj-local-judge-lite/judge.py` 和 `~/mycode/roj-local-judge-lite/judge.py`
下找；也可以显式指定（给了就用它，写错直接报错，不会静默回退）：

```bash
OI_KIT_JUDGE=/path/to/judge.py oj judge problems/luogu/1001
```

为什么需要它：`oj sample` 用 `timeout + subprocess`，只能判出“超时”和“答案不同”，
**看不到真实内存用量**。内存超限（MLE）是 OI 里的常见失分点，而“瞬时申请大内存再释放”
这种形态只有 cgroup 的 `memory.peak` 测得准。

```bash
# 完整评测，结果用 JSON（便于 AI 或脚本读）
oj judge problems/luogu/1001 --json

# 覆盖题目限制
OJ_KIT_JUDGE=/path/to/judge.py oj judge problems/luogu/1001 --time 2000 --memory 256
```

判定取值：`AC` `WA` `TLE` `MLE` `RE` `SE`（评测环境问题）`CE`。
若输出里出现 `isolation: degraded`，说明 cgroup 不可用，此时 **MLE 不可信**。

## 复盘与 rbook 知识点关联

`/oj-reference` 在给出参考代码后会进入复盘，按下列流程把本题知识点匹配到 rbook 章节：

1. 前置校验：`oj status` + `oj sample`（建议 `oj duipai`）。未通过则跳过复盘并提示先修代码。
2. 从 `problem.md` + `main.cpp` 提取知识点列表（如 `["组合枚举", "素数判定"]`）。
3. 一键匹配：

   ```bash
   python .pi/skills/rbook-http/scripts/rbook_match.py "组合枚举" "素数判定" --pretty
   ```

   - 内部 catalog 优先 + 搜索降级，每个知识点取 top-1 篇，输出 `{tag, title, url, score, source}`。
   - catalog 走天级缓存 `.pi/oj-tools/.cache/rbook-catalog-visible-<YYYY-MM-DD>.json`，命中缓存时 stderr 会提示「使用缓存……如需最新数据，删除该文件或加 `--no-cache` 更新缓存」。
   - rbook 内容更新后或当天缓存过期时，加 `--no-cache` 强制重拉并刷新缓存。
4. 写入题目目录的 `index.md`：
   - frontmatter `tags` 填知识点名称；
   - frontmatter `rbook` 填数组，每项 `{tag, title, url}`；
   - 正文 `### 知识点` 小节逐个知识点写一两句思想，并附 `[<文章标题>](https://rbook2.roj.ac.cn<url>)` 可点击引用。
5. `source` 为 `none` 时如实标注"rbook 暂无对应章节"，不硬凑。

rbook 默认走线上 `https://rbook2.roj.ac.cn`。本地有 rbook 服务时设 `RBOOK_BASE_URL=http://127.0.0.1:3000` 或脚本传 `--local` 覆盖。

## 示例：跑一遍 P1036

```bash
oj new luogu P1036
oj fetch luogu P1036
# 写好 main.cpp
oj sample problems/luogu/1036
# 可选：再写 brute.cpp + gen.cpp
oj duipai problems/luogu/1036 100
# 在 Pi 里：
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
- 详见 `skills/oj-cpp-rbook-style/SKILL.md`（即 `.pi/skills/oj-cpp-rbook-style/SKILL.md`）。

## 迁移到别的项目

本包自包含：把 `.pi/` 目录与 `AGENTS.md` 拷到任意 rbook 风格项目即可，无需安装额外依赖
（Python 脚本只用标准库；Pi 按约定目录发现资源，无需配置文件）。`problems/` 目录会被 gitignore，
工作产出不污染仓库。完整的 agent 安装流程见 `install-pi.md`。