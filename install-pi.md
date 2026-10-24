# install-pi.md — 给 Pi agent 的安装手册

这份文档供 **Pi agent** 读取，说明如何把本 `.pi/` 工具包部署到一个 rbook 风格项目的 `.pi/` 目录，使其可用。

> 只覆盖**首次安装**。不包含更新/重装/卸载流程。
> OpenCode 版安装流程见 git 历史中的 `install-ai.md`（本项目已迁移到 Pi，不再维护该文件）。

## 何时使用

当你要把 “Pi OJ Student Toolkit” 安装进某个 rbook 风格项目时读取本文件并按步骤执行。装完后目标项目会获得：`/oj-*` 命令（prompt templates）、`oj-student-coach`、`oj-cpp-rbook-style`、`rbook-http` 三个 skill、以及自包含的 `oj` 命令行工具。

## 前置条件

| 依赖 | 用途 | 检查命令 | 安装时是否必需 |
| ---- | ---- | ---- | ---- |
| pi | 加载 prompts/skills/AGENTS.md | `pi --version` | 是 |
| python3 | 运行 `oj` CLI（纯标准库，无 pip 依赖） | `python3 --version` | 是 |
| g++ | 编译 `main.cpp`/`brute.cpp`/`gen.cpp` | `g++ --version` | 否（但 `oj run`/`sample`/`duipai` 需要） |

无需网络、无需 npm/bun install：Pi 按约定目录发现资源，本包不含需要拉取的插件。

## 路径约定

执行步骤前先确定两个路径：

- `SRC`：**本文件所在目录**，即 `.pi/` 源目录（包含 `oj-tools/`、`prompts/`、`skills/`，其父目录含 `AGENTS.md`、`README.md`）。
- `DST`：目标 rbook 项目根目录下的 `.pi/`。
  - 若部署到**包含本源目录的同一个项目**：`DST = "$SRC"`。
  - 若部署到**别的 rbook 项目**：`DST = "<目标项目根>/.pi"`。

目标项目无需预先存在 `problems/` 目录；`/oj-new` 会在首次创建题目时按需生成 `problems/<oj>/<id>/`。

## Pi 的加载约定（为什么这样部署）

Pi 按目录约定发现资源，**不需要配置文件**：

| 资源 | 位置 | 说明 |
| --- | --- | --- |
| 斜杠命令 | `<project>/.pi/prompts/*.md` | 文件名即命令名，`oj-new.md` → `/oj-new` |
| skill | `<project>/.pi/skills/<name>/SKILL.md` | 也支持 `~/.pi/agent/skills/` 与 `.agents/skills/` |
| 项目规则 | `<project>/AGENTS.md` | 工作目录及祖先目录的 `AGENTS.md` 自动作为上下文加载，无需配置 |

> **项目信任（必读）**：`.pi/prompts` 与 `.pi/skills` 是 Pi 的“受项目信任保护”资源。
> 首次在目标项目里启动 Pi 时它会询问是否信任该项目，选择信任（或 `/trust` 保存决定）后，
> `/oj-*` 命令与三个 skill 才会加载；非交互模式（`-p`/json/rpc）无法弹窗询问，需要显式 `--approve`。
> `AGENTS.md` 不受信任门槛限制，总是加载。
> 修改 `prompts/`、`skills/` 后在本会话执行 `/reload` 即可生效，无需重启。

## 安装步骤

以下命令中先把 `SRC`、`DST` 赋值为实际绝对路径：

```bash
SRC="<本文件所在的 .pi 源目录的绝对路径>"
DST="<目标项目的 .pi 绝对路径>"

# 1. 建立 DST 目录结构
mkdir -p "$DST"/oj-tools/bin "$DST"/oj-tools/scripts "$DST"/oj-tools/templates "$DST"/prompts "$DST"/skills

# 1b.（可选）单题提交到洛谷的工具
mkdir -p "$DST"/oj-tools/luogu-submit-helper/userscripts

# 2. 复制白名单文件（只复制工具自身拥有的文件）
cp "$SRC"/../AGENTS.md "$DST"/../AGENTS.md
cp "$SRC"/../README.md "$DST"/../README.md
cp "$SRC"/prompts/*.md              "$DST"/prompts/
cp -r "$SRC"/skills/*               "$DST"/skills/
cp "$SRC"/oj-tools/bin/oj           "$DST"/oj-tools/bin/
cp "$SRC"/oj-tools/scripts/oj_cli.py "$DST"/oj-tools/scripts/
cp "$SRC"/oj-tools/templates/*      "$DST"/oj-tools/templates/

# 2b.（可选）单题提交工具；tests/ 不部署
cp "$SRC"/oj-tools/luogu-submit-helper/README.md     "$DST"/oj-tools/luogu-submit-helper/
cp "$SRC"/oj-tools/luogu-submit-helper/luogu-submit "$DST"/oj-tools/luogu-submit-helper/
cp "$SRC"/oj-tools/luogu-submit-helper/install.sh   "$DST"/oj-tools/luogu-submit-helper/
cp "$SRC"/oj-tools/luogu-submit-helper/userscripts/*.user.js \
   "$DST"/oj-tools/luogu-submit-helper/userscripts/
chmod +x "$DST"/oj-tools/luogu-submit-helper/luogu-submit \
         "$DST"/oj-tools/luogu-submit-helper/install.sh

# 3. 让 oj 可执行
chmod +x "$DST"/oj-tools/bin/oj

# 4. 将 oj 加入 PATH（之后可以在任何目录直接运行 oj）
#    避免重复添加
line="export PATH=\"$DST/oj-tools/bin:\$PATH\""
for rc in ~/.zshrc ~/.bashrc; do
  grep -qxF "$line" "$rc" 2>/dev/null || echo "$line" >> "$rc"
done
```

**不要复制**以下文件（它们是开发产物或本手册本身）：

```text
install-pi.md          # 本手册，仅留在源端
opencode.json          # OpenCode 遗留配置
package.json / package-lock.json / bun.lock   # 本地插件开发产物
.gitignore             # 源端 git 忽略规则
oj-tools/.build/       # 构建缓存
oj-tools/luogu-submit-helper/tests/   # 上游测试，仅开发时跑
.pytest_cache/         # 测试缓存
**/__pycache__/        # python 字节码缓存
problems/              # 学生工作产出
```

`cp -r` 对已存在的同名子目录会做合并（覆盖同名文件、保留其它文件），因此 DST 中已有的非工具文件（用户自加的 prompt/skill）不会被删除。

> 若目标项目已有 `.pi/settings.json`：**不需要改**。`prompts/` 与 `skills/` 是 Pi 的约定目录，自动发现；除非你要从非约定目录加载，否则无需在 settings 里配置 `prompts`/`skills`。

> 若目标项目已维护自己的 `.pi/skills/rbook-http/`（例如从 `.agents/skills/rbook-http` 同步而来），可跳过第 2 步里 `skills/` 的 `rbook-http` 子目录，避免覆盖项目自有版本。

## 验证

1. **验证 `oj` CLI 可用**（纯本地，不依赖网络）：
   ```bash
   "$DST"/oj-tools/bin/oj --help
   ```
   应打印子命令列表（`new`/`fetch`/`status`/`run`/`sample`/`duipai`/`gen`/`judge`）并以 0 退出。

   若已完成步骤 4 的 PATH 配置，重新打开终端或执行 `source ~/.zshrc`（或 `~/.bashrc`）后可直接用：
   ```bash
   oj --help
   ```

1b. **验证单题提交工具**（可选项，纯标准库）：
   ```bash
   "$DST"/oj-tools/luogu-submit-helper/luogu-submit --help
   ```
   要真正可用还需接上两件事：运行 `install.sh` 软链到 `~/.local/bin`，以及在浏览器 ScriptCat 中
   导入 `userscripts/luogu-submit-helper.user.js`（只装 python 那半无法提交）。

2. **启动 Pi**：Pi 在启动时扫描项目资源。已运行的会话里执行 `/reload` 即可重新加载 prompts/skills/上下文文件，无需重启进程。

3. **确认资源已加载**：
   - 输入 `/` 应能看到 `/oj-new`、`/oj-fetch`、`/oj-status`、`/oj-run`、`/oj-sample`、`/oj-duipai`、`/oj-hint`、`/oj-brute`、`/oj-gen`、`/oj-judge`、`/oj-review`、`/oj-reference`、`/oj-help`；
   - `oj-student-coach`、`oj-cpp-rbook-style`、`rbook-http` 三个 skill 出现在可用 skill 列表中（也可用 `/skill:oj-student-coach` 强制加载）。

   顺带验证 rbook 客户端（需网络，可选）：
   ```bash
   python3 "$DST"/skills/rbook-http/scripts/rbook.py health
   ```
   应输出 `ok true` 与 pages/codes 计数；若报 `API_ROUTE_NOT_FOUND`，说明服务端 API 又变了，
   需按 `.pi/skills/rbook-http/SKILL.md` 的再同步流程更新 vendor 的 `rbook.py`。

4. **非交互自查（可用于 CI 或脚本验证）**：
   ```bash
   pi --approve --no-session -p "/oj-help" --model <任一可用模型>
   ```
   若模板与项目信任都正常，这条命令会展开 `oj-help.md` 并输出学习流程说明；
   若提示 `Unknown command` 或未展开，通常是项目未信任，加 `--approve` 或先在交互会话里 `/trust`。

## SKILL.md frontmatter 必须合法 YAML

Pi 用严格 YAML 解析器读取 `SKILL.md` frontmatter，**解析失败会直接拒绝加载该 skill（只给 warning）**。
最容易踩的坑是 description 里出现裸的“冒号+空格”（如 `workflow: restate`），它会变成一个嵌套映射并报
`Nested mappings are not allowed in compact mappings`。写成引号标量即可：

```yaml
---
name: my-skill
description: 'Use when ... workflow: restate ...'
---
```

## 关键说明

- **非破坏**：本流程只写入工具自身文件，不删除 DST 中已有的其它内容（用户自加的 prompt/skill/extension）。
- **自包含**：`oj` CLI 仅用 python3 标准库，不带任何 pip 依赖；模板文件随 `oj-tools/templates/` 一起部署。
- **路径正确性**：`AGENTS.md`、`README.md`、各 prompt/skill 文件中引用的路径形如 `.pi/oj-tools/bin/oj`，部署到 `.pi/` 后即与实际位置一致，无需改写。
- **C++ 工具链**：`oj run`/`sample`/`duipai` 会调用 `g++ -std=c++17 -O2 -pipe` 编译；若目标机器缺 g++，安装仍算成功，但上述子命令在编译阶段会失败。
- **`oj judge` 额外依赖**：走 cgroup 的完整评测需另行安装 [roj-local-judge-lite](https://github.com/rainboyOJ/roj-local-judge-lite)（仅 Linux）。
