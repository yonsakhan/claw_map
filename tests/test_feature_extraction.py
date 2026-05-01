#!/usr/bin/env python3
"""
测试优化后的特征提取算法
用法：python -m tests.test_feature_extraction
"""

import json
import asyncio
from src.analysis.account_feature_profile import AccountFeatureBuilder


# 模拟小红书用户数据
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


def test_feature_extraction():
    """测试特征提取算法"""
    print("=" * 80)
    print("测试优化后的特征提取算法")
    print("=" * 80)

    builder = AccountFeatureBuilder()

    # 为每个用户准备不同的帖子数据
    user_posts = [
        MOCK_POSTS_USER1,
        MOCK_POSTS_USER2,
        MOCK_POSTS_USER3,
    ]

    for i, (profile, posts) in enumerate(zip(MOCK_PROFILES, user_posts), 1):
        print(f"\n{'='*80}")
        print(f"测试用户 {i}: {profile['display_name']}")
        print(f"{'='*80}")

        # 构建特征
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

        features = builder.build(raw_document)

        # 输出特征
        print(f"\n📊 用户特征：")
        print(f"  账号ID：{features['account_id']}")
        print(f"  特征版本：{features['feature_schema_version']}")
        print(f"  完整度：{features['completeness']['score']:.2%}")

        print(f"\n👤 身份特征：")
        identity = features['features']['identity_clues']['value']
        print(f"  昵称：{identity.get('display_name', 'Unknown')}")
        print(f"  位置：{identity.get('location', 'Unknown')}")
        print(f"  简介：{identity.get('bio', 'Unknown')}")

        print(f"\n👶 生活阶段：")
        life_stage = features['features']['life_stage_clues']['value']
        print(f"  阶段：{life_stage.get('life_stage', 'Unknown')}")
        stats = features['features']['life_stage_clues']['stats']
        print(f"  匹配关键词：{stats.get('matched_keyword', 'None')}")
        print(f"  置信度：{stats.get('confidence', 0):.2%}")

        print(f"\n📍 空间偏好：")
        spatial = features['features']['spatial_preference_clues']['value']
        print(f"  偏好：{spatial.get('top_preferences', ['Unknown'])}")
        stats = features['features']['spatial_preference_clues']['stats']
        print(f"  匹配数量：{stats.get('matched_preferences', 0)}")

        print(f"\n💰 消费水平：")
        consumption = features['features']['consumption_clues']['value']
        print(f"  水平：{consumption.get('consumption_level', 'Unknown')}")
        stats = features['features']['consumption_clues']['stats']
        print(f"  高端信号：{stats.get('high_signals', 0)}")
        print(f"  低端信号：{stats.get('low_signals', 0)}")

        print(f"\n📈 活跃度：")
        activity = features['features']['activity_clues']['value']
        print(f"  等级：{activity.get('activity_level', 'Unknown')}")
        stats = features['features']['activity_clues']['stats']
        print(f"  帖子数：{stats.get('posts_count', 0)}")
        print(f"  总互动：{stats.get('total_interactions', 0)}")

        print(f"\n🎂 年龄段：")
        age = features['features']['age_clues']['value']
        print(f"  年龄段：{age.get('age_group', 'Unknown')}")
        stats = features['features']['age_clues']['stats']
        print(f"  匹配关键词：{stats.get('matched_keyword', 'None')}")
        print(f"  置信度：{stats.get('confidence', 0):.2%}")

        print(f"\n🍼 生育意愿：")
        fertility = features['features']['fertility_clues']['value']
        print(f"  意愿：{fertility.get('fertility_intent', 'Unknown')}")
        print(f"  评分：{fertility.get('fertility_score', 0)}/5")
        stats = features['features']['fertility_clues']['stats']
        print(f"  正面信号：{stats.get('positive_signals', 0)}")
        print(f"  负面信号：{stats.get('negative_signals', 0)}")
        print(f"  中性信号：{stats.get('neutral_signals', 0)}")

        print(f"\n📝 证据片段：")
        for ref in features['evidence_references'][:5]:
            print(f"  - [{ref['feature_key']}] {ref['snippet'][:50]}...")

    print(f"\n{'='*80}")
    print("测试完成！")
    print(f"{'='*80}")

    # 保存测试结果
    output = {
        "test_profiles": MOCK_PROFILES,
        "test_posts": [MOCK_POSTS_USER1, MOCK_POSTS_USER2, MOCK_POSTS_USER3],
        "results": [],
    }

    for profile, posts in zip(MOCK_PROFILES, user_posts):
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
        features = builder.build(raw_document)
        output["results"].append(features)

    with open("reports/feature_extraction_test.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n📁 测试结果已保存到 reports/feature_extraction_test.json")


if __name__ == "__main__":
    test_feature_extraction()
