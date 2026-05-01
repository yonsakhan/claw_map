#!/usr/bin/env python3
"""
测试优化后的推断逻辑
用法：python -m tests.test_inference_logic
"""

import json
from typing import Dict
from src.analysis.account_feature_profile import AccountFeatureBuilder


# 模拟小红书用户数据（测试推断逻辑）
MOCK_PROFILES = [
    {
        "id": "test_user_001",
        "display_name": "备孕小助手",
        "bio": "90后备孕中 | 分享备孕日常 | 期待小生命降临",
        "location": "上海",
        "ip_location": "上海",
    },
    {
        "id": "test_user_002",
        "display_name": "宝妈日记",
        "bio": "两个孩子的妈妈 | 分享育儿经验 | 家庭主妇",
        "location": "北京朝阳",
        "ip_location": "北京",
    },
    {
        "id": "test_user_003",
        "display_name": "职场女性",
        "bio": "30岁 | 单身 | 互联网公司工作 | 喜欢旅行",
        "location": "深圳南山",
        "ip_location": "深圳",
    },
    {
        "id": "test_user_004",
        "display_name": "怀孕记录",
        "bio": "孕28周 | 记录孕期生活 | 期待宝宝到来",
        "location": "广州天河",
        "ip_location": "广州",
    },
    {
        "id": "test_user_005",
        "display_name": "丁克一族",
        "bio": "坚持丁克 | 享受二人世界 | 不喜欢小孩",
        "location": "成都武侯",
        "ip_location": "成都",
    },
    {
        "id": "test_user_006",
        "display_name": "二胎妈妈",
        "bio": "大宝5岁 | 二宝2岁 | 俩娃的日常",
        "location": "杭州西湖",
        "ip_location": "杭州",
    },
    {
        "id": "test_user_007",
        "display_name": "新手妈妈",
        "bio": "宝宝3个月 | 新手妈妈 | 育儿路上",
        "location": "南京鼓楼",
        "ip_location": "南京",
    },
    {
        "id": "test_user_008",
        "display_name": "高龄产妇",
        "bio": "38岁怀孕 | 高龄产妇 | 孕期记录",
        "location": "武汉江汉",
        "ip_location": "武汉",
    },
]

# 为每个用户准备不同的帖子数据
MOCK_POSTS = [
    # 用户1：备孕小助手
    [
        {"title": "备孕第3个月，分享我的排卵监测经验"},
        {"title": "上海哪家医院产检比较好？求推荐"},
        {"title": "每天挤地铁上班真的很累，但为了宝宝要坚持"},
        {"title": "开始准备婴儿用品了，买了好多小衣服"},
        {"title": "和老公商量了一下，决定明年要孩子"},
    ],
    # 用户2：宝妈日记
    [
        {"title": "大宝今天幼儿园毕业了，时间过得好快"},
        {"title": "二宝的辅食食谱分享，宝宝超爱吃"},
        {"title": "带俩娃去公园遛娃，累并快乐着"},
        {"title": "宝宝发烧了，去医院看病的经历"},
        {"title": "分享一下我的育儿经验，希望对新手妈妈有帮助"},
    ],
    # 用户3：职场女性
    [
        {"title": "今天加班到10点，职场女性真的不容易"},
        {"title": "深圳的房价太贵了，什么时候才能买房"},
        {"title": "周末去爬山放松一下，工作压力太大了"},
        {"title": "30岁了，家里开始催婚了"},
        {"title": "分享一下我的职场成长经历"},
    ],
    # 用户4：怀孕记录
    [
        {"title": "孕28周了，宝宝胎动越来越频繁"},
        {"title": "今天去做四维彩超，看到宝宝的样子好激动"},
        {"title": "孕期反应好大，孕吐真的很难受"},
        {"title": "开始准备待产包了，好多东西要买"},
        {"title": "老公陪我去产检，感觉很幸福"},
    ],
    # 用户5：丁克一族
    [
        {"title": "坚持丁克5年，我们过得很幸福"},
        {"title": "不喜欢小孩，但尊重别人的选择"},
        {"title": "二人世界很精彩，去了很多地方旅行"},
        {"title": "养了一只猫，感觉比养孩子轻松多了"},
        {"title": "分享一下丁克生活的利与弊"},
    ],
    # 用户6：二胎妈妈
    [
        {"title": "大宝今天上小学了，时间过得好快"},
        {"title": "二宝的幼儿园生活开始了"},
        {"title": "带俩娃去公园玩，累并快乐着"},
        {"title": "分享一下二胎家庭的育儿经验"},
        {"title": "大宝和二宝的相处之道"},
    ],
    # 用户7：新手妈妈
    [
        {"title": "宝宝3个月了，开始添加辅食"},
        {"title": "新手妈妈的育儿日记"},
        {"title": "宝宝的第一次翻身，好激动"},
        {"title": "分享一下新生儿护理经验"},
        {"title": "宝宝的疫苗接种记录"},
    ],
    # 用户8：高龄产妇
    [
        {"title": "38岁怀孕，高龄产妇的孕期记录"},
        {"title": "高龄产妇的产检经历"},
        {"title": "孕期反应好大，孕吐真的很难受"},
        {"title": "开始准备待产包了，好多东西要买"},
        {"title": "高龄产妇的注意事项"},
    ],
]

# 预期结果
EXPECTED_RESULTS = [
    {
        "life_stage": "备孕中",
        "age_group": "30-34",
        "fertility_intent": "positive",
        "fertility_score": 4,
        "spatial_preferences": ["通勤便利", "医疗资源"],
    },
    {
        "life_stage": "已育2孩+",
        "age_group": "30-34",
        "fertility_intent": "positive",
        "fertility_score": 5,
        "spatial_preferences": ["公园绿地", "医疗资源", "教育资源"],
    },
    {
        "life_stage": "未婚",
        "age_group": "25-29",
        "fertility_intent": "unknown",
        "fertility_score": 0,
        "spatial_preferences": ["公园绿地", "居住空间"],
    },
    {
        "life_stage": "怀孕中",
        "age_group": "30-34",
        "fertility_intent": "positive",
        "fertility_score": 5,
        "spatial_preferences": ["医疗资源"],
    },
    {
        "life_stage": "未婚",
        "age_group": "25-29",
        "fertility_intent": "negative",
        "fertility_score": 0,
        "spatial_preferences": ["公园绿地"],
    },
    {
        "life_stage": "已育2孩+",
        "age_group": "30-34",
        "fertility_intent": "positive",
        "fertility_score": 5,
        "spatial_preferences": ["公园绿地", "教育资源"],
    },
    {
        "life_stage": "已育1孩",
        "age_group": "30-34",
        "fertility_intent": "positive",
        "fertility_score": 4,
        "spatial_preferences": ["医疗资源"],
    },
    {
        "life_stage": "怀孕中",
        "age_group": "35-39",
        "fertility_intent": "positive",
        "fertility_score": 5,
        "spatial_preferences": ["医疗资源"],
    },
]


def test_inference_logic():
    """测试推断逻辑"""
    print("=" * 80)
    print("测试优化后的推断逻辑")
    print("=" * 80)

    builder = AccountFeatureBuilder()

    # 测试结果
    test_results = []
    correct_count = 0
    total_count = 0

    for i, (profile, posts, expected) in enumerate(zip(MOCK_PROFILES, MOCK_POSTS, EXPECTED_RESULTS), 1):
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

        # 输出预期结果
        print(f"\n🎯 预期结果：")
        print(f"  生活阶段：{expected['life_stage']}")
        print(f"  年龄段：{expected['age_group']}")
        print(f"  生育意愿：{expected['fertility_intent']}")
        print(f"  生育评分：{expected['fertility_score']}")
        print(f"  空间偏好：{expected['spatial_preferences']}")

        # 计算准确度
        accuracy = calculate_accuracy(features, expected)
        print(f"\n📈 准确度：{accuracy:.2%}")

        # 统计
        test_results.append({
            "user_id": profile["id"],
            "display_name": profile["display_name"],
            "inferred": {
                "life_stage": life_stage.get('life_stage', 'Unknown'),
                "age_group": age.get('age_group', 'Unknown'),
                "fertility_intent": fertility.get('fertility_intent', 'Unknown'),
                "fertility_score": fertility.get('fertility_score', 0),
                "spatial_preferences": spatial.get('top_preferences', []),
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
        "test_posts": MOCK_POSTS,
        "expected_results": EXPECTED_RESULTS,
        "test_results": test_results,
        "summary": {
            "total_users": total_count,
            "correct_predictions": correct_count,
            "overall_accuracy": correct_count/total_count,
        },
    }

    with open("reports/inference_logic_test.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n📁 测试结果已保存到 reports/inference_logic_test.json")


def calculate_accuracy(features: Dict, expected: Dict) -> float:
    """计算推断准确度"""
    scores = []
    
    # 生活阶段准确度
    life_stage = features['features']['life_stage_clues']['value'].get('life_stage', 'Unknown')
    if life_stage == expected['life_stage']:
        scores.append(1.0)
    else:
        scores.append(0.0)
    
    # 年龄段准确度
    age_group = features['features']['age_clues']['value'].get('age_group', 'Unknown')
    if age_group == expected['age_group']:
        scores.append(1.0)
    else:
        # 允许相邻年龄段
        age_groups = ["18-24", "25-29", "30-34", "35-39", "40+"]
        inferred_idx = age_groups.index(age_group) if age_group in age_groups else -1
        expected_idx = age_groups.index(expected['age_group']) if expected['age_group'] in age_groups else -1
        if abs(inferred_idx - expected_idx) <= 1:
            scores.append(0.7)
        else:
            scores.append(0.0)
    
    # 生育意愿准确度
    fertility_intent = features['features']['fertility_clues']['value'].get('fertility_intent', 'unknown')
    if fertility_intent == expected['fertility_intent']:
        scores.append(1.0)
    else:
        scores.append(0.0)
    
    # 生育评分准确度（允许±1分误差）
    fertility_score = features['features']['fertility_clues']['value'].get('fertility_score', 0)
    if abs(fertility_score - expected['fertility_score']) <= 1:
        scores.append(1.0)
    else:
        scores.append(0.0)
    
    # 空间偏好准确度（允许部分匹配）
    spatial_preferences = features['features']['spatial_preference_clues']['value'].get('top_preferences', [])
    inferred_prefs = set(spatial_preferences)
    expected_prefs = set(expected['spatial_preferences'])
    if inferred_prefs and expected_prefs:
        intersection = inferred_prefs.intersection(expected_prefs)
        union = inferred_prefs.union(expected_prefs)
        scores.append(len(intersection) / len(union) if union else 0.0)
    else:
        scores.append(0.0)
    
    return sum(scores) / len(scores) if scores else 0.0


if __name__ == "__main__":
    test_inference_logic()
