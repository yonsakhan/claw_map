"""Persona 汇总分析 — 生成统计报告。

用法：
    python -m scripts.analyze_personas
    python -m scripts.analyze_personas --input data/personas/xxx.json
"""

import argparse
import json
import os
import time
from collections import Counter, defaultdict


def load_personas(path: str | None) -> list[dict]:
    if path:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    import glob
    files = sorted(glob.glob("data/personas/personas_*.json"))
    if not files:
        print("未找到 persona 数据")
        return []
    with open(files[-1], encoding="utf-8") as f:
        return json.load(f)


def safe_str(v, default="Unknown"):
    if not v or v == "Unknown" or v == "null":
        return default
    return str(v).strip()


def safe_int(v, default=0):
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def normalize_age(raw: str) -> str:
    """统一年龄分组。"""
    raw = safe_str(raw)
    if raw == "Unknown":
        return "Unknown"
    if raw in ("18-24", "18岁以下"):
        return "18-24"
    if raw in ("25-29",):
        return "25-29"
    if raw in ("30-34",):
        return "30-34"
    if raw in ("35-39",):
        return "35-39"
    if raw in ("40+", "40+岁", "40-49", "50+"):
        return "40+"
    # 尝试提取数字
    import re
    m = re.search(r"(\d+)", raw)
    if m:
        age = int(m.group(1))
        if age < 25: return "18-24"
        if age < 30: return "25-29"
        if age < 35: return "30-34"
        if age < 40: return "35-39"
        return "40+"
    if "90" in raw: return "25-29"
    if "80" in raw: return "35-39"
    if "Parent" in raw: return "30-34"
    return "Unknown"


def normalize_fertility(raw: str) -> str:
    """统一生育状态。"""
    raw = safe_str(raw)
    if raw == "Unknown":
        return "Unknown"
    if "备孕" in raw:
        return "备孕中"
    if "怀孕" in raw or "孕中" in raw:
        return "怀孕中"
    if "2孩" in raw or "二孩" in raw or "两孩" in raw:
        return "已育2孩+"
    if "1孩" in raw or "一孩" in raw or "Parent" in raw:
        return "已育1孩"
    if "未婚" in raw or "单身" in raw or "Unmarried" in raw:
        return "未婚"
    if "已婚" in raw and ("未育" in raw or "No" in raw):
        return "已婚未育"
    if "Married" in raw:
        return "已婚未育"
    return raw


def normalize_location(raw: str) -> str:
    """统一地域。"""
    raw = safe_str(raw)
    if raw in ("Unknown", "中国", "null"):
        return "Unknown"
    # 提取省份
    provinces = ["广东", "浙江", "北京", "上海", "四川", "重庆", "江苏", "福建",
                 "湖南", "湖北", "河南", "河北", "山东", "辽宁", "天津", "贵州",
                 "广西", "江西", "安徽", "黑龙江", "山西", "陕西", "云南", "海南",
                 "吉林", "甘肃", "内蒙古", "新疆", "西藏", "宁夏", "青海", "香港", "澳门", "台湾"]
    for p in provinces:
        if p in raw:
            return p
    if "美国" in raw or "Japan" in raw or "日本" in raw or "印尼" in raw or "关岛" in raw:
        return "海外"
    return raw


def generate_report(personas: list[dict]) -> str:
    lines = []
    lines.append("=" * 60)
    lines.append("小红书用户 Persona 分析报告")
    lines.append(f"样本量: {len(personas)}")
    lines.append(f"生成时间: {time.strftime('%Y-%m-%d %H:%M')}")
    lines.append("=" * 60)

    # 1. 年龄分布
    age_counter = Counter()
    for p in personas:
        age_counter[normalize_age(p.get("age_group", ""))] += 1
    lines.append("\n## 1. 年龄分布")
    for k in ["18-24", "25-29", "30-34", "35-39", "40+", "Unknown"]:
        v = age_counter.get(k, 0)
        if v:
            pct = 100 * v / len(personas)
            bar = "█" * int(pct / 2)
            lines.append(f"  {k:8s} {v:4d} ({pct:5.1f}%) {bar}")

    # 2. 生育状态分布
    fert_counter = Counter()
    for p in personas:
        fert_counter[normalize_fertility(p.get("fertility_status", ""))] += 1
    lines.append("\n## 2. 生育状态分布")
    order = ["备孕中", "怀孕中", "已婚未育", "已育1孩", "已育2孩+", "未婚", "Unknown"]
    for k in order:
        v = fert_counter.get(k, 0)
        if v:
            pct = 100 * v / len(personas)
            bar = "█" * int(pct / 2)
            lines.append(f"  {k:10s} {v:4d} ({pct:5.1f}%) {bar}")

    # 3. 年龄×生育状态交叉表
    lines.append("\n## 3. 年龄 × 生育状态 交叉表")
    cross = defaultdict(lambda: defaultdict(int))
    for p in personas:
        age = normalize_age(p.get("age_group", ""))
        fert = normalize_fertility(p.get("fertility_status", ""))
        cross[age][fert] += 1

    fert_cols = ["备孕中", "怀孕中", "已婚未育", "已育1孩", "已育2孩+", "未婚"]
    header = f"  {'年龄':8s}" + "".join(f"{c:>8s}" for c in fert_cols)
    lines.append(header)
    lines.append("  " + "-" * (8 + 8 * len(fert_cols)))
    for age in ["18-24", "25-29", "30-34", "35-39", "40+"]:
        row = f"  {age:8s}"
        for fc in fert_cols:
            v = cross[age].get(fc, 0)
            row += f"{v:>8d}" if v else "       -"
        lines.append(row)

    # 4. 生育意愿
    scores = [safe_int(p.get("fertility_intent_score")) for p in personas if safe_int(p.get("fertility_intent_score")) > 0]
    lines.append("\n## 4. 生育意愿评分 (0-5)")
    if scores:
        lines.append(f"  均分: {sum(scores)/len(scores):.2f}")
        lines.append(f"  中位数: {sorted(scores)[len(scores)//2]}")
        lines.append(f"  有效样本: {len(scores)}/{len(personas)}")
        score_dist = Counter(scores)
        for s in range(6):
            v = score_dist.get(s, 0)
            if v:
                pct = 100 * v / len(scores)
                bar = "█" * int(pct / 2)
                lines.append(f"  {s}分: {v:4d} ({pct:5.1f}%) {bar}")

    # 5. 地域分布
    loc_counter = Counter()
    for p in personas:
        loc_counter[normalize_location(p.get("location", ""))] += 1
    lines.append("\n## 5. 地域分布 (Top 15)")
    for k, v in loc_counter.most_common(15):
        pct = 100 * v / len(personas)
        bar = "█" * int(pct / 2)
        lines.append(f"  {k:8s} {v:4d} ({pct:5.1f}%) {bar}")

    # 6. 空间偏好
    spatial_counter = Counter()
    for p in personas:
        prefs = p.get("spatial_preferences", [])
        if isinstance(prefs, list):
            for sp in prefs:
                sp = safe_str(sp)
                if sp != "Unknown":
                    spatial_counter[sp] += 1
    lines.append("\n## 6. 空间偏好关键词 (Top 20)")
    for k, v in spatial_counter.most_common(20):
        lines.append(f"  {k}: {v}")

    # 7. 按搜索关键词的分布
    kw_counter = Counter()
    for p in personas:
        src = p.get("source_profile", {})
        kw = src.get("search_keyword", "") if isinstance(src, dict) else ""
        if kw:
            for k in kw.split(","):
                k = k.strip()
                if k:
                    kw_counter[k] += 1
    if kw_counter:
        lines.append("\n## 7. 搜索关键词分布")
        for k, v in kw_counter.most_common():
            lines.append(f"  {k}: {v}")

    # 8. 数据质量
    lines.append("\n## 8. 数据质量")
    known_age = sum(1 for p in personas if normalize_age(p.get("age_group", "")) != "Unknown")
    known_fert = sum(1 for p in personas if normalize_fertility(p.get("fertility_status", "")) != "Unknown")
    known_loc = sum(1 for p in personas if normalize_location(p.get("location", "")) != "Unknown")
    lines.append(f"  年龄已知: {known_age}/{len(personas)} ({100*known_age/len(personas):.0f}%)")
    lines.append(f"  生育状态已知: {known_fert}/{len(personas)} ({100*known_fert/len(personas):.0f}%)")
    lines.append(f"  地域已知: {known_loc}/{len(personas)} ({100*known_loc/len(personas):.0f}%)")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Persona 汇总分析")
    parser.add_argument("--input", type=str, default=None, help="指定 persona JSON 文件")
    args = parser.parse_args()

    personas = load_personas(args.input)
    if not personas:
        return

    report = generate_report(personas)
    print(report)

    # 保存报告
    os.makedirs("data/reports", exist_ok=True)
    report_path = f"data/reports/report_{time.strftime('%Y%m%d_%H%M%S')}.txt"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"\n报告已保存到: {report_path}")


if __name__ == "__main__":
    main()
