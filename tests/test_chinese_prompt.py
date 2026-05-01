#!/usr/bin/env python3
"""
测试中文 Prompt 效果
用法：python -m tests.test_chinese_prompt
"""

import json
import asyncio
from src.analysis.persona_extractor import PersonaExtractor
from src.analysis.account_feature_profile import AccountFeatureBuilder


# 模拟小红书用户数据
MOCK_PROFILE = {
    "id": "test_user_001",
    "display_name": "备孕小助手",
    "bio": "90后备孕中 | 分享备孕日常 | 期待小生命降临",
    "location": "上海",
    "ip_location": "上海",
    "follow_count": 150,
    "fans_count": 2300,
    "likes_favorites_count": 8900,
    "note_count": 45,
}

MOCK_POSTS = [
    {
        "title": "备孕第3个月，分享我的排卵监测经验",
        "url": "https://www.xiaohongshu.com/explore/post1",
    },
    {
        "title": "上海哪家医院产检比较好？求推荐",
        "url": "https://www.xiaohongshu.com/explore/post2",
    },
    {
        "title": "每天挤地铁上班真的很累，但为了宝宝要坚持",
        "url": "https://www.xiaohongshu.com/explore/post3",
    },
    {
        "title": "开始准备婴儿用品了，买了好多小衣服",
        "url": "https://www.xiaohongshu.com/explore/post4",
    },
    {
        "title": "和老公商量了一下，决定明年要孩子",
        "url": "https://www.xiaohongshu.com/explore/post5",
    },
]


async def test_chinese_prompt():
    """测试中文 Prompt 效果"""
    print("=" * 60)
    print("测试中文 Prompt 效果")
    print("=" * 60)

    # 构建特征画像
    builder = AccountFeatureBuilder()
    raw_document = {
        "account_id": MOCK_PROFILE["id"],
        "raw_data": {
            "profile": MOCK_PROFILE,
            "posts": MOCK_POSTS,
            "likes": [],
            "favorites": [],
            "follows": [],
        },
    }
    feature_profile = builder.build(raw_document)

    print("\n📊 用户特征画像：")
    print(json.dumps(feature_profile, ensure_ascii=False, indent=2))

    # 测试中文 Prompt（无 API Key 时使用 mock）
    print("\n" + "=" * 60)
    print("测试中文 Prompt（Mock 模式）")
    print("=" * 60)

    extractor = PersonaExtractor(
        allow_mock_fallback=True,
        use_chinese_prompt=True,
    )

    persona = extractor.extract_persona(MOCK_PROFILE, MOCK_POSTS)

    print("\n🎯 推断结果：")
    print(f"  年龄段：{persona.get('age_group', 'Unknown')}")
    print(f"  所在城市：{persona.get('location', 'Unknown')}")
    print(f"  生育状态：{persona.get('fertility_status', 'Unknown')}")
    print(f"  收入水平：{persona.get('income_level', 'Unknown')}")
    print(f"  空间偏好：{persona.get('spatial_preferences', [])}")
    print(f"  生育意愿评分：{persona.get('fertility_intent_score', 0)}")
    print(f"  推断依据：{persona.get('reasoning_summary', 'Unknown')}")

    print("\n" + "=" * 60)
    print("测试英文 Prompt（Mock 模式）")
    print("=" * 60)

    extractor_en = PersonaExtractor(
        allow_mock_fallback=True,
        use_chinese_prompt=False,
    )

    persona_en = extractor_en.extract_persona(MOCK_PROFILE, MOCK_POSTS)

    print("\n🎯 推断结果：")
    print(f"  Age Group：{persona_en.get('age_group', 'Unknown')}")
    print(f"  Location：{persona_en.get('location', 'Unknown')}")
    print(f"  Fertility Status：{persona_en.get('fertility_status', 'Unknown')}")
    print(f"  Income Level：{persona_en.get('income_level', 'Unknown')}")
    print(f"  Spatial Preferences：{persona_en.get('spatial_preferences', [])}")
    print(f"  Fertility Intent Score：{persona_en.get('fertility_intent_score', 0)}")
    print(f"  Reasoning：{persona_en.get('reasoning_summary', 'Unknown')}")

    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)

    # 保存测试结果
    output = {
        "chinese_prompt": persona,
        "english_prompt": persona_en,
        "test_profile": MOCK_PROFILE,
        "test_posts": MOCK_POSTS,
    }

    with open("reports/prompt_test_result.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n📁 测试结果已保存到 reports/prompt_test_result.json")


if __name__ == "__main__":
    asyncio.run(test_chinese_prompt())
