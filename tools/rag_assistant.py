#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
昆仑增长：企业 AI 落地指南——本地工业级知识库检索与决策军师 (RAG Assistant 2.0)
支持中文自然语言整句提问、双模式（命令行参数 / 交互式对话终端）、语义分词与法条精确检索。
"""

import os
import re
import sys

DOCS_DIR = os.path.join(os.path.dirname(__file__), "..", "docs")

# 常见中文无意义停用词
STOP_WORDS = {
    "的", "了", "和", "是", "就", "都", "而", "及", "与", "着", "或", "一个",
    "没有", "我们", "你们", "他们", "这个", "那个", "怎么", "如何", "怎样",
    "什么", "哪些", "可以", "能够", "应该", "要想", "如果", "但是", "因为", "所以",
    "一下", "一些", "有些", "为了", "关于", "对于", "以及", "并且", "还是"
}

def extract_keywords(text):
    """
    智能提取用户输入中的核心实词（结合英文词、预分词与滑动 2~4 元分词）
    """
    cleaned = text.strip()
    # 提取英文单词/专有名词 (如 RAG, SQL, Token, FSM)
    en_words = re.findall(r'[a-zA-Z0-9_\-]+', cleaned)
    
    # 中文字符切分
    cn_text = re.sub(r'[^\u4e00-\u9fa5]', ' ', cleaned)
    cn_chunks = [c.strip() for c in cn_text.split() if c.strip()]
    
    keywords = set([w.lower() for w in en_words if len(w) > 1])
    
    # 对中文块生成 2-gram, 3-gram 和 4-gram
    for chunk in cn_chunks:
        if len(chunk) <= 4:
            if chunk not in STOP_WORDS and len(chunk) >= 2:
                keywords.add(chunk)
        else:
            # 滑动生成候选词
            for n in [2, 3, 4]:
                for i in range(len(chunk) - n + 1):
                    ngram = chunk[i:i+n]
                    if ngram not in STOP_WORDS:
                        keywords.add(ngram)
                        
    return list(keywords)

def load_all_entries():
    """
    加载 docs/ 目录下所有分卷的结构化条目
    """
    entries = []
    if not os.path.exists(DOCS_DIR):
        return entries

    entry_pattern = re.compile(
        r"###\s+(\d+)\.\s+([^\n]+)(.*?)(?=(?:###\s+\d+\.)|\Z)",
        re.DOTALL
    )

    for filename in sorted(os.listdir(DOCS_DIR)):
        if not filename.endswith(".md"):
            continue
        filepath = os.path.join(DOCS_DIR, filename)
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        matches = entry_pattern.findall(content)
        for num, title, body in matches:
            full_text = f"### {num}. {title}\n{body}"
            # 提取证据等级与法条来源
            level_m = re.search(r"-\s+\*\*证据等级\*\*[：:]\s*([^\n]+)", body)
            source_m = re.search(r"-\s+\*\*来源\*\*[：:]\s*([^\n]+)", body)
            say_human_m = re.search(r"-\s+\*\*说人话\*\*[：:]\s*([^\n]+)", body)
            
            entries.append({
                "num": int(num),
                "num_str": num,
                "title": title.strip(),
                "body": body.strip(),
                "file": filename,
                "full_text": full_text,
                "level": level_m.group(1).strip() if level_m else "未标注",
                "source": source_m.group(1).strip() if source_m else "实战工业标准",
                "say_human": say_human_m.group(1).strip() if say_human_m else ""
            })
    return entries

def search_entries(query, top_k=3, all_entries=None):
    """
    执行加权语义检索并呈现决策建议
    """
    if all_entries is None:
        all_entries = load_all_entries()

    if not all_entries:
        print("❌ 未在 docs 目录下找到条目文件，请确认文档路径。")
        return []

    # 优先检查是否直接查询数字编号（如 '341' 或 '#341'）
    num_match = re.search(r'\b(\d{1,3})\b', query)
    if num_match:
        target_num = int(num_match.group(1))
        matched_exact = [e for e in all_entries if e['num'] == target_num]
        if matched_exact:
            print("\n" + "=" * 78)
            print(f"🎯 精确命中条目编号: 第 {target_num} 条")
            print("=" * 78)
            _render_entry(1, 999, matched_exact[0])
            return matched_exact

    keywords = extract_keywords(query)
    # 如果自然分词为空，退化为按空格分词
    if not keywords:
        keywords = [k.strip().lower() for k in query.split() if k.strip()]

    if not keywords:
        print("⚠️ 请输入有效的检索问题或关键词。")
        return []

    scored_entries = []
    for item in all_entries:
        score = 0
        title_lower = item['title'].lower()
        body_lower = item['body'].lower()
        file_lower = item['file'].lower()

        for kw in keywords:
            # 标题完全包含关键词（权重极高）
            if kw in title_lower:
                score += 15
            # 说人话部分命中（核心人话提炼）
            if kw in item['say_human'].lower():
                score += 8
            # 法规/来源/备注命中
            if kw in item['source'].lower():
                score += 6
            # 正文词频匹配
            count_in_body = body_lower.count(kw)
            if count_in_body > 0:
                score += min(count_in_body * 2, 10)
            # 编号字符串匹配
            if kw == str(item['num']):
                score += 50

        if score > 0:
            scored_entries.append((score, item))

    scored_entries.sort(key=lambda x: x[0], reverse=True)

    print("\n" + "=" * 78)
    print(f"🔍 检索提问: 【{query}】")
    print(f"📊 提取关键词: [{', '.join(keywords[:8])}] | 命中相关条目数: {len(scored_entries)} 条")
    print("=" * 78)

    if not scored_entries:
        print("❌ 未检索到直接相关条目。建议更换关键词（如：裁员、发票、算力、Prompt、出罪、合规、高新）。")
        return []

    top_results = scored_entries[:top_k]
    for rank, (score, item) in enumerate(top_results, 1):
        _render_entry(rank, score, item)

    return [item for _, item in top_results]

def _render_entry(rank, score, item):
    badge = f"[{item['level']}]" if "级" in item['level'] else f"[{item['level']} 级]"
    print(f"\n[建议 {rank}] (置信度得分: {score} | 评级: {badge} | 来源卷: {item['file']})")
    print(f"👉 动作核心：### {item['num']}. {item['title']}")
    print("-" * 78)
    
    # 结构化抽取各段落
    lines = [l.strip() for l in item['body'].split("\n") if l.strip()]
    for line in lines:
        if line.startswith("- **成本**："):
            print(f"  💰 成本代价: {line.replace('- **成本**：', '')}")
        elif line.startswith("- **说人话**："):
            print(f"  🗣️ 白话释义: {line.replace('- **说人话**：', '')}")
        elif line.startswith("- **证据等级**："):
            print(f"  ⚖️ 证据标准: {line.replace('- **证据等级**：', '')}")
        elif line.startswith("- **来源**："):
            print(f"  📜 法条/来源: {line.replace('- **来源**：', '')}")
        elif line.startswith("- **备注**："):
            print(f"  💡 实战避坑: {line.replace('- **备注**：', '')}")
            
    print("-" * 78)

def interactive_repl():
    """
    启动交互式终端咨询军师
    """
    all_entries = load_all_entries()
    print("=" * 78)
    print("🥋 昆仑增长 · 《高性价比企业 AI 落地指南》本地 RAG 决策军师 (v2.0)")
    print(f"📚 已加载全书 8 大分卷，共 {len(all_entries)} 条工业级实战建议 (第 001 - 520 条)")
    print("💡 使用贴士:")
    print("   1. 支持输入任意业务/法务痛点（如: 老板想裁员怎么防翻车 / 研发费加计扣除工时怎么做）")
    print("   2. 支持直接输入建议编号（如: 341 / 520）直达对应决策条款")
    print("   3. 输入 ':top 5' 可调整展示前 5 条结果")
    print("   4. 输入 'q' 或 'exit' 退出军师")
    print("=" * 78)

    top_k = 3
    while True:
        try:
            prompt = input(f"\n[AI 军师 (Top-{top_k})]> ").strip()
            if not prompt:
                continue
            if prompt.lower() in ["q", "quit", "exit"]:
                print("👋 祝您商业基业长青，合规稳健增长！再见！")
                break
            if prompt.startswith(":top"):
                parts = prompt.split()
                if len(parts) > 1 and parts[1].isdigit():
                    top_k = int(parts[1])
                    print(f"✅ 已将召回结果数调整为: Top-{top_k}")
                continue

            search_entries(prompt, top_k=top_k, all_entries=all_entries)
        except (KeyboardInterrupt, EOFError):
            print("\n👋 军师已退出。")
            break

if __name__ == "__main__":
    if len(sys.argv) > 1:
        query_text = " ".join(sys.argv[1:])
        search_entries(query_text)
    else:
        interactive_repl()
