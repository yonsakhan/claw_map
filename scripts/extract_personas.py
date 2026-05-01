"""批量 persona 提取脚本 — 对采集到的 JSON profiles 跑 LLM 分析。

用法：
    python -m scripts.extract_personas                           # 处理所有 JSON 文件
    python -m scripts.extract_personas --input data/profiles/xxx.json  # 指定文件
    python -m scripts.extract_personas --limit 10                # 只处理前 10 条
"""

import argparse
import glob
import json
import logging
import os
import time

from src.analysis.persona_extractor import PersonaExtractor

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("ExtractPersonas")

OUTPUT_DIR = "data/personas"


def load_profiles(input_path: str | None, limit: int | None) -> list[dict]:
    """加载所有 profile JSON 文件。"""
    if input_path:
        files = [input_path]
    else:
        files = sorted(glob.glob("data/profiles/*.json"))

    profiles = []
    for f in files:
        with open(f, encoding="utf-8") as fh:
            data = json.load(fh)
            profiles.extend(data)

    if limit:
        profiles = profiles[:limit]

    return profiles


def main():
    parser = argparse.ArgumentParser(description="批量 persona 提取")
    parser.add_argument("--input", type=str, default=None, help="指定 JSON 文件路径")
    parser.add_argument("--limit", type=int, default=None, help="只处理前 N 条")
    args = parser.parse_args()

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    profiles = load_profiles(args.input, args.limit)
    logger.info("加载了 %d 条 profile", len(profiles))

    if not profiles:
        logger.warning("没有找到 profile 数据")
        return

    extractor = PersonaExtractor()
    results = []
    errors = 0

    for i, p in enumerate(profiles):
        name = p.get("display_name", "?")
        logger.info("[%d/%d] %s", i + 1, len(profiles), name)

        profile = {k: v for k, v in p.items() if k != "posts"}
        posts = p.get("posts", [])

        try:
            persona = extractor.extract_persona(profile, posts)
            persona["source_profile"] = profile
            persona["post_count"] = len(posts)
            results.append(persona)
            logger.info("  OK: age=%s fertility=%s score=%s",
                        persona.get("age_group", "?"),
                        persona.get("fertility_status", "?"),
                        persona.get("fertility_intent_score", "?"))
        except Exception as e:
            errors += 1
            logger.error("  失败: %s", e)

    # 保存结果
    output_path = os.path.join(OUTPUT_DIR, f"personas_{time.strftime('%Y%m%d_%H%M%S')}.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # 统计
    print("\n" + "=" * 50)
    print(f"提取完成！成功 {len(results)}/{len(profiles)}，失败 {errors}")
    print(f"结果保存到: {output_path}")

    # 汇总统计
    age_groups = {}
    fertility = {}
    scores = []
    locations = []
    for r in results:
        ag = r.get("age_group", "Unknown")
        age_groups[ag] = age_groups.get(ag, 0) + 1
        fs = r.get("fertility_status", "Unknown")
        fertility[fs] = fertility.get(fs, 0) + 1
        score = r.get("fertility_intent_score")
        if isinstance(score, (int, float)):
            scores.append(score)
        loc = r.get("location", "")
        if loc:
            locations.append(loc)

    print(f"\n年龄分布: {age_groups}")
    print(f"生育状态: {fertility}")
    if scores:
        print(f"生育意愿均分: {sum(scores)/len(scores):.1f} (0-5)")
    print(f"地域分布: {locations}")


if __name__ == "__main__":
    main()
