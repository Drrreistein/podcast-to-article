#!/usr/bin/env python3
"""
build_html.py
根据模板和数据生成最终 HTML 文件

用法:
    python build_html.py <article_data.json> <template.html> <output.html>
"""

import json
import sys
from pathlib import Path
from typing import Dict, List
import re


def escape_html(text: str) -> str:
    """转义 HTML 特殊字符"""
    if not text:
        return ""
    return (text
        .replace('&', '&amp;')
        .replace('<', '&lt;')
        .replace('>', '&gt;')
        .replace('"', '&quot;')
        .replace("'", '&#39;'))


def escape_html_preserve_tags(text: str) -> str:
    """
    只对 HTML 标签外的纯文本做转义，保留标签本身。
    用于 LLM 输出内容中包含 <span class="hl"> 等格式标签的场景。
    """
    import html as html_module
    parts = re.split(r'(<[^>]+>)', text)
    result = []
    for part in parts:
        if re.match(r'<[^>]+>$', part):
            result.append(part)
        else:
            result.append(html_module.escape(part))
    return ''.join(result)


def format_content_as_paragraphs(content: str) -> str:
    """
    将文本内容转换为带 <p> 标签的 HTML 段落。

    处理逻辑：
    1. 识别并保护已有的 HTML 标签（如 <span class="hl">）
    2. 对标签外的纯文本做 HTML 转义
    3. 按双换行分隔段落（Markdown 风格）
    4. 每个段落用 <p> 包裹，单换行转为 <br>
    """
    if not content:
        return ""

    # 先按双换行分隔段落（Markdown 段落分隔风格）
    paragraphs = content.split('\n\n')

    result = []
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        # 保护 HTML 标签，只转义纯文本
        escaped_para = escape_html_preserve_tags(para)
        # 处理段落内部的单换行（转为 <br>）
        escaped_para = escaped_para.replace('\n', '<br>')

        result.append(f'      <p>{escaped_para}</p>')

    return '\n'.join(result)


def auto_extract_placeholders(template: str) -> List[str]:
    """从模板中提取所有未被显式映射的占位符，供自动填充"""
    all_placeholders = re.findall(r'\{\{([^}]+)\}\}', template)
    # 去重，保留顺序
    seen = set()
    unique = []
    for p in all_placeholders:
        if p not in seen:
            seen.add(p)
            unique.append(p.strip())
    return unique


def build_html(data: Dict, template_path: str) -> str:
    """构建最终 HTML"""

    # 读取模板
    template = Path(template_path).read_text(encoding='utf-8')

    # ── 准备数据 ──────────────────────────────────────────
    title       = data.get('title', '')
    subtitle    = data.get('subtitle', '')
    guest       = data.get('guest', {})
    guest_name  = guest.get('name', '嘉宾')
    guest_role  = guest.get('role', '')
    host        = data.get('host', '主持人')
    source      = data.get('source', '')
    source_url  = data.get('source_url', '')
    date        = data.get('date', '')
    duration    = data.get('duration', '')
    intro       = data.get('intro', '')
    doc_title   = f'{title} · {guest_name}'

    # ── 显式映射（占位符 → 值）──────────────────────────────
    # 注释中的示例占位符 → 清空
    explicit = {
        '{{第一章标题}}': '',
        '{{第二章标题}}': '',
        '{{章节导语：这段讨论的核心问题，1-2句话。}}': '',
        '{{正文内容：将对话改写为流畅的第一人称叙述。保留关键细节和数据，纯叙述无引用。}}': '',
        '{{精选原句引用}}': '',
        '{{说话人}}': '',
        '{{时间戳}}': '',
        '{{继续正文...}}': '',
        '{{这一段的核心观点总结。}}': '',
        '{{章节导语...}}': '',
        '{{正文...}}': '',
        '{{原句}}': '',
        '{{继续...}}': '',
        '{{更多章节...}}': '',
        '{{金句1}}': '',
        '{{金句2}}': '',
        '{{金句3}}': '',
        '{{出处}}': '',
        # 封面 / 导读
        '{{200字左右的导读，介绍这篇访谈的核心内容、适合什么读者、有什么价值点。}}': intro,
        # 页脚
        '{{source_url}}':   source_url,
        '{{来源链接}}':     source_url,
        '{{source}}':       source if source else source_url,
    }

    # ── 自动映射（JSON 字段 → 同名占位符）────────────────────
    # 只要 JSON 中有字段，就会自动填充同名 {{xxx}} 占位符
    # 例如 data 有 "title" → 模板中的 {{title}} 会被替换
    flat_data = {**data, **guest}  # guest 字段也提升到顶层
    auto = {}
    for key, value in flat_data.items():
        if not value:
            continue
        # 跳过复杂类型
        if isinstance(value, (list, dict)):
            continue
        ph = f'{{{{{key}}}}}'
        if ph not in explicit and ph not in auto:
            auto[ph] = escape_html(str(value))

    # 封面专用映射（从 JSON 字段组合）
    explicit[f'{{{{访谈标题}}}}']           = escape_html(title)
    explicit[f'{{{{副标题 / 一句话描述}}}}'] = escape_html(subtitle)
    explicit[f'{{{{嘉宾名称}}}}']           = escape_html(guest_name)
    explicit[f'{{{{嘉宾身份描述}}}}']        = escape_html(guest_role)
    explicit[f'{{{{主持人}}}}']             = escape_html(host)
    explicit[f'{{{{日期}}}}']               = date
    explicit[f'{{{{来源平台}}}}']           = source
    explicit[f'{{{{时长}}}}']               = duration
    explicit[f'{{{{文档标题}}}}']            = escape_html(doc_title)
    explicit[f'{{{{作者}}}}']               = escape_html(guest_name)
    explicit[f'{{{{摘要}}}}']               = escape_html(intro[:150] if intro else subtitle)
    explicit[f'{{{{关键词}}}}']             = escape_html(f'播客, 访谈, {guest_name}, AI')
    explicit[f'{{{{整理日期}}}}']            = date

    # 合并
    replacements = {**explicit, **auto}

    # ── 执行替换 ───────────────────────────────────────────
    html = template
    for old, new in replacements.items():
        pattern = r'\s*' + re.escape(old) + r'\s*'
        html = re.sub(pattern, new, html)

    # ── 封面 meta 行（嘉宾名称 + 身份组合）────────────────────
    meta_parts = [f'<strong>{escape_html(guest_name)}</strong>']
    if guest_role:
        meta_parts.append(escape_html(guest_role))
    meta_parts.append(f'主持：{escape_html(host)}')
    if date:
        meta_parts.append(date)
    if duration:
        meta_parts.append(f'时长：{duration}')
    if source:
        meta_parts.append(f'来源：{source}')
    meta_html = '<br>\n    '.join(meta_parts)
    html = html.replace('{{嘉宾名称}}<br>', meta_html)
    # 兜底：仍保留的 {{嘉宾名称}} 单独替换
    html = html.replace('{{嘉宾名称}}', escape_html(guest_name))

    # ── 渲染目录 ───────────────────────────────────────────
    chapters = data.get('chapters', [])
    toc_items = []
    for i, chapter in enumerate(chapters):
        num  = chapter.get('num', str(i + 1).zfill(2))
        ctitle = escape_html(chapter.get('title', ''))
        toc_items.append(
            f'    <div class="timeline-index-item">\n'
            f'      <span class="timeline-index-time">{num}</span>\n'
            f'      <span class="timeline-index-topic">{ctitle}</span>\n'
            f'    </div>'
        )
    toc_html = '\n'.join(toc_items)
    toc_pattern = r'\{\{#each chapters\}\}.*?\{\{/each\}\}'
    html = re.sub(toc_pattern, toc_html, html, flags=re.DOTALL)

    # ── 渲染章节 ───────────────────────────────────────────
    chapters_html = []
    for i, chapter in enumerate(chapters):
        num     = chapter.get('num', str(i + 1).zfill(2))
        ctitle  = escape_html(chapter.get('title', ''))
        lead    = escape_html_preserve_tags(chapter.get('lead', ''))
        content = chapter.get('content', '')
        
        # 将内容格式化为带 <p> 标签的段落
        formatted_content = format_content_as_paragraphs(content)
        
        chapters_html.append(
            f'  <!-- ═════════════ CHAPTER {num} ═════════════ -->\n'
            f'  <section class="chapter">\n'
            f'    <div class="chapter-num">{num}</div>\n'
            f'    <h1>{ctitle}</h1>\n'
            f'    <p class="lead">{lead}</p>\n'
            f'    <div class="chapter-content">\n'
            f'{formatted_content}\n'
            f'    </div>\n'
            f'  </section>'
        )
    chapters_html_str = '\n\n'.join(chapters_html)
    chapters_placeholder = '<!-- ═════════════ 更多章节... ═════════════ -->'
    if chapters_placeholder in html:
        html = html.replace(chapters_placeholder, chapters_html_str)

    # ── 清理残余占位符 ─────────────────────────────────────
    html = re.sub(r'\s*\{\{[^}]+\}\}\s*', '', html)
    html = re.sub(r'<section class="chapter">\s*<div class="chapter-num">\d+</div>\s*<h1></h1>.*?</section>', '', html, flags=re.DOTALL)

    return html


def main():
    if len(sys.argv) < 4:
        print("用法: python build_html.py <article_data.json> <template.html> <output.html>")
        sys.exit(1)

    data_file    = sys.argv[1]
    template_file = sys.argv[2]
    output_file  = sys.argv[3]

    print(f"读取文章数据: {data_file}")
    print(f"使用模板: {template_file}")

    with open(data_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    html = build_html(data, template_file)

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"HTML 已生成: {output_file}")
    print(f"   大小: {len(html)} 字节")


if __name__ == "__main__":
    main()
