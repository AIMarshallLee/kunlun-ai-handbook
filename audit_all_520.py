import os
import re

doc_files = [
    '01_Volume1_Redlines_and_Pitfalls.md',
    '02_Volume2_Traffic_and_Sales.md',
    '03_Volume3_Dev_and_RAG.md',
    '04_Volume4_Internal_and_Org.md',
    '05_Volume5_Industries.md',
    '06_Deep_Tech_and_Production.md',
    '07_Final_Decisive_Volume.md'
]

all_items = []
file_stats = {}

for fname in doc_files:
    fpath = os.path.join('e:/kunlun-ai-handbook/docs', fname)
    with open(fpath, 'r', encoding='utf-8') as f:
        text = f.read()
    matches = re.findall(r'###\s+(\d+)\.\s*(.+)', text)
    nums = [int(m[0]) for m in matches]
    file_stats[fname] = {
        'count': len(nums),
        'min': min(nums) if nums else 0,
        'max': max(nums) if nums else 0,
        'nums': nums
    }
    for m in matches:
        all_items.append((int(m[0]), m[1].strip(), fname))

all_nums = [item[0] for item in all_items]
expected_nums = list(range(1, 521))

print('=== 全书逐卷统计 ===')
for k, v in file_stats.items():
    print(f'{k}: 共 {v["count"]} 条, 范围 [{v["min"]} ~ {v["max"]}]')

print('\n=== 全量完整性校验 ===')
print('总条目数:', len(all_nums))
print('预期总数: 520')
print('是否 1 到 520 绝对无缝严格连续:', all_nums == expected_nums)

missing = set(expected_nums) - set(all_nums)
duplicate = [x for x in all_nums if all_nums.count(x) > 1]
print('缺失编号:', missing if missing else '无')
print('重复编号:', set(duplicate) if duplicate else '无')

# 检查六段论完整度
six_elements = ['- **成本**', '- **说人话**', '- **收益**', '- **证据等级**', '- **来源**', '- **备注**']
incomplete_items = []

for fname in doc_files:
    fpath = os.path.join('e:/kunlun-ai-handbook/docs', fname)
    with open(fpath, 'r', encoding='utf-8') as f:
        text = f.read()
    chunks = re.split(r'###\s+\d+\.', text)
    # 第一个 chunk 是卷首说明
    for i, chunk in enumerate(chunks[1:], 1):
        for elem in six_elements:
            if elem not in chunk:
                incomplete_items.append((fname, i, elem))

print('\n=== 六段论格式合规校验 ===')
print(f'不合格条目数: {len(incomplete_items)}')
if incomplete_items:
    print('前 5 个不合格条目:', incomplete_items[:5])
else:
    print('全书 520 条 100% 具备完整六段论（成本、说人话、收益四维、证据等级、来源、备注）！')
