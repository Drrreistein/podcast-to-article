# 01 - 解析与实体提取

## 任务

你是一个播客访谈内容分析师。请分析以下访谈字幕，提取关键信息。

## 输入

```markdown
{{raw_text}}
```

## 输出要求

请以 JSON 格式输出以下信息：

```json
{
  "title": "访谈标题",
  "subtitle": "一句话描述访谈内容",
  "guest": {
    "name": "嘉宾全名",
    "role": "嘉宾身份/头衔",
    "bio": "一句话嘉宾简介"
  },
  "host": "主持人姓名",
  "date": "YYYY-MM-DD 或 未知",
  "source": "来源平台（如 YouTube、播客名等）",
  "source_url": "原始链接或 空字符串",
  "duration_minutes": 估算分钟数,
  "topics": ["主题1", "主题2", ...],
  "intro": "200字左右的导读，介绍访谈的核心内容、适合什么读者、有什么价值"
}
```

## 注意事项

1. **title**: 从原始内容中提取或根据内容概括
2. **guest**: 仔细识别嘉宾身份，通常在开场介绍中出现
3. **topics**: 识别访谈涵盖的主要话题/主题
4. **intro**: 用简洁的语言概括访谈的价值点，让读者快速判断是否需要阅读

## 示例输出

```json
{
  "title": "从 Vibe Coding 到 Agentic Engineering",
  "subtitle": "Andrej Karpathy 谈 AI 编程范式的转变",
  "guest": {
    "name": "Andrej Karpathy",
    "role": "OpenAI 联合创始人、前特斯拉 AI 总监、Eureka Labs 创始人",
    "bio": "AI 领域知名科学家，以「vibe coding」等概念闻名"
  },
  "host": "Stephanie Zhan",
  "date": "2026-04-29",
  "source": "Sequoia Capital AI Ascent 2026",
  "source_url": "https://www.youtube.com/watch?v=96jN2OCOfLs",
  "duration_minutes": 30,
  "topics": ["AI编程", "软件3.0", "Agentic Engineering", "可验证性", "教育"],
  "intro": "本文是 Andrej Karpathy 在 Sequoia AI Ascent 2026 上的访谈记录。他分享了从去年发明「vibe coding」概念到今年感受到「从未如此落后于编程」心态转变的背后原因……"
}
```
