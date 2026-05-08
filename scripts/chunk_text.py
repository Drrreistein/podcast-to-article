#!/usr/bin/env python3
"""
chunk_text.py
自适应文本分块脚本

根据文本长度自动分块：
- < 7000 字：1 块
- 7000-14000 字：2 块
- 14000-28000 字：3-4 块
- > 28000 字：按段落/主题分多块

输出：chunked_data.json
"""

import json
import sys
import re
from pathlib import Path
from typing import Dict, List, Any


def estimate_chinese_equivalent(text: str) -> int:
    """
    估算中文字符等价字数
    - 中文字符：每个算 1
    - 英文单词：每个约算 0.5 个中文字符（因为中文信息密度更高）
    - 标点/空格：忽略
    """
    chinese_count = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')

    # 英文单词估算
    english_words = len(re.findall(r'[a-zA-Z]+', text))
    english_estimate = english_words * 0.6  # 英文单词约等于 0.6 个中文字符

    return int(chinese_count + english_estimate)


def smart_chunk(text: str, segments: List[Dict], target_size: int = 7000) -> List[Dict[str, Any]]:
    """
    智能分块算法

    - 优先按段落边界分块
    - 保持语义完整性
    - 记录每个 chunk 的时间范围
    """
    chunks = []

    if not segments:
        return chunks

    # 计算总字数（中文等价）
    total_chars = sum(estimate_chinese_equivalent(s['content']) for s in segments)

    # 根据字数估算需要的块数
    if total_chars < 7000:
        num_chunks = 1
    elif total_chars < 14000:
        num_chunks = 2
    elif total_chars < 28000:
        num_chunks = 3
    elif total_chars < 40000:
        num_chunks = 4
    else:
        num_chunks = max(4, int(total_chars // 7000) + 1)

    # 每块的字数目标
    chars_per_chunk = total_chars / num_chunks + 1

    current_chunk = {
        "text": "",
        "segments": [],
        "start_time": segments[0]['time'] if segments else "0:00",
        "end_time": ""
    }

    current_chars = 0

    for i, seg in enumerate(segments):
        seg_chars = estimate_chinese_equivalent(seg['content'])

        # 检查是否需要分块
        if current_chars + seg_chars > chars_per_chunk and current_chunk['text']:
            # 保存当前块
            current_chunk['end_time'] = seg['time']
            current_chunk['text'] = current_chunk['text'].strip()
            current_chunk['word_count'] = estimate_chinese_equivalent(current_chunk['text'])
            chunks.append(current_chunk)

            # 开始新块
            current_chunk = {
                "text": seg['content'],
                "segments": [seg],
                "start_time": seg['time'],
                "end_time": ""
            }
            current_chars = seg_chars
        else:
            # 添加到当前块
            if current_chunk['text']:
                current_chunk['text'] += '\n\n' + seg['content']
            else:
                current_chunk['text'] = seg['content']
            current_chunk['segments'].append(seg)
            current_chars += estimate_chinese_equivalent(seg['content'])

    # 保存最后一块
    if current_chunk['text']:
        current_chunk['end_time'] = segments[-1]['time'] if segments else current_chunk['start_time']
        current_chunk['text'] = current_chunk['text'].strip()
        current_chunk['word_count'] = estimate_chinese_equivalent(current_chunk['text'])
        chunks.append(current_chunk)

    # 为每个 chunk 添加索引
    for i, chunk in enumerate(chunks):
        chunk['index'] = i + 1
        chunk['total_chunks'] = len(chunks)

    return chunks


def main():
    if len(sys.argv) < 2:
        print("用法: python chunk_text.py <parsed_data.json> [输出文件]")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None

    print(f"📦 读取解析数据: {input_file}")

    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    segments = data.get('segments', [])
    raw_text = data.get('raw_text', '')

    print(f"📊 原始数据: {len(segments)} 段落, {data.get('word_count', 0)} 字")

    # 执行分块
    chunks = smart_chunk(raw_text, segments)

    print(f"✂️  分块完成: {len(chunks)} 块")

    for i, chunk in enumerate(chunks):
        print(f"   块 {i+1}: {chunk['word_count']} 字, "
              f"时间 {chunk['start_time']} - {chunk['end_time']}")

    result = {
        "title": data.get('title', ''),
        "source": data.get('source', ''),
        "chunks": chunks,
        "total_words": sum(c['word_count'] for c in chunks)
    }

    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"💾 已保存到: {output_file}")

    # 输出 JSON 到 stdout
    print("\n---JSON_OUTPUT---")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
