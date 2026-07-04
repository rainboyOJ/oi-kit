# install-ai.md — 给 opencode agent 的安装手册

这份文档供 **opencode agent** 读取，说明如何把本 `opencode/` 工具包部署到一个 rbook 风格项目的 `.opencode/` 目录，使其可用。

> 只覆盖**首次安装**。不包含更新/重装/卸载流程。

## 何时使用

当你要把“OpenCode OJ Student Toolkit”安装进某个 rbook 风格项目时读取本文件并按步骤执行。装完后目标项目会获得：`/oj-*` 命令、`oj-student-coach`、`oj-cpp-rbook-style`、`rbook-http` 三个 skill、以及自包含的 `oj` 命令行工具。

## 前置条件

| 依赖 | 用途 | 检查命令 | 安装时是否必需 |
| ---- | ---- | ---- | ---- |
| opencode | 加载命令/skill/插件 | `opencode --version` | 是 |
| python3 | 运行 `oj` CLI（纯标准库，无 pip 依赖） | `python3 --version` | 是 |
| g++ | 编译 `main.cpp`/`brute.cpp`/`gen.cpp` | `g++ --version` | 否（但 `oj run`/`sample`/`duipai` 需要） |
| 网络 | opencode 启动时从 GitHub 拉取 `superpowers` 插件 | — | 是 |

## 路径约定

执行步骤前先确定两个路径：

- `SRC`：**本文件所在目录**，即 `opencode/` 源目录（包含 `AGENTS.md`、`commands/`、`skills/`、`oj-tools/` 等）。
- `DST`：目标 rbook 项目根目录下的 `.opencode/`。
  - 若部署到**包含本源目录的同一个项目**：`DST = "$SRC/../.opencode"`。
  - 若部署到**别的 rbook 项目**：`DST = "<目标项目根>/.opencode"`。

目标项目无需预先存在 `problems/` 目录；`/oj-new` 会在首次创建题目时按需生成 `problems/<oj>/<id>/`。

## 安装步骤

以下命令中先把 `SRC`、`DST` 赋值为实际绝对路径：

```bash
SRC="<本文件所在的 opencode 源目录的绝对路径>"
DST="<目标项目的 .opencode 绝对路径>"

# 1. 建立 DST 目录结构
mkdir -p "$DST"/oj-tools/bin "$DST"/oj-tools/scripts "$DST"/oj-tools/templates

# 2. 复制白名单文件（只复制工具自身拥有的文件）
cp "$SRC"/AGENTS.md   "$DST"/
cp "$SRC"/README.md   "$DST"/
cp -r "$SRC"/commands "$DST"/
cp -r "$SRC"/skills   "$DST"/
cp "$SRC"/oj-tools/bin/oj          "$DST"/oj-tools/bin/
cp "$SRC"/oj-tools/scripts/oj_cli.py "$DST"/oj-tools/scripts/
cp "$SRC"/oj-tools/templates/*     "$DST"/oj-tools/templates/

# 3. 让 oj 可执行
chmod +x "$DST"/oj-tools/bin/oj

# 4. 将 oj 加入 PATH（之后可以在任何目录直接运行 oj）
#    避免重复添加
line="export PATH=\"$DST/oj-tools/bin:\$PATH\""
for rc in ~/.zshrc ~/.bashrc; do
  grep -qxF "$line" "$rc" 2>/dev/null || echo "$line" >> "$rc"
done

# 5. 安装 rbook-http skill（可选，但推荐）
#    该 skill 位于目标 rbook 项目的 .agents/skills/rbook-http/，需单独复制
#    DST 的父目录即目标项目根
PROJECT_ROOT="$(dirname "$DST")"
if [ -d "$PROJECT_ROOT/.agents/skills/rbook-http" ]; then
  cp -r "$PROJECT_ROOT/.agents/skills/rbook-http" "$DST/skills/"
fi
```

**不要复制**以下文件（它们是开发产物或本手册本身）：

```text
install-ai.md          # 本手册，仅留在源端
node_modules/          # npm 产物
package.json           # 本地插件开发产物
package-lock.json      # 同上
bun.lock               # 同上
.gitignore             # 源端 git 忽略规则
oj-tools/.build/       # 构建缓存
**/__pycache__/        # python 字节码缓存
```

`cp -r` 对已存在的同名子目录会做合并（覆盖同名文件、保留其它文件），因此 DST 中已有的非工具文件（如 `goals/`、用户自加的 agent/skill/command）不会被删除。

## 处理 opencode.json

源端 `opencode.json` 内容很小，只声明了 superpowers 插件：

```json
{
  "$schema": "https://opencode.ai/config.json",
  "plugin": ["superpowers@git+https://github.com/obra/superpowers.git"]
}
```

按目标现状二选一：

- **`DST/opencode.json` 不存在**：直接复制。
  ```bash
  cp "$SRC"/opencode.json "$DST"/
  ```
- **`DST/opencode.json` 已存在**：**合并，不要整体覆盖**。保留目标已有的所有字段（`provider`、`model`、`permission`、`command` 等），只确保 `plugin` 数组里包含 `"superpowers@git+https://github.com/obra/superpowers.git"`；若该条已存在则不改。

合并示例（`DST` 已在前文赋值；通过环境变量传给 python，避免 heredoc 转义问题）：

```bash
DST="$DST" python3 - <<'PY'
import json, os, pathlib
p = pathlib.Path(os.environ["DST"]) / "opencode.json"
cfg = json.loads(p.read_text(encoding="utf-8"))
plug = cfg.setdefault("plugin", [])
entry = "superpowers@git+https://github.com/obra/superpowers.git"
if entry not in plug:
    plug.append(entry)
p.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY
```

> superpowers 插件由 opencode 在启动时自动拉取并安装到其全局缓存（`~/.cache/opencode/packages/`），**无需手动 `npm install` 或 `bun install`**，也无需在 DST 里保留 `package.json`/`node_modules`。

## 验证

1. **验证 `oj` CLI 可用**（纯本地，不依赖网络）：
   ```bash
   "$DST"/oj-tools/bin/oj --help
   ```
   应打印子命令列表（`new`/`fetch`/`status`/`run`/`sample`/`duipai`/`gen`）并以 0 退出。

   若已完成步骤 4 的 PATH 配置，重新打开终端或执行 `source ~/.zshrc`（或 `~/.bashrc`）后可直接用：
   ```bash
   oj --help
   ```

2. **重启 opencode**：opencode 在启动时一次性加载配置，不热重载。安装完成后需退出并重新启动 opencode，它才会：
   - 发现新的 `.opencode/`（命令、skill、`AGENTS.md`）；
   - 自动拉取并加载 `superpowers` 插件。

3. **重启后确认**：
   - `/oj-new`、`/oj-fetch`、`/oj-status`、`/oj-run`、`/oj-sample`、`/oj-duipai`、`/oj-hint`、`/oj-brute`、`/oj-gen`、`/oj-review`、`/oj-reference`、`/oj-help` 等命令可用；
   - `oj-student-coach`、`oj-cpp-rbook-style`、`rbook-http` 三个 skill 被识别。

## 关键说明

- **非破坏**：本流程只写入工具自身文件，不删除 DST 中已有的其它内容（如 `goals/` 会话状态、用户自加的 agent/skill）。
- **自包含**：`oj` CLI 仅用 python3 标准库，不带任何 pip 依赖；模板文件随 `oj-tools/templates/` 一起部署。
- **路径正确性**：`AGENTS.md`、`README.md`、各命令文件中引用的路径形如 `.opencode/oj-tools/bin/oj`，部署到 `.opencode/` 后即与实际位置一致，无需改写。
- **C++ 工具链**：`oj run`/`sample`/`duipai` 会调用 `g++ -std=c++17 -O2 -pipe` 编译；若目标机器缺 g++，安装仍算成功，但上述子命令在编译阶段会失败。
