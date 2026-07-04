# TODO

1. ~~**复盘前置校验**：复盘应在 `main.cpp` 通过 `sample`/`duipai` 后才跑。当前 `oj-reference` 可在 `main.cpp` 未验证时就给代码+复盘，水分大。复盘步骤前先 `oj status`/`oj sample` 校验，未通过则跳过或提示先验证。~~ ✅ 已完成（`oj-reference.md` / `oj-student-coach` SKILL.md / `AGENTS.md` 均补述前置校验）

2. **catalog 输出过大**：`--compact` 一次 6000+ 行 JSON，每题复盘都拉远程耗 token。可加 `rbook_match.py "<知识点>"` 工具：内部拉 catalog + 模糊打分，只返回每知识点 top-1 `{tag,title,url}`；或加本地 `.opencode/oj-tools/.cache/rbook-catalog-<date>.json` 缓存。

3. **知识点缺校验**：AI 容易把"DFS"也塞进去但其实 rbook 没该专文、或写"状压"却没真用到。建议约束：每个知识点必须附一句"本题哪里用到该知识点"。

4. **复盘埋在 `/oj-reference` 末尾的灵活性差**：实操能跑，但学生自己写了正解、只想要复盘+rbook关联时没有命令可走（reference 会先重给代码）。考虑加轻量 `/oj-recap`，只跑复盘不动 `main.cpp`。

5. **`oj new` 参数歧义**：`oj new luogu/P1036` 会解析成 problem_id="luogu/P1036"，造成 `problems/luogu/luogu/p1036` 双层目录。建议 `parse_problem_target` 支持 `/` 分隔，或文档明确报错。

6. **md 链接写死 BASE_URL**：复盘 md 用 `https://rbook2.roj.ac.cn/...` 固化链接，学生之后切本地 rbook 不会自动跟随。可只放相对 url 进 frontmatter `rbook`，正文引用走 Obsidian rbook 跳转；或接受"始终线上"约定。

7. **`tags` 复用作知识点丢失主题维度**：复盘把 tags 填成"组合枚举""素数判定"等细粒度术语，跨题聚合"做过哪些数论题"会偏细。可考虑新增 `knowledge:` 字段单独存知识点，`tags` 留作上层主题。