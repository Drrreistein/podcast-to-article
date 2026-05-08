# podcast-to-article

将播客访谈、YouTube/B站 视频字幕转换为结构清晰、阅读友好的长文 HTML。

## 功能特性

- 📖 **像读书一样阅读**：按主题/章节重组，告别流水账
- 🔗 **支持视频链接**：直接输入 YouTube/B站 链接，自动提取字幕
- ✂️ **自适应分块**：30分钟到4-5小时，统一处理
- 💾 **信息完整**：保留所有重要细节、引用、数据
- 🎨 **kami 风格**：羊皮纸质感、专业排版
- 📁 **会话隔离**：每次运行独立文件夹，所有中间文件可追溯

## 工作流程

```
视频链接 或 本地Markdown文件
    ↓
创建会话文件夹 (outputs/{ID}_{时间戳}/)
    ↓ [run.py]
00_transcript.md     — 原始字幕
    ↓ [parse_transcript.py]
01_parsed.json       — 结构化数据（说话人、时间线、段落）
    ↓ [chunk_text.py]
02_chunked.json      — 分块文本
    ↓ [AI + 02-summarize.md]
03_batch_*.json      — 各块摘要
    ↓ [AI + 03-cluster.md]
04_chapters.json     — 章节规划
    ↓ [AI + 04-compose.md]
05_article_data.json — 最终文章数据
    ↓ [build_html.py]
06_final.html        — kami 风格长文
```

## 使用方法

### 方式一：视频链接（推荐）

```bash
python3 scripts/run.py --url "https://www.youtube.com/watch?v=xxx"
```

### 方式二：本地字幕文件

```bash
python3 scripts/run.py "path/to/字幕.md"
```

### 方式三：分步执行（手动模式）

```bash
python3 scripts/run.py --url "..."
# AI 处理中间步骤（见下方）
python3 scripts/build_html.py <article_data.json> <template.html> <output.html>
```

## 输入格式

**视频平台**：YouTube、B站 等公开视频链接

**本地 Markdown 格式**：

```markdown
---
title: "访谈标题"
source: "https://..."
published: 2026-05-07
---

## Transcript

**0:02** · 说话内容...
**1:30** · 另一段说话内容...
```

或带章节索引的格式：

```markdown
00:00 Introduction
00:44 主题一
02:28 主题二

## Transcript

**0:02** · 内容...
```

## 输出结构

每次运行生成独立的会话文件夹（保存到 Obsidian Vault）：

```
/Users/a1-6/Documents/Obsidian Vault/kb/outputs/podcast/
└── {视频ID或文件名}_{YYYYMMDD_HHMMSS}/
    │
    ├── metadata.json           # 会话元信息（来源、块数、文件清单）
    ├── 00_ai_prompt.txt       # AI 处理提示（可直接复制）
    │
    ├── 00_transcript.md       # 原始字幕（从 URL 提取或本地复制）
    ├── 01_parsed.json         # 结构化解析
    ├── 02_chunked.json        # 分块数据
    │
    ├── 03_batch_1.json        # AI 摘要（每批5块）
    ├── 03_batch_2.json        # AI 摘要批次2
    ├── 03_batch_3.json        # AI 摘要批次3（如有）
    │   ...
    │
    ├── 04_chapters.json       # 章节规划
    ├── 05_article_data.json   # 最终文章数据
    └── 06_final.html          # kami 风格长文（最终输出）
```

> **文件命名规则**：带序号前缀（00/01/02...），按处理顺序排列，方便追踪。

## AI 处理流程

### Step 0: URL 字幕提取

`run.py` 自动使用 defuddle.md 提取字幕，保存到 `00_transcript.md`。

### Step 1: 解析与实体提取

加载 `prompts/01-parse.md`，提取：
- 标题、嘉宾信息、主持人
- 来源平台、日期、时长
- 主要话题列表、导读内容

### Step 2: 分段摘要（关键步骤）

对每个文本块加载 `prompts/02-summarize.md`，**完整保留所有信息**：
- 所有核心论点（不限制数量）
- 所有重要引用、具体案例和数据
- 目标：摘要覆盖 90%+ 原文信息

### Step 3: 章节规划

加载 `prompts/03-cluster.md`，规划：
- 章节结构（根据内容长度调整章节数量）
- 每章的内容方向、需要保留的引用

### Step 4: 最终文章生成

加载 `prompts/04-compose.md`，生成：
- 完整文章内容（JSON 格式）
- 章节正文（800-1500字/章）
- 全文目标 8000-15000字

### Step 5: HTML 生成

```bash
python3 scripts/build_html.py \
    {session_dir}/05_article_data.json \
    assets/template.html \
    {session_dir}/06_final.html
```

## 手动模式

如果 AI 处理需要调整，可手动编辑中间文件后重新执行后续步骤：

| 文件 | 说明 |
|------|------|
| `01_parsed.json` | 修正解析错误 |
| `02_chunked.json` | 调整分块 |
| `03_batch_*.json` | 修改摘要内容 |
| `04_chapters.json` | 修改章节规划 |
| `05_article_data.json` | 修改文章内容 |

## 目录结构

```
podcast-to-article/
├── SKILL.md
├── scripts/
│   ├── run.py               # 主入口（创建会话文件夹）
│   ├── parse_transcript.py  # 解析 Markdown 字幕
│   ├── chunk_text.py        # 自适应文本分块
│   └── build_html.py        # 生成 HTML
├── prompts/
│   ├── 01-parse.md
│   ├── 02-summarize.md
│   ├── 03-cluster.md
│   └── 04-compose.md
├── assets/
│   ├── fonts/
│   └── template.html
└── outputs/                 # 会话文件夹（Obsidian Vault 集成路径）
```

## 设计理念

1. **AI 做创意**：理解内容、提取精华、规划结构
2. **脚本做执行**：模板渲染、HTML 生成、格式统一
3. **会话隔离**：每次运行独立文件夹，所有过程文件完整保留

## 依赖

- Python 3.8+
- requests 库

---

Built with ❤️ by Kami
