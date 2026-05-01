#!/usr/bin/env python3
"""
测试优化后的推断准确度
用法：python -m tests.test_inference_accuracy
"""

import json
import asyncio
from typing import Dict
from src.analysis.persona_extractor import PersonaExtractor
from src.analysis.account_feature_profile import AccountFeatureBuilder


# 模拟小红书用户数据（更真实的场景）
MOCK_PROFILES = [
    {
        "id": "test_user_001",
        "display_name": "备孕小助手",
        "bio": "90后备孕中 | 分享备孕日常 | 期待小生命降临",
        "location": "上海",
        "ip_location": "上海",
        "follow_count": 150,
        "fans_count": 2300,
        "likes_favorites_count": 8900,
        "note_count": 45,
    },
    {
        "id": "test_user_002",
        "display_name": "宝妈日记",
        "bio": "两个孩子的妈妈 | 分享育儿经验 | 家庭主妇",
        "location": "北京朝阳",
        "ip_location": "北京",
        "follow_count": 80,
        "fans_count": 1500,
        "likes_favorites_count": 5600,
        "note_count": 32,
    },
    {
        "id": "test_user_003",
        "display_name": "职场女性",
        "bio": "30岁 | 单身 | 互联网公司工作 | 喜欢旅行",
        "location": "深圳南山",
        "ip_location": "深圳",
        "follow_count": 200,
        "fans_count": 800,
        "likes_favorites_count": 3200,
        "note_count": 28,
    },
    {
        "id": "test_user_004",
        "display_name": "怀孕记录",
        "bio": "孕28周 | 记录孕期生活 | 期待宝宝到来",
        "location": "广州天河",
        "ip_location": "广州",
        "follow_count": 120,
        "fans_count": 1800,
        "likes_favorites_count": 7200,
        "note_count": 38,
    },
    {
        "id": "test_user_005",
        "display_name": "丁克一族",
        "bio": "坚持丁克 | 享受二人世界 | 不喜欢小孩",
        "location": "成都武侯",
        "ip_location": "成都",
        "follow_count": 90,
        "fans_count": 950,
        "likes_favorites_count": 4500,
        "note_count": 25,
    },
]

# 为每个用户准备不同的帖子数据
MOCK_POSTS_USER1 = [
    {"title": "备孕第3个月，分享我的排卵监测经验"},
    {"title": "上海哪家医院产检比较好？求推荐"},
    {"title": "每天挤地铁上班真的很累，但为了宝宝要坚持"},
    {"title": "开始准备婴儿用品了，买了好多小衣服"},
    {"title": "和老公商量了一下，决定明年要孩子"},
]

MOCK_POSTS_USER2 = [
    {"title": "大宝今天幼儿园毕业了，时间过得好快"},
    {"title": "二宝的辅食食谱分享，宝宝超爱吃"},
    {"title": "带俩娃去公园遛娃，累并快乐着"},
    {"title": "宝宝发烧了，去医院看病的经历"},
    {"title": "分享一下我的育儿经验，希望对新手妈妈有帮助"},
]

MOCK_POSTS_USER3 = [
    {"title": "今天加班到10点，职场女性真的不容易"},
    {"title": "深圳的房价太贵了，什么时候才能买房"},
    {"title": "周末去爬山放松一下，工作压力太大了"},
    {"title": "30岁了，家里开始催婚了"},
    {"title": "分享一下我的职场成长经历"},
]

MOCK_POSTS_USER4 = [
    {"title": "孕28周了，宝宝胎动越来越频繁"},
    {"title": "今天去做四维彩超，看到宝宝的样子好激动"},
    {"title": "孕期反应好大，孕吐真的很难受"},
    {"title": "开始准备待产包了，好多东西要买"},
    {"title": "老公陪我去产检，感觉很幸福"},
]

MOCK_POSTS_USER5 = [
    {"title": "坚持丁克5年，我们过得很幸福"},
    {"title": "不喜欢小孩，但尊重别人的选择"},
    {"title": "二人世界很精彩，去了很多地方旅行"},
    {"title": "养了一只猫，感觉比养孩子轻松多了"},
    {"title": "分享一下丁克生活的利与弊"},
]


def test_inference_accuracy():
    """测试推断准确度"""
    print("=" * 80)
    print("测试优化后的推断准确度")
    print("=" * 80)

    # 构建特征画像
    builder = AccountFeatureBuilder()
    
    # 为每个用户准备不同的帖子数据
    user_posts = [
        MOCK_POSTS_USER1,
        MOCK_POSTS_USER2,
        MOCK_POSTS_USER3,
        MOCK_POSTS_USER4,
        MOCK_POSTS_USER5,
    ]

    # 预期结果
    expected_results = [
        {
            "age_group": "30-34",
            "fertility_status": "备孕中",
            "income_level": "中",
            "spatial_preferences": ["通勤便利", "医疗资源"],
            "fertility_intent_score": 4,
        },
        {
            "age_group": "30-34",
            "fertility_status": "已育2孩+",
            "income_level": "中",
            "spatial_preferences": ["公园绿地", "医疗资源", "教育资源"],
            "fertility_intent_score": 5,
        },
        {
            "age_group": "25-29",
            "fertility_status": "未婚",
            "income_level": "中",
            "spatial_preferences": ["公园绿地", "居住空间"],
            "fertility_intent_score": 0,
        },
        {
            "age_group": "30-34",
            "fertility_status": "怀孕中",
            "income_level": "中",
            "spatial_preferences": ["医疗资源"],
            "fertility_intent_score": 5,
        },
        {
            "age_group": "30-34",
            "fertility_status": "未婚",
            "income_level": "中",
            "spatial_preferences": ["公园绿地"],
            "fertility_intent_score": 0,
        },
    ]

    # 测试结果
    test_results = []
    correct_count = 0
    total_count = 0

    for i, (profile, posts, expected) in enumerate(zip(MOCK_PROFILES, user_posts, expected_results), 1):
        print(f"\n{'='*80}")
        print(f"测试用户 {i}: {profile['display_name']}")
        print(f"{'='*80}")

        # 构建特征画像
        raw_document = {
            "account_id": profile["id"],
            "raw_data": {
                "profile": profile,
                "posts": posts,
                "likes": [],
                "favorites": [],
                "follows": [],
            },
        }
        feature_profile = builder.build(raw_document)

        # 使用 Mock 模式测试
        extractor = PersonaExtractor(
            allow_mock_fallback=True,
            use_chinese_prompt=True,
        )

        persona = extractor.extract_persona(profile, posts)

        # 输出推断结果
        print(f"\n📊 推断结果：")
        print(f"  年龄段：{persona.get('age_group', 'Unknown')}")
        print(f"  生育状态：{persona.get('fertility_status', 'Unknown')}")
        print(f"  收入水平：{persona.get('income_level', 'Unknown')}")
        print(f"  空间偏好：{persona.get('spatial_preferences', [])}")
        print(f"  生育意愿评分：{persona.get('fertility_intent_score', 0)}")
        print(f"  置信度：{persona.get('confidence', 0):.2%}")

        # 输出预期结果
        print(f"\n🎯 预期结果：")
        print(f"  年龄段：{expected['age_group']}")
        print(f"  生育状态：{expected['fertility_status']}")
        print(f"  收入水平：{expected['income_level']}")
        print(f"  空间偏好：{expected['spatial_preferences']}")
        print(f"  生育意愿评分：{expected['fertility_intent_score']}")

        # 计算准确度
        accuracy = calculate_accuracy(persona, expected)
        print(f"\n📈 准确度：{accuracy:.2%}")

        # 统计
        test_results.append({
            "user_id": profile["id"],
            "display_name": profile["display_name"],
            "inferred": {
                "age_group": persona.get('age_group', 'Unknown'),
                "fertility_status": persona.get('fertility_status', 'Unknown'),
                "income_level": persona.get('income_level', 'Unknown'),
                "spatial_preferences": persona.get('spatial_preferences', []),
                "fertility_intent_score": persona.get('fertility_intent_score', 0),
            },
            "expected": expected,
            "accuracy": accuracy,
        })

        if accuracy >= 0.8:  # 80% 以上算正确
            correct_count += 1
        total_count += 1

    # 输出总结
    print(f"\n{'='*80}")
    print("测试总结")
    print(f"{'='*80}")
    print(f"总用户数：{total_count}")
    print(f"准确推断数：{correct_count}")
    print(f"整体准确度：{correct_count/total_count:.2%}")

    # 保存测试结果
    output = {
        "test_profiles": MOCK_PROFILES,
        "test_posts": user_posts,
        "expected_results": expected_results,
        "test_results": test_results,
        "summary": {
            "total_users": total_count,
            "correct_predictions": correct_count,
            "overall_accuracy": correct_count/total_count,
        },
    }

    with open("reports/inference_accuracy_test.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n📁 测试结果已保存到 reports/inference_accuracy_test.json")


def calculate_accuracy(inferred: Dict, expected: Dict) -> float:
    """计算推断准确度"""
    scores = []
    
    # 年龄段准确度
    if inferred.get("age_group") == expected.get("age_group"):
        scores.append(1.0)
    else:
        # 允许相邻年龄段
        age_groups = ["18-24", "25-29", "30-34", "35-39", "40+"]
        inferred_idx = age_groups.index(inferred.get("age_group", "")) if inferred.get("age_group") in age_groups else -1
        expected_idx = age_groups.index(expected.get("age_group", "")) if expected.get("age_group") in age_groups else -1
        if abs(inferred_idx - expected_idx) <= 1:
            scores.append(0.7)
        else:
            scores.append(0.0)
    
    # 生育状态准确度
    if inferred.get("fertility_status") == expected.get("fertility_status"):
        scores.append(1.0)
    else:
        scores.append(0.0)
    
    # 收入水平准确度
    if inferred.get("income_level") == expected.get("income_level"):
        scores.append(1.0)
    else:
        scores.append(0.0)
    
    # 空间偏好准确度（允许部分匹配）
    inferred_prefs = set(inferred.get("spatial_preferences", []))
    expected_prefs = set(expected.get("spatial_preferences", []))
    if inferred_prefs and expected_prefs:
        intersection = inferred_prefs.intersection(expected_prefs)
        union = inferred_prefs.union(expected_prefs)
        scores.append(len(intersection) / len(union) if union else 0.0)
    else:
        scores.append(0.0)
    
    # 生育意愿评分准确度（允许±1分误差）
    inferred_score = inferred.get("fertility_intent_score", 0)
    expected_score = expected.get("fertility_intent_score", 0)
    if abs(inferred_score - expected_score) <= 1:
        scores.append(1.0)
    else:
        scores.append(0.0)
    
    return sum(scores) / len(scores) if scores else 0.0


if __name__ == "__main__":
    test_inference_accuracy()
