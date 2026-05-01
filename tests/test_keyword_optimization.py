#!/usr/bin/env python3
"""
测试优化后的关键词库
用法：python -m tests.test_keyword_optimization
"""

import json
from src.analysis.account_feature_profile import AccountFeatureBuilder


# 模拟小红书用户数据（测试关键词覆盖）
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


def test_keyword_optimization():
    """测试关键词库优化效果"""
    print("=" * 80)
    print("测试优化后的关键词库")
    print("=" * 80)

    builder = AccountFeatureBuilder()

    # 测试结果
    test_results = []

    for i, (profile, posts) in enumerate(zip(MOCK_PROFILES, MOCK_POSTS), 1):
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

        # 收集测试结果
        test_results.append({
            "user_id": profile["id"],
            "display_name": profile["display_name"],
            "features": {
                "life_stage": life_stage.get('life_stage', 'Unknown'),
                "age_group": age.get('age_group', 'Unknown'),
                "fertility_intent": fertility.get('fertility_intent', 'Unknown'),
                "fertility_score": fertility.get('fertility_score', 0),
                "spatial_preferences": spatial.get('top_preferences', []),
                "consumption_level": consumption.get('consumption_level', 'Unknown'),
            },
            "completeness": features['completeness']['score'],
        })

    # 输出总结
    print(f"\n{'='*80}")
    print("测试总结")
    print(f"{'='*80}")

    # 统计各维度识别率
    life_stage_count = sum(1 for r in test_results if r['features']['life_stage'] != 'Unknown')
    age_group_count = sum(1 for r in test_results if r['features']['age_group'] != 'Unknown')
    fertility_intent_count = sum(1 for r in test_results if r['features']['fertility_intent'] != 'unknown')
    spatial_count = sum(1 for r in test_results if r['features']['spatial_preferences'] and r['features']['spatial_preferences'][0] != 'Unknown')
    consumption_count = sum(1 for r in test_results if r['features']['consumption_level'] != 'Unknown')

    total = len(test_results)
    print(f"总用户数：{total}")
    print(f"生活阶段识别率：{life_stage_count}/{total} ({life_stage_count/total:.2%})")
    print(f"年龄段识别率：{age_group_count}/{total} ({age_group_count/total:.2%})")
    print(f"生育意愿识别率：{fertility_intent_count}/{total} ({fertility_intent_count/total:.2%})")
    print(f"空间偏好识别率：{spatial_count}/{total} ({spatial_count/total:.2%})")
    print(f"消费水平识别率：{consumption_count}/{total} ({consumption_count/total:.2%})")

    # 保存测试结果
    output = {
        "test_profiles": MOCK_PROFILES,
        "test_posts": MOCK_POSTS,
        "test_results": test_results,
        "summary": {
            "total_users": total,
            "life_stage识别率": life_stage_count/total,
            "age_group识别率": age_group_count/total,
            "fertility_intent识别率": fertility_intent_count/total,
            "spatial_preferences识别率": spatial_count/total,
            "consumption_level识别率": consumption_count/total,
        },
    }

    with open("reports/keyword_optimization_test.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n📁 测试结果已保存到 reports/keyword_optimization_test.json")


if __name__ == "__main__":
    test_keyword_optimization()
