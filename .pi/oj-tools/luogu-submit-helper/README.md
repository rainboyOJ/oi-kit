# luogu-submit：洛谷单题提交助手

在终端选中本地源码，让浏览器自动填入洛谷提交页并点一次提交按钮。

本目录是独立可用的最小发行版：**只含单题提交**，不依赖 oi-kit 的任何其他部分，
可以单独拷走使用。它读你自己指定的题库目录，不要求是 rbook 项目。

```text
luogu-submit-helper/
├── luogu-submit                    # 命令本体（Python 3，纯标准库）
├── install.sh                      # 软链到 ~/.local/bin/luogu-submit
├── userscripts/
│   └── luogu-submit-helper.user.js # 浏览器侧 ScriptCat 脚本
└── tests/                          # 上游测试，可选
```

---

## 一、工作原理（先看懂这个，再动手）

```text
luogu-submit P1001
   │
   ├─ 读配置找到题库目录 problems/luogu/1001/
   ├─ 列出可提交源码，你选一个
   ├─ 终端再确认一次（按 Enter）
   ├─ 在本机 127.0.0.1 的随机端口起一个一次性 HTTP 服务，生成一次性 token
   └─ 打开 https://www.luogu.com.cn/problem/P1001?luogu-submit-port=<端口>&luogu-submit-token=<token>
         │
         └─ ScriptCat 里的 userscript 校验 token
              ├─ 拉取源码（GET /task，只能领一次）
              ├─ 切语言 → 填代码 → 回读校验
              ├─ 点一次提交按钮
              └─ 回报结果（POST /result）→ 终端打印"已点击提交按钮"
```

**关键点：命令本身不会提交任何东西。** 真正点按钮的是浏览器里的 userscript。
所以「只装 Python 那半」一定失败 —— 终端会等 120 秒然后超时。

安全性设计：服务只监听 `127.0.0.1`、端口随机、token 随机且只对一次任务有效、
任务只能被领取一次、普通浏览洛谷题目页时脚本完全不激活（没带任务参数就直接返回）。

---

## 二、前置条件

| 依赖 | 用途 | 必需 |
| --- | --- | --- |
| Python 3 | 跑 `luogu-submit`（无 pip 依赖） | 是 |
| ScriptCat（或 Tampermonkey）浏览器扩展 | 加载 userscript，真正执行提交 | 是 |
| 浏览器已登录洛谷 | 未登录时找不到语言选择/提交按钮，脚本会拒绝点击 | 是 |
| `node` | 只有跑 userscript 测试时需要 | 否 |
| Playwright + Chromium | 只有跑浏览器测试时需要 | 否 |

检查：

```bash
python3 --version    # 语法上兼容 3.8+，只用标准库无 pip 依赖（本项目仅在 3.14 实测）
node --check userscripts/luogu-submit-helper.user.js   # 语法自检，可选
```

---

## 三、安装

### 方式 A：从本目录直接安装（推荐，最常见）

```bash
cd .pi/oj-tools/luogu-submit-helper
./install.sh
```

`install.sh` 做的事：把 `luogu-submit` 软链到 `~/.local/bin/luogu-submit`。
反复执行安全（覆盖软链）；若 `~/.local/bin/luogu-submit` 是个**真实文件**而非软链，
脚本会报错退出、不覆盖。

### 方式 B：拷到一个独立目录再用

想把提交工具和 oi-kit 完全分离（例如装到另一台机器、或单独备份）：

```bash
mkdir -p ~/mycode/luogu-submit-helper
cp -r luogu-submit install.sh userscripts ~/mycode/luogu-submit-helper/
chmod +x ~/mycode/luogu-submit-helper/luogu-submit ~/mycode/luogu-submit-helper/install.sh
~/mycode/luogu-submit-helper/install.sh
```

只需要这三个条目；`tests/` 和 `README.md` 不必带。

### 方式 C：不装，直接跑

```bash
python3 /path/to/luogu-submit-helper/luogu-submit 1001
```

不建软链也能用，只是每次要写全路径。下面文档里的 `luogu-submit` 都替换成这条命令即可。

### 确保 `~/.local/bin` 在 PATH 里

`install.sh` 检测到没配会打印提示。手动加：

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc   # zsh 用 ~/.zshrc
source ~/.bashrc
command -v luogu-submit
```

验证安装：

```bash
luogu-submit --help
```

应打印用法并退出 0。

---

## 四、装浏览器 userscript（必做，最容易漏）

1. 浏览器安装 **ScriptCat**（推荐，本脚本按 ScriptCat 编写）或 Tampermonkey。
2. 打开扩展的脚本管理界面 → 新建/导入脚本 → 粘贴
   `userscripts/luogu-submit-helper.user.js` 全文 → 保存并**启用**。
3. 确认脚本的 `@match` 覆盖 `https://www.luogu.com.cn/problem/*`，
   且 `@grant GM_xmlhttpRequest` 与 `@connect 127.0.0.1` 未被扩展拦掉
   （ScriptCat 首次连接本地地址可能弹权限确认，选允许）。
4. 打开任意洛谷题目页，确认脚本没有报错。注意：**直接打开题目页不会做任何事**，
   只有 URL 带 `luogu-submit-port` / `luogu-submit-token` 参数时才工作。

---

## 五、首次配置题库目录

命令需要一个包含 `luogu/` 子目录的**题库根目录**：

```text
<题库根>/luogu/<题目目录>/main.cpp
<题库根>/luogu/<题目目录>/main.py
...
```

配置一次即可，写入
`${XDG_CONFIG_HOME:-~/.config}/luogu-submit-helper/config.json`：

```bash
luogu-submit config /path/to/problems
```

同时追加源码黑名单（默认已排除 `gen.py`、`gen.cpp`）：

```bash
luogu-submit config /path/to/problems --blacklist brute.cpp debug.py
```

约束：

- 传进去的路径必须**已存在**且**含 `luogu/` 子目录**，否则报错
  `题库根目录中没有 luogu/ 子目录`。
- 黑名单按**题目目录直属文件名**精确匹配，不支持路径与通配符；默认项
  `gen.py`/`gen.cpp` 永远生效，`--blacklist` 只能追加不能取消。
- 配置文件用原子写入（临时文件 + `os.replace`），中途中断不会写坏。

查看当前配置：

```bash
cat ~/.config/luogu-submit-helper/config.json
```

---

## 六、提交一题

### 指定题号

```bash
luogu-submit 1001      # 纯数字
luogu-submit P1001     # 带 P
luogu-submit B2002     # 其他前缀
```

### 或先 cd 进题目目录，不传题号

```bash
cd /path/to/problems/luogu/1001
luogu-submit
```

此时当前目录必须正好是已配置题库下的 `luogu/<题目目录>`，否则报错。

### 交互流程

```text
可提交的源码:
  1. main.cpp  [C++20]
  2. main.py   [Python 3]
选择源码编号 [1]，输入 q 取消:        ← 直接 Enter 选 1，输入 q 放弃

即将真实提交:
  题号: P1001
  源码: /path/to/problems/luogu/1001/main.cpp
  语言: C++20
按 Enter 确认，输入任意内容取消:      ← 这一步是最后一道闸

已打开 P1001 提交页，等待 ScriptCat userscript...
已点击提交按钮: 提交按钮已点击
```

**「已点击提交按钮」只代表点击动作完成，不代表 AC。** 结果一律以洛谷提交记录为准。

### 题号 → 本地目录的查找顺序

依次尝试，取第一个存在的目录：

| 题号 | 优先 | 其次 | 再次 |
| --- | --- | --- | --- |
| `1001` / `P1001` | `luogu/1001/` | `luogu/P1001/` | `luogu/p1001/` |
| `B2002` | `luogu/b2002/` | `luogu/B2002/` | —— |

所以纯数字命名（`luogu/1001`）和 rbook 风格（`luogu/P1001`、`luogu/p1001`）都能直接用。

### 源码扫描规则

- 只扫**题目目录直属**文件，**不递归**子目录（`problem-analysis-workspace/`、
  `duipai-failed/` 之类不会干扰）。
- 支持扩展名 → 洛谷语言：

  | 扩展名 | 洛谷语言 |
  | --- | --- |
  | `.cpp` | C++20 |
  | `.py` | Python 3 |
  | `.c` | C |
  | `.java` | Java |
  | `.js` | JavaScript |
  | `.rs` | Rust |
  | `.hs` | Haskell |

- 黑名单文件先剔除，剩下的 `main.*` 排最前，其余按文件名排序。
- 源码以 **UTF-8** 读取；读不了会直接报错（不会静默按其他编码猜）。

---

## 七、故障排查

| 现象 | 原因与处理 |
| --- | --- |
| 终端等 **120 秒后超时** | 最常见：ScriptCat 里没导入/没启用脚本；或浏览器没打开带任务参数的页面。终端会打印完整 URL，可手动打开 |
| `尚未配置题库目录` | 没跑过 `luogu-submit config /path/to/problems` |
| `题库根目录中没有 luogu/ 子目录` | 传成了项目根目录，应传**包含 `luogu/` 的那一层**（通常是 `problems/`） |
| `题目目录不存在: P1001，已尝试: ...` | 目录名与题号不匹配；看错误里列出的候选路径，按上面的查找顺序建目录 |
| `题目目录中没有支持的源码文件` | 目录里只有 `gen.cpp`（被黑名单排除）或不支持的扩展名 |
| userscript 报「找不到/不唯一」语言、编辑器或提交按钮 | 通常是**未登录洛谷**、遇到验证码，或洛谷页面结构改版。脚本在这种情况下**不会**点击提交 |
| `自动打开浏览器失败` | 无图形界面的终端/SSH 场景。手动复制终端打印的 URL 到浏览器打开 |
| 端口/连接被拒 | 本地服务只活到这次任务结束；不要关闭终端或用 Ctrl-C 打断后再操作浏览器 |

补充：`luogu-submit` 退出码 —— `0` 成功（含主动取消），`1` 运行失败（超时/自动提交失败），
`2` 配置或参数错误，`130` 被 Ctrl-C 中断。

---

## 八、卸载

```bash
rm ~/.local/bin/luogu-submit                        # 只是软链
rm -rf ~/.config/luogu-submit-helper                # 配置
# 再到浏览器扩展里删除该 userscript
```

源码目录想删就删，命令本身没有在系统里留其他东西。

---

## 九、跑测试（可选，开发用）

```bash
cd /path/to/luogu-submit-helper
python3 -m unittest discover -s tests       # 22 tests OK；缺 Chromium 时浏览器用例自动 skip
node --check userscripts/luogu-submit-helper.user.js
bash -n install.sh
```

测试**不访问洛谷、不提交代码、不打开你的默认浏览器**；userscript 测试用本地无头
Chromium 加载模拟页面。

---

## 十、说明：本目录与上游的关系

本目录是从上游 `luogo-submit-helper` 仓库**裁剪提取**的单题提交部分，改动只有一处：

> 上游 `luogu-submit` 通过 `from submit_problem_sets import LUOGU_BASE_URL, luogu_dir_id, luogu_real_id`
> 取三个小工具函数；本目录不带题单批量提交脚本，因此这三个函数已**内联**在 `luogu-submit`
> 开头。从上游同步新版时，覆盖文件后**不要丢掉这段内联**，否则会 `ImportError`。

上游有、本目录**没有**的部分：

- `submit_problem_sets.py`：Markdown 题单 + 剪贴板 + 手动提交（低风险，但仍需人手点）
- `submit_problem_sets_auto.py`：Playwright 自动填码/提交（较高风险，需 `playwright` + Chromium）

想要题单批量提交，用上游仓库即可；两边可以共存，只是命令不同。
