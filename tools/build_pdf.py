#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
昆仑增长：全书 520 条商业出版级 PDF 编译系统 (Book PDF Compiler v3.0)
支持 Markdown 复杂表格排版、文中条目超链接（点击直达对应条目）、
A4 纸张页面优化、科技风双栏卡片。
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
    轻量高效自研 Markdown 转 HTML 转换器（深度支持 Markdown 表格与六段论）
    """
    lines = md_text.split('\n')
    html_lines = []
    in_code_block = False
    in_list = False
    in_entry = False
    in_table = False
    table_has_header = False

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

        # 表格处理
        if stripped.startswith('|') and stripped.endswith('|'):
            # 安全切除首尾竖线
            inner = stripped[1:-1]
            cells = [c.strip() for c in inner.split('|')]
            # 检查是否为表头分隔行 (如 | :---: | :--- |)
            if all(re.match(r'^:?-+:?$', c) for c in cells):
                table_has_header = True
                continue
            
            if not in_table:
                if in_list:
                    html_lines.append('</ul>')
                    in_list = False
                html_lines.append('<div class="table-container"><table class="data-table">')
                in_table = True
                table_has_header = False
                # 第一行作为表头
                html_lines.append('  <thead><tr>')
                for c in cells:
                    html_lines.append(f'    <th>{_format_inline(c)}</th>')
                html_lines.append('  </tr></thead><tbody>')
                continue
            else:
                html_lines.append('  <tr>')
                for c in cells:
                    html_lines.append(f'    <td>{_format_inline(c)}</td>')
                html_lines.append('  </tr>')
                continue
        else:
            if in_table:
                html_lines.append('</tbody></table></div>')
                in_table = False

        # 闭合列表
        if in_list and not stripped.startswith('- ') and not stripped.startswith('* ') and stripped != '':
            html_lines.append('</ul>')
            in_list = False

        # 一级卷标题
        if line.startswith('# '):
            if in_table:
                html_lines.append('</tbody></table></div>')
                in_table = False
            if in_entry:
                html_lines.append('</div>')
                in_entry = False
            title = line[2:].strip()
            # 自动生成分卷定位锚点
            vol_id = ""
            for v_num, v_kw in enumerate(["卷首", "第一卷", "第二卷", "第三卷", "第四卷", "第五卷", "第六卷", "第七卷", "附录"]):
                if v_kw in title:
                    vol_id = f' id="vol-{v_num}"'
                    break
            html_lines.append(f'<div class="volume-break"{vol_id}></div><h1 class="volume-title">{html.escape(title)}</h1>')
            continue

        # 二级模块标题
        if line.startswith('## '):
            if in_table:
                html_lines.append('</tbody></table></div>')
                in_table = False
            if in_entry:
                html_lines.append('</div>')
                in_entry = False
            title = line[3:].strip()
            # 附录特定锚点与模块锚点
            mod_id = ""
            if "附录一" in title: mod_id = ' id="appendix-1"'
            elif "附录二" in title: mod_id = ' id="appendix-2"'
            elif "附录三" in title: mod_id = ' id="appendix-3"'
            else:
                m_mod_num = re.search(r'模块([一二三四五六七八九十百]+|[0-9]+)', title)
                if m_mod_num:
                    mod_id = f' id="mod-{m_mod_num.group(1)}"'
            html_lines.append(f'<h2 class="module-title"{mod_id}>{html.escape(title)}</h2>')
            continue

        # 三级条目动作标题 (仅严格匹配 ### 001. xxx 到 520)
        m_item = re.match(r'^###\s+(\d{3})\.\s+(.+)', line)
        if m_item and 1 <= int(m_item.group(1)) <= 520:
            if in_table:
                html_lines.append('</tbody></table></div>')
                in_table = False
            if in_entry:
                html_lines.append('</div>')
            num, title = m_item.groups()
            num_int = int(num)
            in_entry = True
            # 支持数字如 001 和 1 的双重定位锚点
            html_lines.append(f'<div class="entry-card" id="item-{num_int:03d}">')
            html_lines.append(f'  <a id="item-{num_int}"></a>')
            html_lines.append(f'  <div class="entry-header"><span class="entry-num">#{num_int:03d}</span><span class="entry-title">{html.escape(title)}</span></div>')
            continue

        # 普通三级小节标题 (### xxx，如附录小节)
        if line.startswith('### '):
            if in_table:
                html_lines.append('</tbody></table></div>')
                in_table = False
            if in_entry:
                html_lines.append('</div>')
                in_entry = False
            title = line[4:].strip()
            html_lines.append(f'<h3 class="section-subhead">{_format_inline(title)}</h3>')
            continue

        # 普通四级小节标题 (#### xxx)
        if line.startswith('#### '):
            if in_table:
                html_lines.append('</tbody></table></div>')
                in_table = False
            if in_entry:
                html_lines.append('</div>')
                in_entry = False
            title = line[5:].strip()
            html_lines.append(f'<h4 class="section-subhead-4">{_format_inline(title)}</h4>')
            continue

        # 引用块
        if line.startswith('> '):
            quote = line[2:].strip()
            html_lines.append(f'<div class="quote-block">{_format_inline(quote)}</div>')
            continue

        # 横线
        if stripped in ['---', '***', '___']:
            if in_table:
                html_lines.append('</tbody></table></div>')
                in_table = False
            if in_entry:
                html_lines.append('</div>')
                in_entry = False
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

    if in_table:
        html_lines.append('</tbody></table></div>')
    if in_list:
        html_lines.append('</ul>')
    if in_entry:
        html_lines.append('</div>')

    return '\n'.join(html_lines)

def _format_inline(text):
    """
    处理行内加粗、斜体、代码、链接（精准支持 Markdown 超链接 [文本](URL)）
    """
    # 替换加粗 **text**
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    # 替换斜体 *text*
    text = re.sub(r'\*([^\*]+?)\*', r'<em>\1</em>', text)
    # 替换行内代码 `code`
    text = re.sub(r'`([^`]+?)`', r'<code>\1</code>', text)
    # 替换 Markdown 超链接 [文字](链接)
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2" class="doc-link">\1</a>', text)
    return text

def generate_toc_html():
    """
    生成商业出版级全书交互式总目录 (Table of Contents)，支持卷名与模块点击直达
    """
    return """
<!-- 全书交互式总目录 (Apple 极简商务风) -->
<div class="toc-container">
  <div class="toc-header">
    <div class="toc-tag">ARCHITECTURE &amp; MASTER ROADMAP</div>
    <h1 class="toc-main-title">全书架构与总目录导航</h1>
    <p class="toc-lead">全书共八大分卷、27 大核心业务模块、三大实操附录，520 条全量工业级落地建议。点击任意卷名、业务模块或条目编号，即可瞬间直达正文对应位置。</p>
  </div>

  <!-- 卷首篇 -->
  <div class="toc-volume-block">
    <div class="toc-vol-header">
      <a href="#vol-0" class="toc-vol-title">卷首篇：出版前言与标准基石</a>
      <span class="toc-vol-badge">基石篇 · 核心标准</span>
    </div>
    <div class="toc-module-grid">
      <a href="#vol-0" class="toc-module-item">
        <span class="toc-mod-name">一、出版前言：企业 AI 落地的三大致命幻觉与唯一目的</span>
        <span class="toc-mod-range">前言</span>
      </a>
      <a href="#vol-0" class="toc-module-item">
        <span class="toc-mod-name">二、评价体系与口径定义（四维量化收益与 A/B/C 证据）</span>
        <span class="toc-mod-range">标准</span>
      </a>
      <a href="#vol-0" class="toc-module-item highlight-toc-item">
        <span class="toc-mod-name">三、20 大核心业务痛点与条目速查表（含直达锚点）</span>
        <span class="toc-mod-range">速查表</span>
      </a>
      <a href="#vol-0" class="toc-module-item">
        <span class="toc-mod-name">四、20 大行业高频核心术语“说人话”字典</span>
        <span class="toc-mod-range">字典</span>
      </a>
    </div>
  </div>

  <!-- 第一卷 -->
  <div class="toc-volume-block">
    <div class="toc-vol-header">
      <a href="#vol-1" class="toc-vol-title">第一卷：算力与模型防坑红线（第 001 - 040 条）</a>
      <span class="toc-vol-badge">40 条建议</span>
    </div>
    <div class="toc-module-grid">
      <a href="#item-001" class="toc-module-item">
        <span class="toc-mod-name">模块一：反面清单——10大企业常见 AI 伪需求</span>
        <span class="toc-mod-range">#001 - #010</span>
      </a>
      <a href="#item-011" class="toc-module-item">
        <span class="toc-mod-name">模块二：法律与合规红线——网信办算法备案与侵权防范</span>
        <span class="toc-mod-range">#011 - #020</span>
      </a>
      <a href="#item-021" class="toc-module-item">
        <span class="toc-mod-name">模块三：知识产权与商业机密防泄密护栏</span>
        <span class="toc-mod-range">#021 - #030</span>
      </a>
      <a href="#item-031" class="toc-module-item">
        <span class="toc-mod-name">模块四：算力采购与商业 API 账单防刺客</span>
        <span class="toc-mod-range">#031 - #040</span>
      </a>
    </div>
  </div>

  <!-- 第二卷 -->
  <div class="toc-volume-block">
    <div class="toc-vol-header">
      <a href="#vol-2" class="toc-vol-title">第二卷：全域流量与获客增长（第 041 - 099 条）</a>
      <span class="toc-vol-badge">59 条建议</span>
    </div>
    <div class="toc-module-grid">
      <a href="#item-041" class="toc-module-item">
        <span class="toc-mod-name">模块五：爆款内容工程与自媒体矩阵</span>
        <span class="toc-mod-range">#041 - #055</span>
      </a>
      <a href="#item-056" class="toc-module-item">
        <span class="toc-mod-name">模块六：广告投放测款与视觉资产工业化</span>
        <span class="toc-mod-range">#056 - #070</span>
      </a>
      <a href="#item-071" class="toc-module-item">
        <span class="toc-mod-name">模块七：GEO（生成式引擎优化）与搜索流量重构</span>
        <span class="toc-mod-range">#071 - #085</span>
      </a>
      <a href="#item-086" class="toc-module-item">
        <span class="toc-mod-name">模块八：AI SDR 与销售全流程自动化推进</span>
        <span class="toc-mod-range">#086 - #099</span>
      </a>
    </div>
  </div>

  <!-- 第三卷 -->
  <div class="toc-volume-block">
    <div class="toc-vol-header">
      <a href="#vol-3" class="toc-vol-title">第三卷：研发重构与技术底座（第 100 - 130 条）</a>
      <span class="toc-vol-badge">31 条建议</span>
    </div>
    <div class="toc-module-grid">
      <a href="#item-100" class="toc-module-item">
        <span class="toc-mod-name">模块九：AI Coding 辅助编程与工程提效</span>
        <span class="toc-mod-range">#100 - #110</span>
      </a>
      <a href="#item-111" class="toc-module-item">
        <span class="toc-mod-name">模块十：企业级高可用 RAG（检索增强生成）实战</span>
        <span class="toc-mod-range">#111 - #120</span>
      </a>
      <a href="#item-121" class="toc-module-item">
        <span class="toc-mod-name">模块十一：企业级 Agent 与有限状态机（FSM）工作流</span>
        <span class="toc-mod-range">#121 - #130</span>
      </a>
    </div>
  </div>

  <!-- 第四卷 -->
  <div class="toc-volume-block">
    <div class="toc-vol-header">
      <a href="#vol-4" class="toc-vol-title">第四卷：组织提效与内控管理（第 131 - 180 条）</a>
      <span class="toc-vol-badge">50 条建议</span>
    </div>
    <div class="toc-module-grid">
      <a href="#item-131" class="toc-module-item">
        <span class="toc-mod-name">模块十二：财务、税务与内控合规</span>
        <span class="toc-mod-range">#131 - #142</span>
      </a>
      <a href="#item-143" class="toc-module-item">
        <span class="toc-mod-name">模块十三：HR、用工合规与劳动仲裁防御</span>
        <span class="toc-mod-range">#143 - #155</span>
      </a>
      <a href="#item-156" class="toc-module-item">
        <span class="toc-mod-name">模块十四：法务与合同审查红线库</span>
        <span class="toc-mod-range">#156 - #168</span>
      </a>
      <a href="#item-169" class="toc-module-item">
        <span class="toc-mod-name">模块十五：日常协同、立项三原则与组织考核</span>
        <span class="toc-mod-range">#169 - #180</span>
      </a>
    </div>
  </div>

  <!-- 第五卷 -->
  <div class="toc-volume-block">
    <div class="toc-vol-header">
      <a href="#vol-5" class="toc-vol-title">第五卷：实体产业深度落地（第 181 - 240 条）</a>
      <span class="toc-vol-badge">60 条建议</span>
    </div>
    <div class="toc-module-grid">
      <a href="#item-181" class="toc-module-item">
        <span class="toc-mod-name">模块十六：跨境电商与外贸出海</span>
        <span class="toc-mod-range">#181 - #195</span>
      </a>
      <a href="#item-196" class="toc-module-item">
        <span class="toc-mod-name">模块十七：传统零售与连锁门店</span>
        <span class="toc-mod-range">#196 - #210</span>
      </a>
      <a href="#item-211" class="toc-module-item">
        <span class="toc-mod-name">模块十八：离散制造与车间一线</span>
        <span class="toc-mod-range">#211 - #225</span>
      </a>
      <a href="#item-226" class="toc-module-item">
        <span class="toc-mod-name">模块十九：专业服务业（咨询、审计、律所）</span>
        <span class="toc-mod-range">#226 - #240</span>
      </a>
    </div>
  </div>

  <!-- 第六卷 -->
  <div class="toc-volume-block">
    <div class="toc-vol-header">
      <a href="#vol-6" class="toc-vol-title">第六卷：深水区高阶工程实战（第 241 - 340 条）</a>
      <span class="toc-vol-badge">100 条建议</span>
    </div>
    <div class="toc-module-grid">
      <a href="#item-241" class="toc-module-item">
        <span class="toc-mod-name">模块二十：模型底层吞吐量调优与并发架构</span>
        <span class="toc-mod-range">#241 - #275</span>
      </a>
      <a href="#item-276" class="toc-module-item">
        <span class="toc-mod-name">模块二十一：高阶企业智能体与业务状态机</span>
        <span class="toc-mod-range">#276 - #285</span>
      </a>
      <a href="#item-286" class="toc-module-item">
        <span class="toc-mod-name">模块二十二：大客户商业攻防与复杂博弈深水区</span>
        <span class="toc-mod-range">#286 - #300</span>
      </a>
      <a href="#item-301" class="toc-module-item">
        <span class="toc-mod-name">模块二十三：工业生产级长尾工程防御大绝学</span>
        <span class="toc-mod-range">#301 - #340</span>
      </a>
    </div>
  </div>

  <!-- 第七卷 -->
  <div class="toc-volume-block">
    <div class="toc-vol-header">
      <a href="#vol-7" class="toc-vol-title">第七卷：法务、裁员与出罪大结局（第 341 - 520 条）</a>
      <span class="toc-vol-badge">180 条建议</span>
    </div>
    <div class="toc-module-grid">
      <a href="#item-341" class="toc-module-item">
        <span class="toc-mod-name">模块二十四：劳动人事与组织优化生死合规</span>
        <span class="toc-mod-range">#341 - #380</span>
      </a>
      <a href="#item-381" class="toc-module-item">
        <span class="toc-mod-name">模块二十五：金税四期穿透与税务稽查刑事熔断</span>
        <span class="toc-mod-range">#381 - #430</span>
      </a>
      <a href="#item-431" class="toc-module-item">
        <span class="toc-mod-name">模块二十六：安全生产、环保风控与数据出境刑责防范</span>
        <span class="toc-mod-range">#431 - #475</span>
      </a>
      <a href="#item-476" class="toc-module-item">
        <span class="toc-mod-name">模块二十七：挂名法人脱钩出罪与债务责任隔离大绝学</span>
        <span class="toc-mod-range">#476 - #520</span>
      </a>
    </div>
  </div>

  <!-- 附录篇 -->
  <div class="toc-volume-block">
    <div class="toc-vol-header">
      <a href="#vol-8" class="toc-vol-title">附录篇：三大工业级工具表单与决策模板</a>
      <span class="toc-vol-badge">附录 · 实操底表</span>
    </div>
    <div class="toc-module-grid">
      <a href="#appendix-1" class="toc-module-item">
        <span class="toc-mod-name">附录一：自建 GPU 机房 vs 云端商业 API 5年全生命周期 TCO 对比清单</span>
        <span class="toc-mod-range">TCO 测算表</span>
      </a>
      <a href="#appendix-2" class="toc-module-item">
        <span class="toc-mod-name">附录二：生成式 AI 算法备案与安全评估全流程自查对照表（8大合规闭环）</span>
        <span class="toc-mod-range">自查对照表</span>
      </a>
      <a href="#appendix-3" class="toc-module-item">
        <span class="toc-mod-name">附录三：企业 AI 落地立项决策模板（含三维坐标准入与中止军令状）</span>
        <span class="toc-mod-range">军令状模板</span>
      </a>
    </div>
  </div>
</div>
"""

def compile_book():
    print("=" * 75)
    print("🚀 启动《高性价比企业 AI 落地指南》全书商业出版级 PDF 编译系统 (v3.0)...")
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
    toc_html = generate_toc_html()

    try:
        git_res = subprocess.run(["git", "rev-parse", "--short", "HEAD"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=ROOT_DIR)
        git_commit = git_res.stdout.strip() or "31da1c2"
    except Exception:
        git_commit = "31da1c2"

    from datetime import datetime
    build_time = datetime.now().strftime("%Y-%m-%d %H:%M")

    # 顶奢排版 CSS 样式
    full_html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>高性价比企业 AI 落地指南 - 昆仑增长 出品</title>
<style>
  @page {{
    size: A4;
    margin: 18mm 15mm 18mm 15mm;
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

  /* 苹果极简商务风封面 (Apple Minimalist Executive Cover) */
  .cover-page {{
    page-break-after: always;
    min-height: 92vh;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    background: #ffffff;
    color: #0f172a;
    padding: 20px 10px 10px 10px;
    box-sizing: border-box;
  }}
  .cover-top {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid #e2e8f0;
    padding-bottom: 16px;
  }}
  .cover-brand {{
    font-size: 10.5pt;
    font-weight: 800;
    letter-spacing: 2px;
    color: #0f172a;
    text-transform: uppercase;
  }}
  .cover-edition {{
    font-size: 8.5pt;
    font-weight: 600;
    color: #64748b;
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    padding: 3px 10px;
    border-radius: 4px;
  }}
  .cover-center {{
    padding: 40px 0 20px 0;
    text-align: left;
  }}
  .cover-tagline {{
    font-size: 8.5pt;
    font-weight: 700;
    color: #2563eb;
    letter-spacing: 3px;
    text-transform: uppercase;
    margin-bottom: 14px;
  }}
  .cover-title {{
    font-size: 34pt;
    font-weight: 900;
    color: #0f172a;
    letter-spacing: -1px;
    line-height: 1.15;
    margin: 0 0 10px 0;
  }}
  .cover-en-title {{
    font-size: 10.5pt;
    font-weight: 500;
    color: #64748b;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    margin-bottom: 22px;
  }}
  .cover-line {{
    width: 48px;
    height: 3px;
    background: #0f172a;
    margin: 0 0 24px 0;
  }}
  .cover-desc {{
    font-size: 11pt;
    line-height: 1.8;
    color: #334155;
    max-width: 680px;
    margin: 0 0 40px 0;
  }}
  .cover-specs-grid {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
  }}
  .spec-card {{
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 16px 12px;
    text-align: left;
    box-shadow: 0 1px 3px rgba(0,0,0,0.02);
  }}
  .spec-value {{
    font-size: 18pt;
    font-weight: 800;
    color: #0f172a;
    font-family: Consolas, -apple-system, sans-serif;
    line-height: 1;
    margin-bottom: 6px;
  }}
  .spec-unit {{
    font-size: 10pt;
    font-weight: 600;
    color: #2563eb;
    margin-left: 2px;
  }}
  .spec-label {{
    font-size: 8.5pt;
    font-weight: 700;
    color: #1e293b;
    margin-bottom: 3px;
  }}
  .spec-sub {{
    font-size: 7.5pt;
    color: #64748b;
  }}

  /* 封面版本与联系方式卡片 (对齐高端出版物标准) */
  .cover-meta-box {{
    margin-top: 26px;
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 12px 16px;
    text-align: center;
    font-size: 8.5pt;
    line-height: 1.6;
    color: #475569;
  }}
  .cover-meta-box .meta-line {{
    margin-bottom: 4px;
  }}
  .cover-meta-box .meta-line:last-child {{
    margin-bottom: 0;
  }}
  .cover-meta-box .meta-stamp {{
    font-size: 8pt;
    color: #64748b;
    border-bottom: 1px dashed #cbd5e1;
    padding-bottom: 6px;
    margin-bottom: 6px;
  }}
  .cover-meta-box .wechat-badge {{
    color: #0f172a;
    background: #e0f2fe;
    border: 1px solid #bae6fd;
    padding: 2px 8px;
    border-radius: 4px;
    font-family: Consolas, monospace;
    font-size: 9pt;
  }}
  .cover-link {{
    color: #2563eb;
    text-decoration: underline;
    font-weight: 600;
  }}
  .cover-link:hover {{
    color: #1d4ed8;
  }}

  .cover-footer {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-top: 1px solid #e2e8f0;
    padding-top: 16px;
    font-size: 8.5pt;
    color: #64748b;
  }}

  /* 总目录样式 (Apple 极简商务风) */
  .toc-container {{
    page-break-before: always;
    page-break-after: always;
    padding: 10px 0;
  }}
  .toc-header {{
    border-bottom: 2px solid #0f172a;
    padding-bottom: 14px;
    margin-bottom: 18px;
  }}
  .toc-tag {{
    font-size: 8pt;
    font-weight: 700;
    color: #64748b;
    letter-spacing: 2px;
    text-transform: uppercase;
    margin-bottom: 4px;
  }}
  .toc-main-title {{
    font-size: 19pt;
    font-weight: 800;
    color: #0f172a;
    letter-spacing: -0.5px;
    margin: 0 0 6px 0;
  }}
  .toc-lead {{
    font-size: 9pt;
    color: #64748b;
    margin: 0;
    line-height: 1.5;
  }}
  .toc-volume-block {{
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    padding: 10px 14px;
    margin-bottom: 10px;
    page-break-inside: avoid;
  }}
  .toc-vol-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid #f1f5f9;
    padding-bottom: 6px;
    margin-bottom: 8px;
  }}
  .toc-vol-title {{
    font-size: 10pt;
    font-weight: 700;
    color: #0f172a;
    text-decoration: none;
  }}
  .toc-vol-title:hover {{
    color: #2563eb;
  }}
  .toc-vol-badge {{
    font-size: 7.5pt;
    font-weight: 600;
    color: #475569;
    background: #f1f5f9;
    padding: 2px 6px;
    border-radius: 4px;
  }}
  .toc-module-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 6px;
  }}
  .toc-module-item {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 4px;
    padding: 5px 8px;
    text-decoration: none;
    transition: all 0.15s ease;
  }}
  .toc-module-item:hover {{
    background: #eff6ff;
    border-color: #bfdbfe;
  }}
  .toc-mod-name {{
    font-size: 8pt;
    color: #1e293b;
    font-weight: 500;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }}
  .toc-mod-range {{
    font-size: 7.5pt;
    font-weight: 700;
    color: #2563eb;
    font-family: Consolas, monospace;
    margin-left: 6px;
    flex-shrink: 0;
  }}
  .highlight-toc-item {{
    background: #eff6ff;
    border-color: #93c5fd;
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
    font-size: 13pt;
    font-weight: 700;
    color: #1e3a8a;
    background: #f0fdf4;
    border-left: 5px solid #16a34a;
    padding: 8px 14px;
    margin-top: 30px;
    margin-bottom: 20px;
    border-radius: 0 6px 6px 0;
  }}

  /* 小节标题 (用于附录与序言子标题) */
  .section-subhead {{
    font-size: 11pt;
    font-weight: 700;
    color: #1e293b;
    border-left: 4px solid #2563eb;
    padding-left: 10px;
    margin-top: 24px;
    margin-bottom: 14px;
  }}
  .section-subhead-4 {{
    font-size: 10pt;
    font-weight: 600;
    color: #334155;
    margin-top: 16px;
    margin-bottom: 8px;
  }}

  /* 表格排版 (速查表/附录表) */
  .table-container {{
    width: 100%;
    margin: 16px 0 24px 0;
    overflow-x: auto;
    page-break-inside: auto;
  }}
  .data-table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 8.5pt;
    line-height: 1.45;
    background: #ffffff;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    border: 1px solid #cbd5e1;
    border-radius: 4px;
  }}
  .data-table th {{
    background: #1e293b;
    color: #ffffff;
    font-weight: 700;
    padding: 8px 10px;
    text-align: left;
    border: 1px solid #334155;
    font-size: 8.5pt;
    white-space: nowrap;
  }}
  .data-table td {{
    padding: 7px 10px;
    border: 1px solid #e2e8f0;
    color: #334155;
    vertical-align: top;
  }}
  .data-table tr:nth-child(even) {{
    background: #f8fafc;
  }}
  .data-table tr:hover {{
    background: #f1f5f9;
  }}

  /* 代码块与模板 */
  pre {{
    background: #0f172a;
    color: #e2e8f0;
    padding: 12px 16px;
    border-radius: 6px;
    font-size: 8pt;
    line-height: 1.45;
    overflow-x: auto;
    font-family: Consolas, "Courier New", monospace;
    page-break-inside: avoid;
    margin: 14px 0;
  }}
  code {{
    font-family: Consolas, "Courier New", monospace;
    font-size: 8.5pt;
  }}

  /* 超链接样式与直达跳转 */
  a.doc-link {{
    color: #2563eb;
    text-decoration: none;
    font-weight: 600;
    border-bottom: 1px dotted #2563eb;
    padding-bottom: 1px;
    transition: color 0.2s;
  }}
  a.doc-link:hover {{
    color: #1d4ed8;
    border-bottom: 1px solid #1d4ed8;
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
    scroll-margin-top: 30px;
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
      height: auto;
      min-height: 90vh;
    }}
    .entry-card {{
      box-shadow: none;
      border: 1px solid #cbd5e1;
    }}
    .data-table th {{
      background: #334155 !important;
      -webkit-print-color-adjust: exact;
    }}
    .data-table tr:nth-child(even) {{
      background: #f8fafc !important;
      -webkit-print-color-adjust: exact;
    }}
  }}
</style>
</head>
<body>

<!-- 商业出版封面 (Apple 极简商务风) -->
<div class="cover-page">
  <div class="cover-top">
    <div class="cover-brand">KUNLUN GROWTH · 昆仑增长 出品</div>
    <div class="cover-edition">2026 商业实战典藏版 · 企业落地内参</div>
  </div>

  <div class="cover-center">
    <div class="cover-tagline">EXECUTIVE AI IMPLEMENTATION HANDBOOK</div>
    <h1 class="cover-title">高性价比企业 AI 落地指南</h1>
    <div class="cover-en-title">How to Adopt Enterprise AI with High Cost-Effectiveness</div>
    <div class="cover-line"></div>
    <p class="cover-desc">
      拒绝 PPT 泡沫与技术炫技，专注法条、代码、算力账单与真实毛利。<br>
      全书 520 条工业级建议 · 独创六段论实战模型 · 严防破产与身家倾覆。
    </p>

    <!-- 苹果风 4 大核心参数卡片 -->
    <div class="cover-specs-grid">
      <div class="spec-card">
        <div class="spec-value">520<span class="spec-unit">条</span></div>
        <div class="spec-label">全量工业级建议</div>
        <div class="spec-sub">绝不跳号 · 绝不注水</div>
      </div>
      <div class="spec-card">
        <div class="spec-value">4<span class="spec-unit">维</span></div>
        <div class="spec-label">全方位量化收益</div>
        <div class="spec-sub">金钱 · 时间 · 寿命 · 自由</div>
      </div>
      <div class="spec-card">
        <div class="spec-value">A/B/C<span class="spec-unit">级</span></div>
        <div class="spec-label">顶格法条证据链</div>
        <div class="spec-sub">现行法律 · 顶会学术论文</div>
      </div>
      <div class="spec-card">
        <div class="spec-value">5<span class="spec-unit">年</span></div>
        <div class="spec-label">全周期 TCO 测算</div>
        <div class="spec-sub">自建机房 vs 商业 API 对比</div>
      </div>
    </div>

    <!-- 实时版本、在线直达与编著者微信联系方式 (MarshallPD) -->
    <div class="cover-meta-box">
      <div class="meta-line meta-stamp">生成于 {build_time} (北京时间) · 正文提交 <strong>{git_commit}</strong></div>
      <div class="meta-line">💬 编著者微信：<strong class="wechat-badge">MarshallPD</strong>（商业咨询 · 技术交流 · 方案落地）</div>
      <div class="meta-line">正文每天都在持续迭代，以在线版为准：<a href="https://github.com/AIMarshallLee/kunlun-ai-handbook" class="cover-link">https://github.com/AIMarshallLee/kunlun-ai-handbook</a></div>
      <div class="meta-line">在线检索、配套工具与本 PDF 的最新下载都在 <a href="https://github.com/AIMarshallLee/kunlun-ai-handbook/tree/main/docs" class="cover-link">https://github.com/AIMarshallLee/kunlun-ai-handbook/tree/main/docs</a></div>
    </div>
  </div>

  <div class="cover-footer">
    <div class="cover-meta-left">
      <strong>编著团队：</strong>昆仑增长 数字化咨询团队 · 联系微信：<strong>MarshallPD</strong>
    </div>
    <div class="cover-meta-right">
      <strong>开源许可：</strong>基于 CC BY-NC-SA 4.0 协议发布（自用免费 · 严禁商用）
    </div>
  </div>
</div>

<!-- 全书架构与总目录导航 -->
{toc_html}

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
