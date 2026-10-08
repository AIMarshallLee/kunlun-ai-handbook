#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
昆仑增长：全书 520 条商业出版级 PDF 编译系统 (Book PDF Compiler)
将 docs/ 下所有分卷聚合，并基于高审美 CSS 渲染为出版级 HTML，
调用系统原生 Microsoft Edge 无头引擎导出印刷级 PDF 电子书。
"""

import os
import re
import sys
import subprocess
import html

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS_DIR = os.path.join(ROOT_DIR, "docs")
OUTPUT_HTML = os.path.join(DOCS_DIR, "book_preview.html")
OUTPUT_PDF = os.path.join(DOCS_DIR, "高性价比企业AI落地指南_全本完整版.pdf")

EDGE_PATHS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    os.path.expanduser(r"~\AppData\Local\Microsoft\Edge\Application\msedge.exe")
]

def find_edge():
    for p in EDGE_PATHS:
        if os.path.exists(p):
            return p
    return None

def md_to_html(md_text):
    """
    轻量高效自研 Markdown 转 HTML 转换器（针对全书六段论深度定制）
    """
    lines = md_text.split('\n')
    html_lines = []
    in_code_block = False
    in_list = False
    in_entry = False

    for line in lines:
        stripped = line.strip()

        # 代码块处理
        if stripped.startswith('```'):
            if in_code_block:
                html_lines.append('</code></pre>')
                in_code_block = False
            else:
                html_lines.append('<pre><code>')
                in_code_block = True
            continue

        if in_code_block:
            html_lines.append(html.escape(line))
            continue

        # 闭合列表
        if in_list and not stripped.startswith('- ') and not stripped.startswith('* ') and stripped != '':
            html_lines.append('</ul>')
            in_list = False

        # 一级卷标题
        if line.startswith('# '):
            if in_entry:
                html_lines.append('</div>')
                in_entry = False
            title = line[2:].strip()
            html_lines.append(f'<div class="volume-break"></div><h1 class="volume-title">{html.escape(title)}</h1>')
            continue

        # 二级模块标题
        if line.startswith('## '):
            if in_entry:
                html_lines.append('</div>')
                in_entry = False
            title = line[3:].strip()
            html_lines.append(f'<h2 class="module-title">{html.escape(title)}</h2>')
            continue

        # 三级条目动作标题 (### 001. xxx)
        if re.match(r'^###\s+(\d+)\.\s+(.+)', line):
            if in_entry:
                html_lines.append('</div>')
            m = re.match(r'^###\s+(\d+)\.\s+(.+)', line)
            num, title = m.groups()
            in_entry = True
            html_lines.append(f'<div class="entry-card" id="item-{num}">')
            html_lines.append(f'  <div class="entry-header"><span class="entry-num">#{int(num):03d}</span><span class="entry-title">{html.escape(title)}</span></div>')
            continue

        # 引用块
        if line.startswith('> '):
            quote = line[2:].strip()
            html_lines.append(f'<div class="quote-block">{_format_inline(quote)}</div>')
            continue

        # 横线
        if stripped in ['---', '***', '___']:
            html_lines.append('<hr class="divider" />')
            continue

        # 条目内六段论特征匹配
        if stripped.startswith('- **成本**：') or stripped.startswith('- **成本**:'):
            val = stripped.split('：', 1)[-1].split(':', 1)[-1]
            html_lines.append(f'  <div class="field-row field-cost"><span class="field-label">💰 成本投入</span><span class="field-val">{_format_inline(val)}</span></div>')
            continue

        if stripped.startswith('- **说人话**：') or stripped.startswith('- **说人话**:'):
            val = stripped.split('：', 1)[-1].split(':', 1)[-1]
            html_lines.append(f'  <div class="field-row field-human"><span class="field-label">🗣️ 说 人 话</span><span class="field-val">{_format_inline(val)}</span></div>')
            continue

        if stripped.startswith('- **收益**：') or stripped.startswith('- **收益**:'):
            html_lines.append('  <div class="benefits-container"><span class="field-label">📈 量化收益</span><div class="benefits-grid">')
            continue

        # 收益四维子条目
        if stripped.startswith('*金钱*：') or stripped.startswith('*金钱*:') or stripped.startswith('- *金钱*：'):
            val = stripped.split('：', 1)[-1].split(':', 1)[-1]
            html_lines.append(f'    <div class="benefit-tag tag-money"><strong>[金钱资本]</strong> {_format_inline(val)}</div>')
            continue
        if stripped.startswith('*时间*：') or stripped.startswith('*时间*:') or stripped.startswith('- *时间*：'):
            val = stripped.split('：', 1)[-1].split(':', 1)[-1]
            html_lines.append(f'    <div class="benefit-tag tag-time"><strong>[时间人效]</strong> {_format_inline(val)}</div>')
            continue
        if stripped.startswith('*寿命*：') or stripped.startswith('*寿命*:') or stripped.startswith('- *寿命*：'):
            val = stripped.split('：', 1)[-1].split(':', 1)[-1]
            html_lines.append(f'    <div class="benefit-tag tag-life"><strong>[企业寿命]</strong> {_format_inline(val)}</div>')
            continue
        if stripped.startswith('*自由*：') or stripped.startswith('*自由*:') or stripped.startswith('- *自由*：'):
            val = stripped.split('：', 1)[-1].split(':', 1)[-1]
            html_lines.append(f'    <div class="benefit-tag tag-free"><strong>[人身自由]</strong> {_format_inline(val)}</div>')
            html_lines.append('  </div></div>')  # 闭合 benefits-grid 和 benefits-container
            continue

        if stripped.startswith('- **证据等级**：') or stripped.startswith('- **证据等级**:'):
            val = stripped.split('：', 1)[-1].split(':', 1)[-1].strip()
            level_char = 'a' if 'a' in val.lower() else ('b' if 'b' in val.lower() else 'c')
            html_lines.append(f'  <div class="field-row field-evidence"><span class="field-label">⚖️ 证据分级</span><span class="badge badge-{level_char}">{html.escape(val)}</span></div>')
            continue

        if stripped.startswith('- **来源**：') or stripped.startswith('- **来源**:'):
            val = stripped.split('：', 1)[-1].split(':', 1)[-1]
            html_lines.append(f'  <div class="field-row field-source"><span class="field-label">📜 法条/依据</span><span class="field-val">{_format_inline(val)}</span></div>')
            continue

        if stripped.startswith('- **备注**：') or stripped.startswith('- **备注**:'):
            val = stripped.split('：', 1)[-1].split(':', 1)[-1]
            html_lines.append(f'  <div class="field-row field-notes"><span class="field-label">💡 实战避坑</span><span class="field-val">{_format_inline(val)}</span></div>')
            continue

        # 普通无序列表
        if stripped.startswith('- ') or stripped.startswith('* '):
            if not in_list:
                html_lines.append('<ul>')
                in_list = True
            content = stripped[2:].strip()
            html_lines.append(f'  <li>{_format_inline(content)}</li>')
            continue

        # 普通段落
        if stripped != '':
            html_lines.append(f'<p>{_format_inline(stripped)}</p>')

    if in_list:
        html_lines.append('</ul>')
    if in_entry:
        html_lines.append('</div>')

    return '\n'.join(html_lines)

def _format_inline(text):
    """
    处理行内加粗、斜体、代码、链接
    """
    # 转义基础字符
    # 替换加粗 **text**
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    # 替换斜体 *text*
    text = re.sub(r'\*([^\*]+?)\*', r'<em>\1</em>', text)
    # 替换行内代码 `code`
    text = re.sub(r'`([^`]+?)`', r'<code>\1</code>', text)
    return text

def compile_book():
    print("=" * 75)
    print("🚀 启动《高性价比企业 AI 落地指南》全书商业出版级 PDF 编译系统...")
    print("=" * 75)

    doc_files = [
        "00_Preface_and_Dictionary.md",
        "01_Volume1_Redlines_and_Pitfalls.md",
        "02_Volume2_Traffic_and_Sales.md",
        "03_Volume3_Dev_and_RAG.md",
        "04_Volume4_Internal_and_Org.md",
        "05_Volume5_Industries.md",
        "06_Deep_Tech_and_Production.md",
        "07_Final_Decisive_Volume.md",
        "08_Appendices.md"
    ]

    all_html_sections = []

    for idx, fname in enumerate(doc_files, 1):
        fpath = os.path.join(DOCS_DIR, fname)
        if not os.path.exists(fpath):
            print(f"⚠️ 找不到文件: {fname}，跳过。")
            continue
        print(f"📖 [{idx}/{len(doc_files)}] 正在解析与排版: {fname}...")
        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read()
        section_html = md_to_html(content)
        all_html_sections.append(section_html)

    book_body = '\n'.join(all_html_sections)

    # 顶奢排版 CSS 样式
    full_html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>高性价比企业 AI 落地指南 - 昆仑增长 出品</title>
<style>
  @page {{
    size: A4;
    margin: 20mm 15mm 20mm 15mm;
    @bottom-center {{
      content: counter(page);
      font-size: 9pt;
      color: #888;
    }}
  }}
  *, *::before, *::after {{
    box-sizing: border-box;
  }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", "WenQuanYi Micro Hei", sans-serif;
    color: #1e293b;
    background-color: #ffffff;
    line-height: 1.6;
    font-size: 10pt;
    margin: 0;
    padding: 0;
  }}

  /* 封面排版 */
  .cover-page {{
    page-break-after: always;
    height: 100vh;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    text-align: center;
    background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #0369a1 100%);
    color: #ffffff;
    padding: 60px 40px;
  }}
  .cover-logo {{
    font-size: 18pt;
    letter-spacing: 4px;
    font-weight: 700;
    color: #38bdf8;
    margin-bottom: 30px;
    text-transform: uppercase;
  }}
  .cover-title {{
    font-size: 32pt;
    font-weight: 900;
    line-height: 1.25;
    margin: 0 0 20px 0;
    color: #ffffff;
    letter-spacing: 1px;
    text-shadow: 0 4px 12px rgba(0,0,0,0.4);
  }}
  .cover-subtitle {{
    font-size: 14pt;
    color: #cbd5e1;
    max-width: 650px;
    line-height: 1.6;
    margin-bottom: 50px;
  }}
  .cover-badges {{
    display: flex;
    gap: 15px;
    margin-bottom: 60px;
  }}
  .cover-pill {{
    background: rgba(255, 255, 255, 0.15);
    border: 1px solid rgba(255, 255, 255, 0.3);
    padding: 6px 18px;
    border-radius: 20px;
    font-size: 10pt;
    font-weight: 600;
  }}
  .cover-footer {{
    margin-top: auto;
    font-size: 10pt;
    color: #94a3b8;
    border-top: 1px solid rgba(255,255,255,0.2);
    padding-top: 20px;
    width: 80%;
  }}

  /* 卷次与模块标题 */
  .volume-break {{
    page-break-before: always;
  }}
  .volume-title {{
    font-size: 20pt;
    font-weight: 800;
    color: #0f172a;
    border-bottom: 3px solid #2563eb;
    padding-bottom: 10px;
    margin-top: 40px;
    margin-bottom: 25px;
  }}
  .module-title {{
    font-size: 14pt;
    font-weight: 700;
    color: #1e3a8a;
    background: #f0fdf4;
    border-left: 5px solid #16a34a;
    padding: 8px 14px;
    margin-top: 30px;
    margin-bottom: 20px;
    border-radius: 0 6px 6px 0;
  }}

  /* 六段论卡片 */
  .entry-card {{
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 14px 16px;
    margin-bottom: 18px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.03);
    page-break-inside: avoid; /* 绝不在单个卡片内部被强制断页 */
  }}
  .entry-header {{
    display: flex;
    align-items: baseline;
    border-bottom: 1px dashed #cbd5e1;
    padding-bottom: 8px;
    margin-bottom: 10px;
  }}
  .entry-num {{
    font-family: Consolas, monospace;
    font-size: 12pt;
    font-weight: 800;
    color: #2563eb;
    margin-right: 10px;
  }}
  .entry-title {{
    font-size: 11pt;
    font-weight: 700;
    color: #0f172a;
  }}

  /* 行级属性 */
  .field-row {{
    margin-bottom: 6px;
    display: flex;
    align-items: flex-start;
    font-size: 9.5pt;
  }}
  .field-label {{
    min-width: 82px;
    font-weight: 700;
    color: #475569;
    flex-shrink: 0;
  }}
  .field-val {{
    color: #334155;
    flex-grow: 1;
  }}
  .field-human {{
    background: #fefce8;
    border-left: 3px solid #eab308;
    padding: 6px 10px;
    border-radius: 0 4px 4px 0;
    margin: 8px 0;
  }}
  .field-human .field-label {{
    color: #854d0e;
  }}
  .field-human .field-val {{
    color: #713f12;
    font-weight: 500;
  }}

  /* 收益网格 */
  .benefits-container {{
    margin: 8px 0;
  }}
  .benefits-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 6px;
    margin-top: 4px;
  }}
  .benefit-tag {{
    font-size: 8.5pt;
    padding: 5px 8px;
    border-radius: 4px;
    line-height: 1.4;
  }}
  .tag-money {{ background: #ecfdf5; border: 1px solid #a7f3d0; color: #065f46; }}
  .tag-time  {{ background: #eff6ff; border: 1px solid #bfdbfe; color: #1e40af; }}
  .tag-life  {{ background: #fdf4ff; border: 1px solid #f5d0fe; color: #86198f; }}
  .tag-free  {{ background: #fff1f2; border: 1px solid #fecdd3; color: #9f1239; }}

  /* 徽章 */
  .badge {{
    display: inline-block;
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 8pt;
    font-weight: 700;
    text-transform: uppercase;
  }}
  .badge-a {{ background: #dc2626; color: #ffffff; }}
  .badge-b {{ background: #2563eb; color: #ffffff; }}
  .badge-c {{ background: #64748b; color: #ffffff; }}

  .quote-block {{
    border-left: 4px solid #94a3b8;
    background: #f8fafc;
    padding: 8px 14px;
    color: #475569;
    font-style: italic;
    margin: 12px 0;
    border-radius: 0 4px 4px 0;
  }}
  .divider {{
    border: none;
    border-top: 1px solid #e2e8f0;
    margin: 25px 0;
  }}

  /* 打印时优化 */
  @media print {{
    .cover-page {{
      height: 100vh;
    }}
    .entry-card {{
      box-shadow: none;
      border: 1px solid #cbd5e1;
    }}
  }}
</style>
</head>
<body>

<!-- 商业出版封面 -->
<div class="cover-page">
  <div class="cover-logo">KUNLUN GROWTH · 昆仑增长 出品</div>
  <h1 class="cover-title">高性价比企业 AI 落地指南</h1>
  <div class="cover-subtitle">
    拒绝 PPT 泡沫与技术炫技，专注法条、代码、算力账单与真实毛利。<br>
    520 条全量工业级建议，逐条六段论展开，全方位守卫企业身家与利润。
  </div>
  <div class="cover-badges">
    <div class="cover-pill">520 条工业级建议</div>
    <div class="cover-pill">四维收益深度量化</div>
    <div class="cover-pill">A/B/C 级法条证据支撑</div>
    <div class="cover-pill">全周期 TCO 测算</div>
  </div>
  <div class="cover-footer">
    昆仑增长 数字化咨询团队 编著 · 2026 商业实战典藏版 · 基于 CC BY-NC-SA 4.0 (非商业性使用) 许可协议发布
  </div>
</div>

<!-- 全书正文 -->
{book_body}

</body>
</html>
"""

    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(full_html)
    print(f"✅ 排版预览 HTML 生成成功: {OUTPUT_HTML} (文件大小: {os.path.getsize(OUTPUT_HTML)/1024:.1f} KB)")

    edge_bin = find_edge()
    if not edge_bin:
        print("⚠️ 未找到 Edge 可执行文件，无法直接无头渲染 PDF。请使用浏览器打开 HTML 手动另存为 PDF。")
        return

    print(f"🖨️ 调用 Edge 无头排版引擎进行 PDF 印刷级编译: {edge_bin}...")
    cmd = [
        edge_bin,
        "--headless",
        "--disable-gpu",
        "--run-all-compositor-stages-before-draw",
        f"--print-to-pdf={OUTPUT_PDF}",
        "--no-pdf-header-footer",
        OUTPUT_HTML
    ]

    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
        if os.path.exists(OUTPUT_PDF) and os.path.getsize(OUTPUT_PDF) > 1024:
            pdf_size_mb = os.path.getsize(OUTPUT_PDF) / (1024 * 1024)
            print("=" * 75)
            print(f"🎉 商业出版级 PDF 编译大功告成！")
            print(f"📁 PDF 保存路径: {OUTPUT_PDF}")
            print(f"📦 文件总大小: {pdf_size_mb:.2f} MB")
            print("=" * 75)
        else:
            print("⚠️ PDF 输出文件生成异常，请检查渲染日志:", res.stderr.decode('utf-8', errors='ignore'))
    except Exception as e:
        print(f"❌ 渲染执行失败: {e}")

if __name__ == "__main__":
    compile_book()
