---
name: rbook-http
description: 使用 rbook 动态算法电子书的只读 HTTP API 检索、读取文章、获取代码模板和整理解题上下文。用户询问本算法电子书内容、需要定位文章、需要根据文章和模板代码写 OJ 题解或 C++ 代码、需要通过 HTTP 读取 rbook 内容时，应优先使用本技能。
---

# rbook HTTP 使用指南

本项目把算法电子书暴露为只读 HTTP API。这个服务只负责提供文章、目录、搜索结果和模板代码；它不提供对话功能，也不在网站中嵌入 AI。

使用本技能时，把 rbook 当作一个“可通过 HTTP 查询的知识库”。本地智能体读取这个技能后，应通过 HTTP API 获取上下文，再根据获取到的文章和代码模板回答用户问题或生成 OJ 解题内容。

## 基础配置

优先使用环境变量 `RBOOK_BASE_URL`：

```bash
BASE_URL="${RBOOK_BASE_URL:-https://rbook2.roj.ac.cn}"
```

本项目约定默认使用线上服务，开箱即用。本地有 rbook 服务时设 `RBOOK_BASE_URL=http://127.0.0.1:3000` 覆盖，或在脚本里传 `--local`。

使用 API 前先检查健康状态：

```bash
curl "$BASE_URL/api/health"
```

如果健康检查失败，不要继续臆测文章内容；应报告服务不可用，或按用户要求切换到线上地址再试。

## 推荐工具

本 skill 带有一组 Python 脚本，位于 `scripts/` 目录。优先使用这些脚本访问 API；它们会自动处理中文 URL 编码、JSON 解析、错误输出和常用字段裁剪。脚本不可用时，再按后文 curl 示例直接请求 API。

所有脚本默认读取 `RBOOK_BASE_URL`，未设置时使用线上地址 `https://rbook2.roj.ac.cn`。若需访问本地服务，传 `--local` 或设置环境变量 `RBOOK_BASE_URL=http://127.0.0.1:3000`。

### 健康检查

```bash
python skills/rbook-http/scripts/rbook_health.py --online --pretty
```

### 获取 AI 目录

```bash
python skills/rbook-http/scripts/rbook_catalog.py --scope visible --compact --pretty
```

常用参数：

- `--scope visible|all`：默认只取首页可见文章。
- `--compact`：只输出 agent 常用字段。
- `--limit N`：限制输出文章数量。

### 片段搜索

```bash
python skills/rbook-http/scripts/rbook_search.py "数位DP 状态 记忆化" --limit 8 --pretty
```

常用参数：

- `--text-length N`：控制每条片段正文长度。
- `--no-text`：只返回标题、路径、分数等元数据。
- `--raw`：输出 API 原始响应。

### 读取文章上下文

```bash
python skills/rbook-http/scripts/rbook_page_context.py graph/bcc/index.md --include-code --compact --pretty
```

常用参数：

- `--include-code`：同时返回模板代码正文。
- `--include-html`：包含渲染 HTML，只有用户需要 HTML 时使用。
- `--compact`：只保留文章、引用和代码相关常用字段。

### 读取模板代码

```bash
python skills/rbook-http/scripts/rbook_code.py /code/graph/v-bcc.cpp --content-only
```

常用参数：

- `--content-only`：只输出代码正文，适合直接作为代码生成参考。

## 总体工作流

1. 如果不知道精确文章路径，先搜索。
2. 回答算法概念或教程问题时，优先使用片段搜索，因为它返回更聚焦的上下文。
3. 找到最相关页面后，再获取完整页面或 AI 页面上下文。
4. 推理和写解释时优先使用 `markdown` 或 `text`，只有用户需要渲染结果时才使用 `html`。
5. 不调用 admin 接口。
6. 不调用 problem 相关能力；题目服务已经拆分到独立项目，本项目 API 不负责题目数据。
7. 对中文查询使用 `curl -G --data-urlencode`，避免 URL 编码问题。

字段契约的项目内文档在 `docs/development/ai-api-schema.md`。当文档和实际响应不一致时，以实际 API 响应和契约测试为准。

## 常用场景

### 回答电子书里的知识点

当用户问“这个电子书里有没有某个算法”“某个知识点在哪里”“解释一下某篇文章内容”时：

1. 用 `/api/chunks/search` 搜索关键词。
2. 根据结果中的 `path`、`title`、`heading` 选择相关页面。
3. 用 `/api/page?path=...` 或 `/api/ai/page-context?path=...` 读取完整上下文。
4. 回答时说明信息来自哪篇文章；需要可点击引用时用 `BASE_URL + url` 拼接。

示例：

```bash
curl -G \
  --data-urlencode "q=数位DP 状态 记忆化" \
  --data-urlencode "limit=8" \
  --data-urlencode "textLength=900" \
  "$BASE_URL/api/chunks/search"
```

### 根据 rbook 风格完成 OJ 题解和代码

当用户希望根据本项目文章和模板代码完成 OJ 题目、生成题解、保持代码风格时，优先使用 AI 专用接口：

1. 调用 `/api/ai/catalog` 获取正式文章目录、文章引用链接和 `code_template` 元数据。
2. 根据题目关键词、算法模型、模板标签选择相关文章。
3. 调用 `/api/ai/page-context?path=<article>&includeCode=true` 获取完整文章、引用信息、模板代码和正文 `@include-code` 代码。
4. 如果只需要某份模板代码，调用 `/api/ai/code?path=/code/...`。
5. 写 C++ 代码时优先模仿 `codeTemplates[].content` 的结构、变量命名、注释密度和竞赛风格。
6. 写题解时说明使用了哪些本项目文章，并使用 `BASE_URL + citation.url` 生成可点击引用。
7. 不使用本 API 查询题目数据。

题解引用格式示例：

```md
本文使用了本项目中的 [点双连通分量](https://rbook2.roj.ac.cn/graph/bcc/index.html) 文章内容。
```

## API 端点

### 健康检查

```bash
GET /api/health
```

返回服务状态、索引生成时间和页面/片段统计。成功响应中应包含：

- `ok`
- `generatedAt`
- `stats.pages`
- `stats.chunks`
- `stats.errors`

### 站点信息

```bash
GET /api/site
```

返回电子书站点元信息、统计信息和索引生成时间。

### 目录树

```bash
GET /api/toc
GET /api/nav
```

返回章节目录树。用户问某个主题在电子书哪里时使用这个接口。

### 页面列表

```bash
GET /api/pages
GET /api/pages?visible=true
```

返回页面元数据列表。只需要首页目录中可见文章时使用 `visible=true`。

### 页面详情

```bash
GET /api/page?path=dynamic_programming/数位DP/index.md
```

返回页面元数据和完整内容，包括：

- `frontMatter`
- `markdown`
- `text`
- `html`
- `headings`
- `chunks`

使用建议：

- 写结构化解释时使用 `markdown`。
- 只需要压缩上下文时使用 `text`。
- 用户明确需要页面渲染结果时才使用 `html`。

中文路径建议用 URL 编码：

```bash
curl -G \
  --data-urlencode "path=dynamic_programming/数位DP/index.md" \
  "$BASE_URL/api/page"
```

### 页面级搜索

```bash
GET /api/search?q=数位DP&limit=5
```

返回页面级搜索结果和摘要，适合先定位相关页面。

推荐写法：

```bash
curl -G \
  --data-urlencode "q=数位DP" \
  --data-urlencode "limit=5" \
  "$BASE_URL/api/search"
```

### 片段搜索

```bash
GET /api/chunks/search?q=数位DP 状态 记忆化&limit=8&textLength=900
```

返回更聚焦的段落上下文。回答具体算法问题时默认优先使用这个接口。

参数说明：

- `q`：必填，搜索词。
- `limit`：可选，返回条数。
- `textLength`：可选，每个结果的文本长度。
- `includeText`：可选，设为 `false` 时不返回完整文本。

推荐写法：

```bash
curl -G \
  --data-urlencode "q=数位DP 状态 记忆化" \
  --data-urlencode "limit=8" \
  --data-urlencode "textLength=900" \
  "$BASE_URL/api/chunks/search"
```

### AI 文章目录

```bash
GET /api/ai/catalog
GET /api/ai/catalog?scope=visible
GET /api/ai/catalog?scope=all
```

返回适合智能体使用的文章目录。默认 `scope=visible`，只返回首页目录中可见的正式文章；只有需要内部文章或隐藏页面时才使用 `scope=all`。

每篇文章通常包含：

- `path`
- `url`
- `title`
- `description`
- `excerpt`
- `tags`
- `categories`
- `headings`
- `navTrail`
- `visible`
- `source`
- `codeTemplates`
- `citation`

其中 `citation` 只包含 `title`、`path`、`url`，没有 `href`。`codeTemplates[]` 中的模板代码链接字段是 `codeUrl`，它也是相对路径。

选择 OJ 解题参考文章和代码模板时，先调用这个接口。

### AI 页面上下文

```bash
GET /api/ai/page-context?path=graph/bcc/index.md
GET /api/ai/page-context?path=graph/bcc/index.md&includeCode=true
GET /api/ai/page-context?path=graph/bcc/index.md&includeCode=true&includeHtml=true
```

返回单篇文章的完整智能体上下文，包括：

- `article.markdown`
- `article.text`
- `article.headings`
- `article.frontMatter`
- `article.citation`
- `codeTemplates`
- `includedCode`

参数说明：

- `path`：必填，文章 Markdown 路径。
- `includeCode=true`：可选，返回模板代码正文；当代码风格或模板内容重要时使用。
- `includeHtml=true`：可选，返回渲染 HTML；只有用户需要 HTML 时使用。

`codeTemplates` 来自文章头部元数据里的 `code_template`，生成 OJ 代码时优先参考它。`includedCode` 来自正文 `@include-code(...)`，常用于解释性代码片段。

注意：AI 专用接口只返回相对路径，不返回 `href`、`codeHref` 这类绝对链接。需要可点击链接时，由调用方用当前 `BASE_URL` 拼接 `url` 或 `codeUrl`。

字段约定：

- `article.url` 和 `article.citation.url` 是文章页面相对链接。
- `codeTemplates[].code` 和 `codeTemplates[].codeUrl` 都指向 `/code/...` 模板代码。
- `includedCode[].codeUrl` 可能是 `null`；只有正文使用 `/code/...` 时才有可拼接链接。
- `includeCode=true` 时，`codeTemplates[]` 和 `includedCode[]` 才包含 `content`。

推荐写法：

```bash
curl -G \
  --data-urlencode "path=graph/bcc/index.md" \
  --data-urlencode "includeCode=true" \
  "$BASE_URL/api/ai/page-context"
```

### AI 代码模板

```bash
GET /api/ai/code?path=/code/graph/v-bcc.cpp
```

返回单个代码模板：

- `path`
- `url`
- `language`
- `content`

这个接口只读取电子书 `book/code/` 目录下的文件。不要传任意系统文件路径，也不要尝试 `../`。

推荐写法：

```bash
curl -G \
  --data-urlencode "path=/code/graph/v-bcc.cpp" \
  "$BASE_URL/api/ai/code"
```

## 回答规范

回答电子书相关问题时：

- 尽量给出文章标题、路径或链接，方便用户继续阅读。
- 使用 API 返回的内容作为事实依据，不要编造电子书中不存在的内容。
- 如果结果来自片段搜索，说明它是搜索到的片段；如果结果来自完整页面，按文章结构回答。
- 写 OJ 题解时，说明使用了哪些 rbook 文章或模板代码。
- 写 C++ 代码时，优先参考 `codeTemplates[].content` 的风格。
- 需要引用链接时，用当前 `BASE_URL` 拼接 `article.url` 或 `citation.url`。
- 如果 API 没找到相关内容，应如实说明没有在 rbook 中找到，而不是硬凑答案。

## 禁止事项

- 不调用 `/api/admin/*`，除非用户明确要求维护服务并提供授权上下文。
- 不把本 API 当作题目库查询接口。
- 不调用或假设存在站内对话、AI 对话、题目查询等接口。
- 不使用任意文件路径读取代码；`/api/ai/code` 只接受 `/code/...`。
- 不把搜索结果当作最终事实；重要回答应进一步读取完整文章或页面上下文。
