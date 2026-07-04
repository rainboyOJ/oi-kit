Provide a final reference solution only after the learning steps are complete.

Arguments: `$ARGUMENTS`

Use this command only when the student has already tried the problem.

Before giving a complete solution, state the expected prerequisites:

- the student has read and restated the problem;
- a brute-force idea exists;
- the bottleneck has been discussed;
- the optimized idea has been attempted or the student is intentionally entering reference stage.

Then provide:

1. concise idea;
2. why it is correct;
3. key implementation details;
4. C++17 code in `oj-cpp-rbook-style`;
5. suggested sample check and duipai command.

Make clear that this is a reference, not a replacement for the student's own attempt.

## 复盘：知识点归纳与 rbook 关联

代码给出之后，必须追加复盘阶段，把本题用到的知识点匹配到 rbook 章节，填入题目目录下的 `index.md`。使用 `rbook-http` skill 完成本步。

### 前置校验（必须通过才进入复盘）

复盘不得在 `main.cpp` 未经样例验证时进行，否则复盘会基于未验证的代码"吹"知识点，水分大、误导学生。流程开始前先执行：

```bash
.opencode/oj-tools/bin/oj status <problem_dir>
.opencode/oj-tools/bin/oj sample <problem_dir>
```

判定规则：

- `problem.md` 或 `main.cpp` 缺失：不进入复盘，提示学生先抓题/写代码。
- `oj sample` 任意样例失败：不进入复盘，明确告知哪条样例失败、要求学生先修复 `main.cpp` 通过样例（可选 `oj duipai` 进一步对拍）。
- 有 `brute.cpp` 和 `gen.cpp` 且学生希望严格验证：建议先 `oj duipai 100`，出现反例则不进入复盘，先修代码。

只有样例全部通过（且若跑了 duipai 则对拍无反例）后，才继续下面的复盘流程。跳过复盘时给学生的提示应为：

```text
复盘暂未进行：main.cpp 尚未通过样例/对拍。
请先修复并运行 oj sample（与 oj duipai）通过后，再重新触发 /oj-reference 完成复盘。
```

### 复盘流程

1. 读取 `problem.md` 与已完成的 `main.cpp`，提取本题用到的知识点列表（如 `["数位DP", "记忆化搜索"]`）。
2. 调用 `python skills/rbook-http/scripts/rbook_catalog.py --scope visible --compact --pretty` 拿到 rbook 目录。
3. 对每个知识点，在目录的 `title` / `excerpt` / `headings` / `tags` 中匹配最相关的一篇文章。命中则记录其 `citation.title` 和 `citation.url`。
4. 若 catalog 未命中该知识点，降级调用 `python skills/rbook-http/scripts/rbook_search.py "<知识点>" --limit 5 --no-text --pretty`，从片段搜索结果里选 top-1 章节，取其 `path`/`title`。
5. 缺省 `BASE_URL` 是线上 `https://rbook2.roj.ac.cn`，无需额外配置即可使用；按 skill 文档验证健康状态后再继续。
6. 每个知识点只取 top-1 篇，不贴模板代码正文。
7. 更新 `index.md`：
   - frontmatter：`tags` 填知识点名称，`rbook` 填数组，每项形如 `{tag: <知识点>, title: <文章标题>, url: <文章相对 url>}`。
   - 正文 `### 知识点` 小节：逐个知识点写一两句思想，并以 `[<文章标题>](<BASE_URL + url>)` 形式给出可点击引用。
8. 如 rbook 中确无对应章节，如实在该条知识点下注明"rbook 暂无对应章节"，不强行硬凑。

复盘是学习闭环的最后一环，必须真实反映 rbook 覆盖范围。
