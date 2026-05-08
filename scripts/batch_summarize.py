#!/usr/bin/env python3
"""
批量处理脚本 - 使用 AI 对每个 chunk 进行摘要
"""
import json
import os
from pathlib import Path

SKILL_DIR = Path(__file__).parent.parent
OUTPUT_DIR = SKILL_DIR / "outputs" / "luofuli-2026-05-07"
PROMPTS_DIR = SKILL_DIR / "prompts"

def load_chunk_texts():
    """加载所有 chunk 文本"""
    chunks = []
    for i in range(1, 10):
        fname = OUTPUT_DIR / f"chunk_{i}_text.txt"
        if fname.exists():
            with open(fname, 'r', encoding='utf-8') as f:
                text = f.read()
            chunks.append({
                "index": i,
                "text": text,
                "char_count": len(text)
            })
    return chunks

def main():
    chunks = load_chunk_texts()
    print(f"加载了 {len(chunks)} 个 chunk")

    for chunk in chunks:
        print(f"\nChunk {chunk['index']}: {chunk['char_count']} 字符")
        print(f"  前100字符: {chunk['text'][:100]}...")

    # 打印提示信息
    print("""
========================================
下一步：使用 AI 执行摘要处理
========================================

请将以下信息复制给 AI 助手执行摘要：

---

请帮我处理播客转文章任务，对每个 chunk 进行摘要。

Chunk 信息：
""")

    for chunk in chunks:
        print(f"- Chunk {chunk['index']}: {chunk['char_count']} 字符")

    print("""

请按以下步骤处理：

1. 读取 ~/.workbuddy/skills/podcast-to-article/prompts/02-summarize.md 作为指导
2. 对每个 chunk 生成详细摘要（不压缩内容）
3. 保存到 outputs/luofuli-2026-05-07/03-summaries.json
   格式: {"summaries": [{"chunk_index": 1, "summary": "..."}, ...]}

4. 然后读取 prompts/03-cluster.md 进行章节规划
5. 最后读取 prompts/04-compose.md 生成最终文章

---
""")

if __name__ == "__main__":
    main()
