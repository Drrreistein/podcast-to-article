#!/usr/bin/env python3
"""
run.py - podcast-to-article 主入口脚本

功能：为每次运行创建独立的会话文件夹，保存所有中间过程文件。

用法:
    # 方式一：视频链接（推荐）
    python3 scripts/run.py --url "https://www.youtube.com/watch?v=xxx"

    # 方式二：本地字幕文件
    python3 scripts/run.py "path/to/你的字幕.md"

会话文件夹结构:
    outputs/
    └── {视频ID或输入文件名}_{YYYYMMDD_HHMMSS}/
        ├── metadata.json           # 元信息（来源、块数等）
        ├── 00_transcript.md        # 原始字幕
        ├── 01_parsed.json          # 结构化解析
        ├── 02_chunked.json         # 分块数据
        ├── 03_batch_1.json         # AI 摘要批次1
        ├── 03_batch_2.json         # AI 摘要批次2
        ├── 03_batch_3.json         # AI 摘要批次3
        ├── 04_chapters.json        # 章节规划
        ├── 05_article_data.json    # 最终文章数据
        └── 06_final.html           # 最终 HTML
"""

import os
import re
import sys
import json
import shutil
import argparse
import subprocess
import requests
from pathlib import Path
from datetime import datetime


# ── 路径常量 ────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent
SKILL_DIR  = SCRIPT_DIR.parent
ASSETS_DIR = SKILL_DIR / "assets"
PROMPTS_DIR = SKILL_DIR / "prompts"
# 最终文章输出到 Obsidian Vault
DEFAULT_OUTPUTS = Path("/Users/a1-6/Documents/Obsidian Vault/kb/outputs/podcast")


def extract_video_id(url: str) -> str | None:
    """从 URL 中提取视频 ID"""
    patterns = [
        # 优先匹配完整 YouTube URL，短模式放后面避免误匹配
        (r'youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})', 'youtube'),
        (r'youtube\.com/embed/([a-zA-Z0-9_-]{11})', 'youtube embed'),
        (r'youtu\.be/([a-zA-Z0-9_-]{11})', 'youtube short'),
        (r'bilibili\.com/video/([a-zA-Z0-9]+)', 'bilibili'),
    ]
    for pattern, _ in patterns:
        m = re.search(pattern, url)
        if m:
            return m.group(1)
    return None


def extract_title_from_content(content: str) -> str | None:
    """从字幕内容中提取视频标题"""
    # YAML frontmatter
    m = re.search(r'^title:\s*["\']?(.+?)["\']?\s*$', content, re.MULTILINE)
    if m:
        return m.group(1).strip()
    # Markdown H1
    m = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    if m:
        return m.group(1).strip()
    return None


def create_session_folder(base_dir: Path, identifier: str | None, url: str | None) -> Path:
    """创建会话文件夹"""
    # 优先用视频 ID，其次用文件名标识符，最后用时间戳
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')

    if identifier:
        # 清理文件名中的非法字符
        safe_id = re.sub(r'[^\w\-_. ]', '_', identifier)[:60]
        folder_name = f"{safe_id}_{ts}"
    else:
        folder_name = f"session_{ts}"

    session_dir = base_dir / folder_name
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir


def fetch_url_content(url: str) -> tuple[str | None, str | None]:
    """使用 defuddle.md 提取 URL 字幕内容"""
    print(f"\n🔗 正在从 URL 提取字幕...")
    print(f"   URL: {url}")

    video_id = extract_video_id(url)
    if video_id:
        print(f"   视频ID: {video_id}")

    try:
        defuddle_url = f"https://defuddle.md/{url}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        }
        response = requests.get(defuddle_url, headers=headers, timeout=60)
        response.raise_for_status()
        content = response.text

        if len(content) < 100:
            print(f"⚠️ 警告：获取的内容可能不完整 ({len(content)} 字符)")

        return content, video_id

    except requests.RequestException as e:
        print(f"❌ 获取 URL 内容失败: {e}")
        return None, None


def run_command(cmd: list[str], description: str) -> bool:
    """执行命令并打印输出"""
    print(f"\n{'='*50}")
    print(f"📦 {description}")
    print(f"{'='*50}")

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.stdout:
        print(result.stdout)
    if result.stderr and result.stderr.strip():
        print(result.stderr, file=sys.stderr)

    if result.returncode != 0:
        print(f"❌ 命令执行失败 (code {result.returncode})")
        return False

    return True


def save_metadata(session_dir: Path, data: dict):
    """保存会话元信息"""
    metadata_file = session_dir / "metadata.json"
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✅ 元信息已保存: {metadata_file}")


def main():
    parser = argparse.ArgumentParser(
        description='podcast-to-article: 播客访谈 → 结构化长文',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python3 run.py --url "https://www.youtube.com/watch?v=xxx"
  python3 run.py "video_transcript.md"
  python3 run.py "~/Downloads/interview.md" ./outputs/
        """
    )
    parser.add_argument('--url', '-u', help='视频链接（YouTube、B站等）')
    parser.add_argument('input_file', nargs='?', help='本地字幕 Markdown 文件路径')
    parser.add_argument('output_dir', nargs='?', help='输出根目录（可选，默认 outputs/）')

    args = parser.parse_args()

    # ── 确定输入来源并创建会话文件夹 ──────────────────────
    input_source: str = ""
    input_file: Path | None = None
    video_id: str | None = None
    source_label: str = ""   # 用于文件夹命名

    if args.url:
        print(f"""
╔══════════════════════════════════════════════════╗
║     podcast-to-article                          ║
║     视频链接 → 字幕 → 结构化长文               ║
╚══════════════════════════════════════════════════╝
""")
        print(f"🔗 视频链接: {args.url}")

        content, video_id = fetch_url_content(args.url)
        if not content:
            sys.exit(1)

        # 创建会话文件夹
        base_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else DEFAULT_OUTPUTS
        session_dir = create_session_folder(base_dir, video_id, args.url)

        # 保存原始字幕
        ts_str = datetime.now().strftime('%Y%m%d')
        transcript_file = session_dir / f"00_transcript.md"
        with open(transcript_file, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ 字幕已保存: {transcript_file}")

        input_file = transcript_file
        input_source = f"URL: {args.url}"
        title = extract_title_from_content(content)
        source_label = video_id or "url"

    elif args.input_file:
        input_file = Path(args.input_file).expanduser().resolve()
        if not input_file.exists():
            print(f"❌ 文件不存在: {input_file}")
            sys.exit(1)

        base_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else DEFAULT_OUTPUTS
        source_label = input_file.stem  # 文件名（不含扩展名）
        session_dir = create_session_folder(base_dir, source_label, None)

        print(f"""
╔══════════════════════════════════════════════════╗
║     podcast-to-article                          ║
║     播客访谈 → 结构化长文                       ║
╚══════════════════════════════════════════════════╝
""")
        input_source = f"本地文件: {input_file}"

        # 复制本地文件到会话文件夹
        dest = session_dir / f"00_transcript.md"
        shutil.copy2(input_file, dest)
        input_file = dest
        title = extract_title_from_content(input_file.read_text(encoding='utf-8'))

    else:
        parser.print_help()
        print("\n❌ 请提供 --url 或输入文件")
        sys.exit(1)

    session_dir.mkdir(parents=True, exist_ok=True)
    print(f"📂 会话文件夹: {session_dir}")

    # ── Step 1: 解析字幕 ──────────────────────────────────
    parsed_file = session_dir / "01_parsed.json"

    cmd = [
        sys.executable,
        str(SCRIPT_DIR / "parse_transcript.py"),
        str(input_file),
        str(parsed_file),
    ]
    if not run_command(cmd, "Step 1: 解析字幕"):
        sys.exit(1)

    try:
        parsed_data = json.loads(parsed_file.read_text(encoding='utf-8'))
    except Exception as e:
        print(f"❌ 读取解析结果失败: {e}")
        sys.exit(1)

    word_count    = parsed_data.get('word_count', 0)
    duration_min  = parsed_data.get('duration_minutes', 0)
    raw_title     = parsed_data.get('title', title or '未命名访谈')

    print(f"""
{'='*50}
📊 解析结果
{'='*50}
   标题: {raw_title}
   段落数: {len(parsed_data.get('segments', []))}
   字数: {word_count}
   估算时长: {duration_min} 分钟
""")

    # ── Step 2: 分块 ──────────────────────────────────────
    chunked_file = session_dir / "02_chunked.json"

    cmd = [
        sys.executable,
        str(SCRIPT_DIR / "chunk_text.py"),
        str(parsed_file),
        str(chunked_file),
    ]
    if not run_command(cmd, "Step 2: 自适应文本分块"):
        sys.exit(1)

    try:
        chunked_data = json.loads(chunked_file.read_text(encoding='utf-8'))
    except Exception as e:
        print(f"❌ 读取分块结果失败: {e}")
        sys.exit(1)

    chunks = chunked_data.get('chunks', [])
    total_words = chunked_data.get('total_words', 0)

    print(f"""
{'='*50}
📊 分块结果
{'='*50}
   块数: {len(chunks)}
   总字数: {total_words}
""")
    for chunk in chunks:
        print(f"   块 {chunk['index']}/{chunk['total_chunks']}: "
              f"{chunk['word_count']} 字 "
              f"({chunk.get('start_time', 'N/A')} - {chunk.get('end_time', 'N/A')})")

    # ── 保存元信息 ───────────────────────────────────────
    save_metadata(session_dir, {
        "title":        raw_title,
        "source":       input_source,
        "session_dir":  str(session_dir),
        "video_id":     video_id,
        "word_count":   word_count,
        "duration_min": duration_min,
        "chunks": [
            {
                "index":      c['index'],
                "word_count": c['word_count'],
                "start_time": c.get('start_time'),
                "end_time":   c.get('end_time'),
            }
            for c in chunks
        ],
        "files": {
            "transcript":   "00_transcript.md",
            "parsed":       "01_parsed.json",
            "chunked":      "02_chunked.json",
            "batches":      [f"03_batch_{i+1}.json" for i in range((len(chunks) - 1) // 5 + 1)],
            "chapters":     "04_chapters.json",
            "article_data": "05_article_data.json",
            "final_html":   "06_final.html",
        }
    })

    # ── AI 处理提示 ──────────────────────────────────────
    n_batches = (len(chunks) - 1) // 5 + 1
    batch_tips = "\n".join(
        f"  • batch_{i+1}: chunks {min(i*5+1, len(chunks))}-{min((i+1)*5, len(chunks))}"
        for i in range(n_batches)
    )

    print(f"""
{'='*50}
🎯 AI 处理步骤（复制给 AI 助手）
{'='*50}

请帮我处理播客转文章任务。会话文件夹: {session_dir}

📁 会话结构:
  00_transcript.md  — 原始字幕
  01_parsed.json   — 结构化解析（说话人、时间线、段落）
  02_chunked.json  — {len(chunks)} 个文本块

{batch_tips}
  04_chapters.json     — 章节规划
  05_article_data.json — 最终文章数据
  06_final.html        — 最终 HTML

📋 处理流程:
  1. 读取 {PROMPTS_DIR}/01-parse.md → 处理 01_parsed.json
  2. 读取 {PROMPTS_DIR}/02-summarize.md → 逐块摘要，保存到 03_batch_*.json
  3. 读取 {PROMPTS_DIR}/03-cluster.md → 章节规划，保存到 04_chapters.json
  4. 读取 {PROMPTS_DIR}/04-compose.md → 生成文章，保存到 05_article_data.json
  5. 运行 build_html.py 生成 06_final.html

💡 示例 build_html 命令:
  python3 {SCRIPT_DIR}/build_html.py \\
      {session_dir}/05_article_data.json \\
      {ASSETS_DIR}/template.html \\
      {session_dir}/06_final.html
""")

    # 追加到 AI 提示文件，方便复制
    prompt_summary = session_dir / "00_ai_prompt.txt"
    prompt_summary.write_text(f"""请帮我处理播客转文章任务。

会话文件夹: {session_dir}
块数: {len(chunks)}
{batch_tips}

1. 读取 {PROMPTS_DIR}/01-parse.md，处理 01_parsed.json
2. 读取 {PROMPTS_DIR}/02-summarize.md，逐块摘要 → 03_batch_*.json
3. 读取 {PROMPTS_DIR}/03-cluster.md，章节规划 → 04_chapters.json
4. 读取 {PROMPTS_DIR}/04-compose.md，生成文章 → 05_article_data.json
5. python3 {SCRIPT_DIR}/build_html.py {session_dir}/05_article_data.json {ASSETS_DIR}/template.html {session_dir}/06_final.html
""", encoding='utf-8')
    print(f"📝 AI 提示已保存: {prompt_summary}")


if __name__ == "__main__":
    main()
