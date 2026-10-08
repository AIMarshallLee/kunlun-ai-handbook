#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
昆仑增长：企业自建 GPU 机房 vs 云端商业 API 5年全生命周期 TCO 精密对比计算器
用于辅助企业 CEO、CFO、CTO 在立项前进行理性量化决策。
"""

import sys

def calculate_tco(
    gpu_server_count=2,
    cards_per_server=8,
    single_server_price_wan=120.0,
    network_storage_wan=35.0,
    pdu_ups_wan=15.0,
    cabinet_rent_year_wan=6.0,
    power_kwh_cost=1.0,
    kw_per_server=10.2,
    dedicated_line_year_wan=3.6,
    maint_sla_5year_wan=20.0,
    ops_salary_year_wan=30.0,
    retrain_finetune_wan=25.0,
    daily_tokens_million=10.0,
    api_price_per_million_tokens=2.0,
    hardware_deprecation_reserve_wan=80.0
):
    print("=" * 70)
    print("      昆仑增长：企业自建 GPU 机房 vs 云端商业 API 5年 TCO 测算模型")
    print("=" * 70)

    # 1. 自建机房 CapEx (资本性支出)
    hardware_capex = gpu_server_count * single_server_price_wan
    total_capex = hardware_capex + network_storage_wan + pdu_ups_wan

    # 2. 自建机房 OpEx (5年运营支出)
    # 电力计算：单台千瓦 * 台数 * 24小时 * 365天 * 5年 * 电价
    total_kwh_5yr = kw_per_server * gpu_server_count * 24 * 365 * 5
    power_cost_5yr_wan = (total_kwh_5yr * power_kwh_cost) / 10000.0

    cabinet_cost_5yr_wan = cabinet_rent_year_wan * 5
    network_cost_5yr_wan = dedicated_line_year_wan * 5
    total_opex = cabinet_cost_5yr_wan + power_cost_5yr_wan + network_cost_5yr_wan + maint_sla_5year_wan

    # 3. 人资成本 (5年)
    hr_cost_5yr_wan = ops_salary_year_wan * 5

    # 4. 技术债与资产折旧准备
    tech_debt_wan = retrain_finetune_wan + hardware_deprecation_reserve_wan

    # 自建 5 年总 TCO
    on_premise_total_tco = total_capex + total_opex + hr_cost_5yr_wan + tech_debt_wan

    # 5. 云端商业 API 方案 (5年)
    # 日均 Token 数 * 365 * 5 * 单价
    total_tokens_5yr_million = daily_tokens_million * 365 * 5
    api_cost_5yr_wan = (total_tokens_5yr_million * api_price_per_million_tokens) / 10000.0
    cloud_api_total_tco = api_cost_5yr_wan

    # 打印对比报表
    print(f"\n【测算场景假设】")
    print(f"- 业务日均消耗 Token：{daily_tokens_million:.1f} 百万 Token (年均约 {daily_tokens_million*365/100:.1f} 亿 Token)")
    print(f"- 自建规格：{gpu_server_count} 台服务器，共计 {gpu_server_count * cards_per_server} 卡高密度集群")
    print(f"- 云端 API 综合单价：{api_price_per_million_tokens:.2f} 元 / 百万 Token (含缓存折扣)")

    print("\n" + "-" * 70)
    print(f"{'成本细分子项':<30} | {'自建私有化机房 (万元)':<18} | {'云端商业 API (万元)':<15}")
    print("-" * 70)
    print(f"{'硬件资本支出 (CapEx)':<30} | {total_capex:<20.2f} | {0.0:<15.2f}")
    print(f"{'5年机柜租金与网络专线':<30} | {(cabinet_cost_5yr_wan + network_cost_5yr_wan):<20.2f} | {0.0:<15.2f}")
    print(f"{'5年 PUE 电力能耗支出':<30} | {power_cost_5yr_wan:<20.2f} | {0.0:<15.2f}")
    print(f"{'5年专职运维人资支出 (HR)':<30} | {hr_cost_5yr_wan:<20.2f} | {0.0:<15.2f}")
    print(f"{'5年硬件维保与技术代差折旧':<30} | {(maint_sla_5year_wan + tech_debt_wan):<20.2f} | {0.0:<15.2f}")
    print(f"{'5年实际业务 API 调用支出':<30} | {0.0:<20.2f} | {cloud_api_total_tco:<15.2f}")
    print("-" * 70)
    print(f"{'5年全生命周期 TCO 总计':<30} | {on_premise_total_tco:<20.2f} | {cloud_api_total_tco:<15.2f}")
    print("=" * 70)

    ratio = on_premise_total_tco / max(cloud_api_total_tco, 0.01)
    diff_wan = on_premise_total_tco - cloud_api_total_tco

    print(f"\n【财务决策结论】")
    if on_premise_total_tco > cloud_api_total_tco:
        print(f"⚠️  警告：自建私有化算力的 5年 TCO 是云端商业 API 的 【{ratio:.1f} 倍】！")
        print(f"👉 采用云端方案 5 年内可为企业直接省下现金流净支出：【{diff_wan:.2f} 万元】。")
        print(f"💡 决策建议：若无绝密军工合规硬性隔离要求，坚决【否决自建机房方案】，采用云端 API 模式！")
    else:
        print(f"✅ 结论：当前业务 Token 吞吐极大，自建机房方案在经济学上已具备边际效益。")
    print("=" * 70)

if __name__ == "__main__":
    calculate_tco()
