#!/usr/bin/env python3
"""
parse_transcript.py
解析 Markdown 格式的访谈字幕文件，提取结构化数据

输入格式：
- YAML frontmatter（可选）
- 时间戳章节索引
- Transcript 部分
- 时间戳格式：`**0:02** · 内容`

输出：
{
    "title": str,
    "source": str,
    "speakers": [{"name": str, "role": str}],
    "chapters": [{"time": str, "title": str}],
    "segments": [{"time": str, "content": str}],
    "raw_text": str
}
"""

import re
import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional


def parse_frontmatter(content: str) -> tuple[Dict[str, Any], str]:
    """解析 YAML frontmatter"""
    frontmatter = {}
    body = content

    # 检查是否有 frontmatter
    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3:
            yaml_content = parts[1]
            body = parts[2].strip()

            # 简单的 YAML 解析（处理基本格式）
            for line in yaml_content.strip().split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    value = value.strip().strip('"').strip("'")
                    if value:
                        frontmatter[key.strip()] = value

    return frontmatter, body


def parse_chapters(body: str) -> List[Dict[str, str]]:
    """解析时间戳章节索引"""
    chapters = []

    # 匹配格式：00:00 Introduction 或 00:00 · Introduction
    pattern = r'(\d{1,2}:\d{2}(?::\d{2})?)\s*(?:·|\s{2,})\s*(.+)'

    for line in body.split('\n'):
        line = line.strip()
        match = re.match(pattern, line)
        if match:
            time, title = match.groups()
            # 标准化时间格式
            time = normalize_time(time)
            chapters.append({"time": time, "title": title.strip()})

    return chapters


def normalize_time(time_str: str) -> str:
    """将时间标准化为 MM:SS 或 HH:MM:SS"""
    parts = time_str.split(':')

    if len(parts) == 2:
        return f"{int(parts[0]):02d}:{int(parts[1]):02d}"
    elif len(parts) == 3:
        return f"{int(parts[0]):02d}:{int(parts[1]):02d}:{int(parts[2]):02d}"
    else:
        return time_str


def parse_transcript(body: str) -> List[Dict[str, str]]:
    """解析 Transcript 部分"""
    segments = []

    # 找到 Transcript 部分
    transcript_match = re.search(r'##\s*Transcript', body)
    if transcript_match:
        body = body[transcript_match.end():]

    # 匹配格式：**0:02** · 内容 或 **0:02:** 内容
    pattern = r'\*\*(\d{1,2}:\d{2}(?::\d{2})?)\*\*[:\s]*·?\s*(.+?)(?=\n\*\*|\n##|\Z)'

    matches = re.findall(pattern, body, re.DOTALL)

    for time_match, content in matches:
        time = normalize_time(time_match)
        content = content.strip()
        # 清理内容中的多余空格
        content = re.sub(r'\s+', ' ', content)
        if content:
            segments.append({
                "time": time,
                "content": content
            })

    return segments


def detect_speakers(segments: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """简单检测说话人（基于上下文分析）"""
    # 这里可以扩展更复杂的说话人识别逻辑
    # 当前版本基于常见的访谈模式进行简单推断
    return [{"name": "Guest", "role": "嘉宾"}]


def parse_transcript_file(file_path: str) -> Dict[str, Any]:
    """主解析函数"""
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")

    content = path.read_text(encoding='utf-8')

    # 解析 frontmatter
    frontmatter, body = parse_frontmatter(content)

    # 提取标题
    title = frontmatter.get('title', '')
    if not title:
        # 尝试从第一行提取
        first_line = body.split('\n')[0].strip()
        if first_line and not first_line.startswith('#'):
            title = first_line

    # 解析章节索引
    chapters = parse_chapters(body)

    # 解析正文
    segments = parse_transcript(body)

    # 生成原始文本（用于 AI 处理）
    raw_text = '\n'.join([f"[{s['time']}] {s['content']}" for s in segments])

    return {
        "title": title,
        "source": frontmatter.get('source', ''),
        "published": frontmatter.get('published', ''),
        "speakers": [
            {"name": "Guest", "role": "嘉宾"},
            {"name": "Host", "role": "主持"}
        ],
        "chapters": chapters,
        "segments": segments,
        "raw_text": raw_text,
        "word_count": len(raw_text),
        "duration_minutes": estimate_duration(segments)
    }


def estimate_duration(segments: List[Dict[str, str]]) -> int:
    """估算时长（分钟）"""
    if not segments:
        return 0

    # 获取最后一个时间戳
    last_time = segments[-1]['time']
    parts = last_time.split(':')

    if len(parts) == 2:
        return int(parts[0]) + 1  # 加1分钟缓冲
    elif len(parts) == 3:
        return int(parts[0]) * 60 + int(parts[1]) + 1

    return 0


def save_json(data: Dict[str, Any], output_path: str):
    """保存为 JSON 文件"""
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main():
    if len(sys.argv) < 2:
        print("用法: python parse_transcript.py <输入文件> [输出文件]")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None

    print(f"📖 解析文件: {input_file}")

    try:
        data = parse_transcript_file(input_file)

        print(f"✅ 解析完成!")
        print(f"   标题: {data['title']}")
        print(f"   来源: {data['source']}")
        print(f"   章节数: {len(data['chapters'])}")
        print(f"   段落数: {len(data['segments'])}")
        print(f"   字数: {data['word_count']}")
        print(f"   估算时长: {data['duration_minutes']} 分钟")

        if output_file:
            save_json(data, output_file)
            print(f"💾 已保存到: {output_file}")

        # 输出 JSON 到 stdout（供后续脚本使用）
        print("\n---JSON_OUTPUT---")
        print(json.dumps(data, ensure_ascii=False))

    except Exception as e:
        print(f"❌ 解析失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
