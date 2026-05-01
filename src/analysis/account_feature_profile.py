from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import re
import json


class AccountFeatureBuilder:
    def __init__(self):
        # 生育相关关键词库（优化版）
        self.fertility_keywords = {
            "备孕中": [
                # 强信号
                "备孕", "排卵", "验孕", "造人", "备孕中", "备孕期",
                "排卵试纸", "排卵期", "基础体温", "黄体酮", "叶酸",
                "备孕日记", "备孕日常", "备孕记录", "备孕生活",
                # 弱信号
                "期待小生命", "准备要孩子", "计划怀孕", "想要宝宝",
                "造人计划", "备孕路上", "备孕历程", "备孕经验",
            ],
            "怀孕中": [
                # 强信号
                "怀孕", "孕检", "产检", "胎动", "孕吐", "孕期",
                "孕妇", "孕妈", "孕晚期", "孕中期", "孕早期",
                "NT检查", "唐筛", "糖耐", "四维", "B超",
                "待产", "预产期", "胎心", "胎教", "孕妇装",
                # 弱信号
                "怀孕日记", "孕期生活", "孕期记录", "孕期反应",
                "孕吐严重", "孕期营养", "孕期运动", "孕期检查",
            ],
            "已育1孩": [
                # 强信号
                "宝宝", "婴儿", "奶粉", "辅食", "月子", "产后",
                "新生儿", "育儿", "带娃", "遛娃", "带孩子",
                "一岁", "两岁", "三岁", "幼儿园", "早教",
                "奶瓶", "尿不湿", "纸尿裤", "婴儿车", "婴儿床",
                # 弱信号
                "宝宝辅食", "宝宝奶粉", "宝宝衣服", "宝宝玩具",
                "育儿经验", "育儿日常", "育儿记录", "育儿心得",
            ],
            "已育2孩+": [
                # 强信号
                "大宝", "二宝", "三宝", "俩娃", "三个娃",
                "二胎", "三胎", "多胎", "双胞胎", "龙凤胎",
                "老大", "老二", "老三", "哥哥", "姐姐", "弟弟", "妹妹",
                # 弱信号
                "两个孩子", "三个孩子", "多孩家庭", "大家庭",
                "二胎生活", "三胎生活", "多孩育儿", "兄弟姐妹",
            ],
        }

        # 生活阶段关键词库（优化版）
        self.life_stage_keywords = {
            "未婚": [
                # 强信号
                "单身", "一个人", "独居", "没有男朋友", "没有女朋友",
                "相亲", "找对象", "谈恋爱", "恋爱中",
                # 弱信号
                "未婚", "没结婚", "没对象", "单身生活",
                "一个人生活", "独居生活", "单身日记",
                # 新增：丁克相关
                "丁克", "不要孩子", "不想生", "讨厌小孩", "不喜欢小孩",
            ],
            "已婚未育": [
                # 强信号
                "结婚", "老公", "老婆", "丈夫", "妻子", "已婚",
                "婚礼", "结婚纪念日", "二人世界", "夫妻",
                # 弱信号
                "婚后生活", "夫妻生活", "二人世界", "新婚",
                "结婚后", "婚后日常", "夫妻日常",
            ],
        }

        # 空间偏好关键词库（优化版）
        self.spatial_keywords = {
            "通勤便利": [
                # 通勤场景
                "地铁", "通勤", "上班", "挤地铁", "公交", "打车",
                "上班路上", "通勤时间", "早高峰", "晚高峰",
                "地铁站", "公交站", "换乘", "通勤距离",
                # 时间成本
                "通勤累", "通勤辛苦", "通勤痛苦", "通勤疲惫",
                "上班远", "上班距离", "上班时间", "上班路上",
            ],
            "公园绿地": [
                # 休闲需求
                "公园", "遛娃", "户外", "绿地", "散步", "跑步",
                "小区绿化", "花园", "植物园", "森林公园",
                "河边", "湖边", "海边", "爬山", "徒步",
                # 环境需求
                "空气好", "环境好", "绿化好", "风景好",
                "自然", "亲近自然", "户外活动", "户外运动",
                # 新增：旅行相关
                "旅行", "出游", "旅游", "度假", "游玩",
            ],
            "医疗资源": [
                # 孕产需求
                "医院", "产检", "妇幼保健院", "儿童医院",
                # 日常医疗
                "儿科", "看病", "挂号", "门诊", "社区医院",
                "药店", "诊所", "卫生院", "医疗",
                # 健康管理
                "体检", "疫苗", "打针", "吃药", "保健",
                "健康", "医疗资源", "医疗服务", "医疗设施",
            ],
            "教育资源": [
                # 学前教育
                "幼儿园", "托班", "早教", "托儿所",
                # 基础教育
                "小学", "中学", "高中", "学区", "学区房",
                # 课外培训
                "培训班", "兴趣班", "辅导班", "家教",
                "教育", "学校", "升学", "考试",
            ],
            "生活配套": [
                # 购物需求
                "超市", "商场", "便利店", "菜市场", "生鲜",
                # 生活服务
                "外卖", "快递", "洗衣", "理发", "银行", "ATM",
                # 日常生活
                "买菜", "购物", "生活便利", "生活配套",
                "生活设施", "商业配套", "商业设施",
            ],
            "出行安全": [
                # 人身安全
                "安全", "治安", "监控", "路灯", "保安",
                # 出行便利
                "门禁", "小区安全", "夜间出行", "夜路",
                # 特殊群体
                "女性安全", "独居安全", "老人安全", "儿童安全",
                "安全出行", "安全环境", "安全社区",
            ],
            "居住空间": [
                # 住房需求
                "房子", "户型", "面积", "租房", "买房",
                # 居住环境
                "装修", "家具", "收纳", "阳台", "采光",
                # 空间功能
                "卧室", "客厅", "厨房", "卫生间", "储物间",
                "居住空间", "居住环境", "居住条件",
            ],
        }

        # 收入水平关键词库（优化版）
        self.income_keywords = {
            "高": [
                # 生活方式
                "奢侈", "高端", "五星", "名牌", "豪华",
                "进口", "定制", "限量", "VIP", "私人",
                # 医疗选择
                "私立医院", "月子中心", "VIP产房", "高端产检",
                # 教育选择
                "国际学校", "海外留学", "私立学校", "贵族学校",
                # 消费习惯
                "高尔夫", "马术", "滑雪", "潜水", "游艇",
                "高端消费", "奢侈品牌", "高端品牌",
            ],
            "低": [
                # 消费习惯
                "平价", "省钱", "优惠", "折扣", "团购",
                "打折", "促销", "特价", "便宜", "实惠",
                # 购物平台
                "拼多多", "淘宝", "二手", "闲置", "跳蚤市场",
                # 生活压力
                "分期", "贷款", "负债", "月光", "省钱攻略",
                "精打细算", "勤俭节约", "经济实惠",
            ],
        }

        # 年龄段关键词库（优化版）
        self.age_keywords = {
            "18-24": [
                # 学生阶段
                "大学", "考研", "应届", "实习", "毕业",
                "校园", "宿舍", "食堂", "社团", "学生",
                # 年轻特征
                "年轻人", "95后", "00后", "青春", "活力",
            ],
            "25-29": [
                # 职场阶段
                "工作", "职场", "加班", "升职", "跳槽",
                "租房", "独居", "恋爱", "结婚", "买房",
                # 生活阶段
                "奋斗", "打拼", "事业", "职业发展",
            ],
            "30-34": [
                # 家庭阶段
                "备孕", "怀孕", "宝宝", "育儿", "家庭",
                "事业", "稳定", "中年", "三十而立",
                # 生活阶段
                "成家立业", "家庭责任", "育儿压力",
            ],
            "35-39": [
                # 家庭扩展
                "二胎", "高龄", "35岁", "中年危机",
                "孩子上学", "学区房", "辅导作业",
                # 生活阶段
                "中年", "上有老下有小", "家庭负担",
            ],
            "40+": [
                # 家庭成熟
                "孩子上学", "中考", "高考", "青春期",
                "更年期", "中年", "四十不惑", "知天命",
                # 生活阶段
                "中年危机", "退休", "养老", "健康问题",
            ],
        }

        # 生育意愿关键词库（优化版 - 大幅扩展）
        self.fertility_intent_keywords = {
            "正面": [
                # 积极备孕
                "备孕", "怀孕", "宝宝", "孩子", "生育",
                "想要孩子", "计划要孩子", "准备要孩子",
                "期待", "期待小生命", "期待宝宝",
                # 已育满意
                "幸福", "值得", "还想生", "再生一个",
                "孩子是礼物", "母爱", "父爱", "家庭幸福",
                # 新增：育儿相关
                "育儿", "带娃", "遛娃", "亲子",
                "宝宝成长", "孩子成长", "育儿经验",
                # 新增：家庭相关
                "家庭", "一家三口", "一家四口", "天伦之乐",
                "温馨", "幸福时光", "美好回忆",
                # 新增：教育相关
                "教育", "培养", "陪伴", "成长",
                "孩子教育", "育儿心得", "教育理念",
                # 新增：生活相关
                "生活", "日常", "记录", "分享",
                "育儿日常", "带娃日常", "亲子时光",
            ],
            "负面": [
                # 明确拒绝
                "丁克", "不生", "不要孩子", "不想生",
                "讨厌小孩", "不喜欢小孩", "恐婚恐育",
                # 顾虑担忧
                "压力大", "养不起", "养不起孩子",
                "生育成本", "育儿成本", "经济压力",
                # 新增：负面情绪
                "焦虑", "担忧", "害怕", "恐惧",
                "生育焦虑", "育儿焦虑", "经济焦虑",
                # 新增：生活压力
                "工作压力", "生活压力", "经济负担",
                "房贷", "车贷", "生活成本",
                # 新增：个人发展
                "事业", "职业发展", "个人发展",
                "不想被束缚", "自由", "独立",
                # 新增：后悔相关
                "后悔", "后悔生孩子", "后悔生育",
                "负担", "累赘", "束缚",
                # 新增：负面体验
                "累", "疲惫", "崩溃", "绝望",
                "心累", "身体累", "精神压力",
            ],
            "中性": [
                # 犹豫观望
                "顺其自然", "看情况", "以后再说", "不着急",
                "还没想好", "还在考虑", "犹豫", "不确定",
                # 中立态度
                "随缘", "无所谓", "看缘分", "到时候再说",
                # 新增：客观描述
                "计划", "打算", "考虑", "思考",
                "未来", "规划", "人生规划",
                # 新增：条件限制
                "条件", "时机", "准备", "成熟",
                "条件成熟", "时机合适", "准备好了",
            ],
        }

    def build(self, raw_document: Dict[str, Any]) -> Dict[str, Any]:
        account_id = str(raw_document.get("account_id", ""))
        raw_data = raw_document.get("raw_data", {}) or raw_document
        profile = raw_data.get("profile", {}) or {}
        posts = raw_data.get("posts", []) or []
        likes = raw_data.get("likes", []) or []
        favorites = raw_data.get("favorites", []) or []
        follows = raw_data.get("follows", []) or []

        # 提取所有文本片段
        all_snippets = self._extract_all_snippets(profile, posts, likes, favorites, follows)

        # 构建特征
        identity = self._identity_clues(profile)
        life_stage = self._life_stage_clues(profile, posts, all_snippets)
        spatial = self._spatial_clues(posts, likes, favorites, all_snippets)
        consumption = self._consumption_clues(profile, posts, likes, favorites, all_snippets)
        activity = self._activity_clues(posts, likes, favorites, follows)
        age = self._age_clues(profile, posts, all_snippets, life_stage)
        fertility = self._fertility_clues(profile, posts, all_snippets, life_stage)

        # 计算整体置信度
        overall_confidence = self._calculate_overall_confidence(
            identity, life_stage, spatial, consumption, activity, age, fertility
        )

        # 计算证据质量
        evidence_quality = self._calculate_evidence_quality(
            identity, life_stage, spatial, consumption, activity, age, fertility
        )

        # 生成证据来源可视化数据
        evidence_visualization = self._generate_evidence_visualization(
            identity, life_stage, spatial, consumption, activity, age, fertility
        )

        features = {
            "identity_clues": identity,
            "life_stage_clues": life_stage,
            "spatial_preference_clues": spatial,
            "consumption_clues": consumption,
            "activity_clues": activity,
            "age_clues": age,
            "fertility_clues": fertility,
        }
        completeness = self._completeness(features)
        return {
            "account_id": account_id,
            "feature_schema_version": "v2",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "features": features,
            "completeness": completeness,
            "overall_confidence": overall_confidence,
            "evidence_quality": evidence_quality,
            "evidence_visualization": evidence_visualization,
            "evidence_references": self._evidence_references(features),
        }

    def _extract_all_snippets(
        self,
        profile: Dict[str, Any],
        posts: List[Dict[str, Any]],
        likes: List[Dict[str, Any]],
        favorites: List[Dict[str, Any]],
        follows: List[Dict[str, Any]],
    ) -> List[str]:
        """提取所有文本片段"""
        snippets: List[str] = []

        # 从 profile 提取
        for field in ["bio", "display_name", "location", "ip_location"]:
            value = profile.get(field)
            if value:
                snippets.append(str(value))

        # 从 posts 提取
        for post in posts:
            for field in ["title", "content", "text", "description"]:
                value = post.get(field)
                if value:
                    snippets.append(str(value))
            # 提取笔记详情
            detail = post.get("detail", {})
            if detail:
                for field in ["content_text", "title", "description"]:
                    value = detail.get(field)
                    if value:
                        snippets.append(str(value))

        # 从 likes/favorites 提取
        for item in likes + favorites:
            for field in ["title", "content", "text", "description"]:
                value = item.get(field)
                if value:
                    snippets.append(str(value))

        return snippets

    def _identity_clues(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        raw_location = profile.get("location") or ""
        ip_location = profile.get("ip_location") or ""
        location = raw_location or ip_location or "Unknown"
        display_name = profile.get("display_name") or ""
        bio = profile.get("bio") or ""
        evidence = [item for item in [display_name, bio, raw_location, ip_location] if item]
        
        # 计算置信度
        confidence = 0.0
        if evidence:
            confidence = min(1.0, len(evidence) * 0.3)  # 每个证据增加0.3置信度
        
        # 计算证据质量
        evidence_quality = self._assess_evidence_quality(evidence, "identity")
        
        return self._feature_value(
            {"location": location, "display_name": display_name, "bio": bio},
            evidence,
            {"profile_fields_present": len([i for i in [raw_location, display_name, bio, ip_location] if i])},
            confidence=confidence,
            evidence_quality=evidence_quality,
        )

    def _life_stage_clues(
        self,
        profile: Dict[str, Any],
        posts: List[Dict[str, Any]],
        all_snippets: List[str],
    ) -> Dict[str, Any]:
        """生活阶段识别（优化版）"""
        merged = " ".join(all_snippets).lower()
        
        # 优先检查生育状态
        for stage, keywords in self.fertility_keywords.items():
            for keyword in keywords:
                if keyword in merged:
                    # 计算置信度
                    confidence = self._calculate_keyword_confidence(keyword, all_snippets, "fertility")
                    # 计算证据质量
                    evidence = [snippet for snippet in all_snippets if keyword in snippet.lower()][:3]
                    evidence_quality = self._assess_evidence_quality(evidence, "fertility")
                    return self._feature_value(
                        {"life_stage": stage},
                        evidence,
                        {"matched_keyword": keyword, "confidence": confidence},
                        confidence=confidence,
                        evidence_quality=evidence_quality,
                    )

        # 检查婚姻状态
        for stage, keywords in self.life_stage_keywords.items():
            for keyword in keywords:
                if keyword in merged:
                    # 计算置信度
                    confidence = self._calculate_keyword_confidence(keyword, all_snippets, "life_stage")
                    # 计算证据质量
                    evidence = [snippet for snippet in all_snippets if keyword in snippet.lower()][:3]
                    evidence_quality = self._assess_evidence_quality(evidence, "life_stage")
                    return self._feature_value(
                        {"life_stage": stage},
                        evidence,
                        {"matched_keyword": keyword, "confidence": confidence},
                        confidence=confidence,
                        evidence_quality=evidence_quality,
                    )

        return self._feature_value(
            {"life_stage": "Unknown"},
            ["fallback:insufficient_evidence"],
            {"matched_keyword": None, "confidence": 0.0},
            confidence=0.0,
            evidence_quality={"relevance": 0.0, "timeliness": 0.0, "credibility": 0.0, "overall": 0.0},
        )

    def _spatial_clues(
        self,
        posts: List[Dict[str, Any]],
        likes: List[Dict[str, Any]],
        favorites: List[Dict[str, Any]],
        all_snippets: List[str],
    ) -> Dict[str, Any]:
        """空间偏好识别（优化版）"""
        merged = " ".join(all_snippets).lower()
        matched = []
        evidence_map = {}

        for preference, keywords in self.spatial_keywords.items():
            for keyword in keywords:
                if keyword in merged:
                    if preference not in matched:
                        matched.append(preference)
                        evidence_map[preference] = []
                    # 收集证据
                    for snippet in all_snippets:
                        if keyword in snippet.lower() and len(evidence_map[preference]) < 2:
                            evidence_map[preference].append(snippet)
                    break  # 找到一个关键词就跳出

        if not matched:
            matched = ["Unknown"]
            evidence_map = {"Unknown": ["fallback:insufficient_evidence"]}

        # 构建证据列表
        evidence = []
        for preference in matched[:3]:
            evidence.extend(evidence_map.get(preference, [])[:2])

        # 计算置信度
        confidence = self._calculate_spatial_confidence(matched, evidence_map)
        
        # 计算证据质量
        evidence_quality = self._assess_evidence_quality(evidence, "spatial")

        return self._feature_value(
            {"top_preferences": matched[:3]},
            evidence[:4],
            {"matched_preferences": len([m for m in matched if m != "Unknown"])},
            confidence=confidence,
            evidence_quality=evidence_quality,
        )

    def _consumption_clues(
        self,
        profile: Dict[str, Any],
        posts: List[Dict[str, Any]],
        likes: List[Dict[str, Any]],
        favorites: List[Dict[str, Any]],
        all_snippets: List[str],
    ) -> Dict[str, Any]:
        """消费水平识别（优化版）"""
        merged = " ".join(all_snippets).lower()
        
        # 统计高低频关键词
        high_count = 0
        low_count = 0
        evidence_high = []
        evidence_low = []

        for keyword in self.income_keywords["高"]:
            if keyword in merged:
                high_count += 1
                for snippet in all_snippets:
                    if keyword in snippet.lower() and len(evidence_high) < 2:
                        evidence_high.append(snippet)

        for keyword in self.income_keywords["低"]:
            if keyword in merged:
                low_count += 1
                for snippet in all_snippets:
                    if keyword in snippet.lower() and len(evidence_low) < 2:
                        evidence_low.append(snippet)

        # 判断收入水平
        if high_count > low_count and high_count >= 2:
            level = "High"
            evidence = evidence_high[:3]
            confidence = min(1.0, high_count * 0.2)  # 每个高端信号增加0.2置信度
        elif low_count > high_count and low_count >= 2:
            level = "Low"
            evidence = evidence_low[:3]
            confidence = min(1.0, low_count * 0.2)  # 每个低端信号增加0.2置信度
        else:
            level = "Medium"
            evidence = ["fallback:insufficient_evidence"]
            confidence = 0.3  # 中等收入的默认置信度
        
        # 计算证据质量
        evidence_quality = self._assess_evidence_quality(evidence, "consumption")

        return self._feature_value(
            {"consumption_level": level},
            evidence,
            {"high_signals": high_count, "low_signals": low_count},
            confidence=confidence,
            evidence_quality=evidence_quality,
        )

    def _activity_clues(
        self,
        posts: List[Dict[str, Any]],
        likes: List[Dict[str, Any]],
        favorites: List[Dict[str, Any]],
        follows: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        post_count = len(posts)
        like_count = len(likes)
        favorite_count = len(favorites)
        follow_count = len(follows)
        total = post_count + like_count + favorite_count + follow_count
        level = "low"
        if total >= 20:
            level = "high"
        elif total >= 8:
            level = "medium"
        evidence = [
            f"posts={post_count}",
            f"likes={like_count}",
            f"favorites={favorite_count}",
            f"follows={follow_count}",
        ]
        
        # 计算置信度
        confidence = min(1.0, total * 0.05)  # 每个互动增加0.05置信度
        
        # 计算证据质量
        evidence_quality = self._assess_evidence_quality(evidence, "activity")
        
        return self._feature_value(
            {"activity_level": level},
            evidence,
            {
                "posts_count": post_count,
                "likes_count": like_count,
                "favorites_count": favorite_count,
                "follows_count": follow_count,
                "total_interactions": total,
            },
            confidence=confidence,
            evidence_quality=evidence_quality,
        )

    def _age_clues(
        self,
        profile: Dict[str, Any],
        posts: List[Dict[str, Any]],
        all_snippets: List[str],
        life_stage: Dict[str, Any],
    ) -> Dict[str, Any]:
        """年龄段识别（优化版 - 增加交叉验证）"""
        merged = " ".join(all_snippets).lower()
        
        # 优先检查明确的年龄段关键词
        for age_group, keywords in self.age_keywords.items():
            for keyword in keywords:
                if keyword in merged:
                    # 计算置信度
                    confidence = self._calculate_keyword_confidence(keyword, all_snippets, "age")
                    # 计算证据质量
                    evidence = [snippet for snippet in all_snippets if keyword in snippet.lower()][:3]
                    evidence_quality = self._assess_evidence_quality(evidence, "age")
                    return self._feature_value(
                        {"age_group": age_group},
                        evidence,
                        {"matched_keyword": keyword, "confidence": confidence},
                        confidence=confidence,
                        evidence_quality=evidence_quality,
                    )

        # 如果没有明确的年龄段关键词，尝试从生育状态推断
        fertility_status = life_stage.get("value", {}).get("life_stage", "Unknown")
        if fertility_status in ["备孕中", "怀孕中", "已育1孩", "已育2孩+"]:
            # 生育状态推断年龄段
            if fertility_status in ["备孕中", "怀孕中"]:
                return self._feature_value(
                    {"age_group": "30-34"},
                    ["inferred_from_fertility_status"],
                    {"matched_keyword": "fertility_inference", "confidence": 0.6},
                    confidence=0.6,
                    evidence_quality={"relevance": 0.5, "timeliness": 0.5, "credibility": 0.5, "overall": 0.5},
                )
            elif fertility_status in ["已育1孩", "已育2孩+"]:
                return self._feature_value(
                    {"age_group": "30-34"},
                    ["inferred_from_fertility_status"],
                    {"matched_keyword": "fertility_inference", "confidence": 0.6},
                    confidence=0.6,
                    evidence_quality={"relevance": 0.5, "timeliness": 0.5, "credibility": 0.5, "overall": 0.5},
                )
        elif fertility_status == "未婚":
            # 未婚状态推断年龄段
            return self._feature_value(
                {"age_group": "25-29"},
                ["inferred_from_life_stage"],
                {"matched_keyword": "life_stage_inference", "confidence": 0.5},
                confidence=0.5,
                evidence_quality={"relevance": 0.4, "timeliness": 0.4, "credibility": 0.4, "overall": 0.4},
            )
        elif fertility_status == "已婚未育":
            # 已婚未育推断年龄段
            return self._feature_value(
                {"age_group": "25-29"},
                ["inferred_from_life_stage"],
                {"matched_keyword": "life_stage_inference", "confidence": 0.5},
                confidence=0.5,
                evidence_quality={"relevance": 0.4, "timeliness": 0.4, "credibility": 0.4, "overall": 0.4},
            )

        return self._feature_value(
            {"age_group": "Unknown"},
            ["fallback:insufficient_evidence"],
            {"matched_keyword": None, "confidence": 0.0},
            confidence=0.0,
            evidence_quality={"relevance": 0.0, "timeliness": 0.0, "credibility": 0.0, "overall": 0.0},
        )

    def _fertility_clues(
        self,
        profile: Dict[str, Any],
        posts: List[Dict[str, Any]],
        all_snippets: List[str],
        life_stage: Dict[str, Any],
    ) -> Dict[str, Any]:
        """生育意愿识别（优化版 - 大幅扩展关键词和交叉验证）"""
        merged = " ".join(all_snippets).lower()
        
        # 统计各类型关键词
        positive_count = 0
        negative_count = 0
        neutral_count = 0
        evidence_positive = []
        evidence_negative = []
        evidence_neutral = []

        # 正面关键词匹配
        for keyword in self.fertility_intent_keywords["正面"]:
            if keyword in merged:
                positive_count += 1
                for snippet in all_snippets:
                    if keyword in snippet.lower() and len(evidence_positive) < 2:
                        evidence_positive.append(snippet)

        # 负面关键词匹配（增加权重）
        for keyword in self.fertility_intent_keywords["负面"]:
            if keyword in merged:
                # 负面情绪关键词权重更高
                if keyword in ["焦虑", "担忧", "害怕", "恐惧", "后悔", "累", "疲惫", "崩溃", "绝望"]:
                    negative_count += 2  # 双倍权重
                else:
                    negative_count += 1
                for snippet in all_snippets:
                    if keyword in snippet.lower() and len(evidence_negative) < 2:
                        evidence_negative.append(snippet)

        # 中性关键词匹配
        for keyword in self.fertility_intent_keywords["中性"]:
            if keyword in merged:
                neutral_count += 1
                for snippet in all_snippets:
                    if keyword in snippet.lower() and len(evidence_neutral) < 2:
                        evidence_neutral.append(snippet)

        # 从生育状态推断生育意愿（增强版）
        fertility_status = life_stage.get("value", {}).get("life_stage", "Unknown")
        if fertility_status in ["备孕中", "怀孕中"]:
            # 备孕/怀孕状态，生育意愿为正面
            positive_count += 5  # 增加权重
            evidence_positive.append("inferred_from_fertility_status: " + fertility_status)
        elif fertility_status in ["已育1孩", "已育2孩+"]:
            # 已育状态，生育意愿为正面
            positive_count += 4  # 增加权重
            evidence_positive.append("inferred_from_fertility_status: " + fertility_status)
        elif fertility_status == "未婚":
            # 未婚状态，检查是否有丁克倾向
            if any(kw in merged for kw in ["丁克", "不要孩子", "不想生", "讨厌小孩"]):
                negative_count += 3
                evidence_negative.append("inferred_from_life_stage: 未婚+丁克")
            else:
                neutral_count += 2
                evidence_neutral.append("inferred_from_life_stage: 未婚")
        elif fertility_status == "已婚未育":
            # 已婚未育状态，生育意愿为中性
            neutral_count += 2
            evidence_neutral.append("inferred_from_life_stage: 已婚未育")

        # 从空间偏好推断生育意愿（新增）
        spatial_preferences = self._infer_spatial_from_snippets(all_snippets)
        if "医疗资源" in spatial_preferences:
            # 关注医疗资源，可能与生育相关
            positive_count += 1
        if "教育资源" in spatial_preferences:
            # 关注教育资源，可能与育儿相关
            positive_count += 1

        # 从消费水平推断生育意愿（新增）
        consumption_level = self._infer_consumption_from_snippets(all_snippets)
        if consumption_level == "High":
            # 高收入，可能更有能力生育
            positive_count += 1
        elif consumption_level == "Low":
            # 低收入，可能对生育有顾虑
            negative_count += 1

        # 从帖子内容推断生育意愿（新增）
        negative_post_count = self._count_negative_posts(all_snippets)
        if negative_post_count >= 3:
            # 多个负面帖子，可能对生育有顾虑
            negative_count += negative_post_count

        # 判断生育意愿（优化逻辑）
        if positive_count > negative_count and positive_count > neutral_count:
            intent = "positive"
            # 评分算法优化：基础分 + 正面信号 - 负面信号
            score = min(5, max(0, 3 + positive_count - negative_count))
            evidence = evidence_positive[:3]
            # 计算置信度
            confidence = self._calculate_fertility_confidence(positive_count, negative_count, neutral_count, "positive")
        elif negative_count > positive_count and negative_count > neutral_count:
            intent = "negative"
            score = max(0, min(5, 2 - negative_count + positive_count))
            evidence = evidence_negative[:3]
            # 计算置信度
            confidence = self._calculate_fertility_confidence(positive_count, negative_count, neutral_count, "negative")
        elif neutral_count > 0:
            intent = "neutral"
            score = 2
            evidence = evidence_neutral[:3]
            # 计算置信度
            confidence = self._calculate_fertility_confidence(positive_count, negative_count, neutral_count, "neutral")
        else:
            intent = "unknown"
            score = 0
            evidence = ["fallback:insufficient_evidence"]
            confidence = 0.0
        
        # 计算证据质量
        evidence_quality = self._assess_evidence_quality(evidence, "fertility")

        return self._feature_value(
            {"fertility_intent": intent, "fertility_score": score},
            evidence,
            {
                "positive_signals": positive_count,
                "negative_signals": negative_count,
                "neutral_signals": neutral_count,
            },
            confidence=confidence,
            evidence_quality=evidence_quality,
        )

    def _infer_spatial_from_snippets(self, snippets: List[str]) -> List[str]:
        """从文本片段推断空间偏好"""
        merged = " ".join(snippets).lower()
        matched = []
        
        for preference, keywords in self.spatial_keywords.items():
            for keyword in keywords:
                if keyword in merged:
                    if preference not in matched:
                        matched.append(preference)
                    break
        
        return matched

    def _infer_consumption_from_snippets(self, snippets: List[str]) -> str:
        """从文本片段推断消费水平"""
        merged = " ".join(snippets).lower()
        
        high_count = 0
        low_count = 0
        
        for keyword in self.income_keywords["高"]:
            if keyword in merged:
                high_count += 1
        
        for keyword in self.income_keywords["低"]:
            if keyword in merged:
                low_count += 1
        
        if high_count > low_count and high_count >= 2:
            return "High"
        elif low_count > high_count and low_count >= 2:
            return "Low"
        else:
            return "Medium"

    def _count_negative_posts(self, snippets: List[str]) -> int:
        """统计负面帖子数量"""
        negative_keywords = [
            "焦虑", "担忧", "害怕", "恐惧", "后悔",
            "累", "疲惫", "崩溃", "绝望", "压力",
            "负担", "养不起", "经济压力", "生活压力",
        ]
        
        count = 0
        for snippet in snippets:
            if any(keyword in snippet.lower() for keyword in negative_keywords):
                count += 1
        
        return count

    def _assess_evidence_quality(self, evidence: List[str], feature_type: str) -> Dict[str, float]:
        """评估证据质量"""
        if not evidence or evidence == ["fallback:insufficient_evidence"]:
            return {"relevance": 0.0, "timeliness": 0.0, "credibility": 0.0, "overall": 0.0}
        
        # 相关性评估
        relevance = self._assess_relevance(evidence, feature_type)
        
        # 时效性评估
        timeliness = self._assess_timeliness(evidence)
        
        # 可信度评估
        credibility = self._assess_credibility(evidence, feature_type)
        
        # 整体质量
        overall = (relevance + timeliness + credibility) / 3
        
        return {
            "relevance": round(relevance, 2),
            "timeliness": round(timeliness, 2),
            "credibility": round(credibility, 2),
            "overall": round(overall, 2),
        }

    def _assess_relevance(self, evidence: List[str], feature_type: str) -> float:
        """评估证据相关性"""
        if not evidence:
            return 0.0
        
        # 根据特征类型评估相关性
        relevance_scores = []
        
        for snippet in evidence:
            score = 0.5  # 基础分
            
            # 根据特征类型调整
            if feature_type == "fertility":
                # 生育相关证据
                if any(kw in snippet.lower() for kw in ["备孕", "怀孕", "宝宝", "孩子", "育儿"]):
                    score = 0.9
                elif any(kw in snippet.lower() for kw in ["家庭", "生活", "日常"]):
                    score = 0.7
            elif feature_type == "life_stage":
                # 生活阶段证据
                if any(kw in snippet.lower() for kw in ["单身", "结婚", "已婚", "未婚"]):
                    score = 0.9
                elif any(kw in snippet.lower() for kw in ["恋爱", "相亲", "找对象"]):
                    score = 0.7
            elif feature_type == "spatial":
                # 空间偏好证据
                if any(kw in snippet.lower() for kw in ["地铁", "通勤", "公园", "医院", "学校"]):
                    score = 0.9
                elif any(kw in snippet.lower() for kw in ["安全", "便利", "配套"]):
                    score = 0.7
            elif feature_type == "consumption":
                # 消费水平证据
                if any(kw in snippet.lower() for kw in ["奢侈", "高端", "平价", "省钱"]):
                    score = 0.9
                elif any(kw in snippet.lower() for kw in ["消费", "购物", "生活"]):
                    score = 0.7
            elif feature_type == "age":
                # 年龄段证据
                if any(kw in snippet.lower() for kw in ["大学", "工作", "备孕", "怀孕", "宝宝"]):
                    score = 0.9
                elif any(kw in snippet.lower() for kw in ["年轻", "青春", "事业", "家庭"]):
                    score = 0.7
            elif feature_type == "activity":
                # 活跃度证据
                if any(kw in snippet.lower() for kw in ["帖子", "点赞", "收藏", "关注"]):
                    score = 0.9
                elif any(kw in snippet.lower() for kw in ["互动", "活跃", "分享"]):
                    score = 0.7
            
            relevance_scores.append(score)
        
        return sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0.0

    def _assess_timeliness(self, evidence: List[str]) -> float:
        """评估证据时效性"""
        if not evidence:
            return 0.0
        
        # 检查是否包含时间相关关键词
        time_keywords = ["今天", "昨天", "最近", "刚刚", "现在", "目前", "当前"]
        recent_keywords = ["本月", "今年", "这周", "上周", "上个月"]
        
        timeliness_scores = []
        
        for snippet in evidence:
            score = 0.5  # 基础分
            
            # 检查时间关键词
            if any(kw in snippet.lower() for kw in time_keywords):
                score = 0.9
            elif any(kw in snippet.lower() for kw in recent_keywords):
                score = 0.7
            elif any(kw in snippet.lower() for kw in ["去年", "前年", "以前", "过去"]):
                score = 0.3
            
            timeliness_scores.append(score)
        
        return sum(timeliness_scores) / len(timeliness_scores) if timeliness_scores else 0.0

    def _assess_credibility(self, evidence: List[str], feature_type: str) -> float:
        """评估证据可信度"""
        if not evidence:
            return 0.0
        
        credibility_scores = []
        
        for snippet in evidence:
            score = 0.5  # 基础分
            
            # 证据长度
            if len(snippet) > 50:
                score += 0.1
            if len(snippet) > 100:
                score += 0.1
            
            # 证据来源（根据特征类型）
            if feature_type == "identity":
                # 身份证据
                if any(kw in snippet.lower() for kw in ["小红书号", "IP属地", "简介"]):
                    score += 0.2
            elif feature_type == "fertility":
                # 生育证据
                if any(kw in snippet.lower() for kw in ["备孕", "怀孕", "宝宝", "育儿"]):
                    score += 0.2
            elif feature_type == "spatial":
                # 空间证据
                if any(kw in snippet.lower() for kw in ["地铁", "公园", "医院", "学校"]):
                    score += 0.2
            
            # 证据一致性（检查是否包含矛盾信息）
            if self._check_evidence_consistency(snippet, feature_type):
                score += 0.1
            
            credibility_scores.append(min(1.0, score))
        
        return sum(credibility_scores) / len(credibility_scores) if credibility_scores else 0.0

    def _check_evidence_consistency(self, snippet: str, feature_type: str) -> bool:
        """检查证据一致性"""
        snippet_lower = snippet.lower()
        
        # 检查矛盾信息
        if feature_type == "fertility":
            # 生育相关矛盾
            positive_keywords = ["备孕", "怀孕", "宝宝", "孩子", "育儿"]
            negative_keywords = ["丁克", "不生", "不要孩子", "讨厌小孩"]
            
            has_positive = any(kw in snippet_lower for kw in positive_keywords)
            has_negative = any(kw in snippet_lower for kw in negative_keywords)
            
            # 如果同时包含正面和负面关键词，则不一致
            if has_positive and has_negative:
                return False
        
        elif feature_type == "life_stage":
            # 生活阶段矛盾
            single_keywords = ["单身", "未婚", "一个人"]
            married_keywords = ["结婚", "已婚", "老公", "老婆"]
            
            has_single = any(kw in snippet_lower for kw in single_keywords)
            has_married = any(kw in snippet_lower for kw in married_keywords)
            
            # 如果同时包含单身和已婚关键词，则不一致
            if has_single and has_married:
                return False
        
        return True

    def _calculate_keyword_confidence(self, keyword: str, snippets: List[str], keyword_type: str) -> float:
        """计算关键词匹配置信度"""
        # 基础置信度
        base_confidence = 0.7
        
        # 根据关键词类型调整
        if keyword_type == "fertility":
            # 生育相关关键词置信度更高
            base_confidence = 0.9
        elif keyword_type == "life_stage":
            # 生活阶段关键词置信度中等
            base_confidence = 0.8
        elif keyword_type == "age":
            # 年龄段关键词置信度较低
            base_confidence = 0.7
        
        # 根据证据数量调整
        evidence_count = sum(1 for snippet in snippets if keyword in snippet.lower())
        if evidence_count >= 3:
            base_confidence = min(1.0, base_confidence + 0.1)
        elif evidence_count >= 2:
            base_confidence = min(1.0, base_confidence + 0.05)
        
        return base_confidence

    def _calculate_spatial_confidence(self, matched: List[str], evidence_map: Dict[str, List[str]]) -> float:
        """计算空间偏好置信度"""
        if not matched or matched[0] == "Unknown":
            return 0.0
        
        # 基础置信度
        base_confidence = 0.6
        
        # 根据匹配数量调整
        if len(matched) >= 3:
            base_confidence = min(1.0, base_confidence + 0.2)
        elif len(matched) >= 2:
            base_confidence = min(1.0, base_confidence + 0.1)
        
        # 根据证据数量调整
        total_evidence = sum(len(evidence) for evidence in evidence_map.values())
        if total_evidence >= 6:
            base_confidence = min(1.0, base_confidence + 0.1)
        elif total_evidence >= 4:
            base_confidence = min(1.0, base_confidence + 0.05)
        
        return base_confidence

    def _calculate_fertility_confidence(
        self,
        positive_count: int,
        negative_count: int,
        neutral_count: int,
        intent: str,
    ) -> float:
        """计算生育意愿置信度"""
        # 基础置信度
        base_confidence = 0.5
        
        # 根据信号强度调整
        total_signals = positive_count + negative_count + neutral_count
        if total_signals >= 10:
            base_confidence = min(1.0, base_confidence + 0.3)
        elif total_signals >= 5:
            base_confidence = min(1.0, base_confidence + 0.2)
        elif total_signals >= 3:
            base_confidence = min(1.0, base_confidence + 0.1)
        
        # 根据信号差异调整
        if intent == "positive":
            if positive_count > negative_count * 2:
                base_confidence = min(1.0, base_confidence + 0.2)
            elif positive_count > negative_count * 1.5:
                base_confidence = min(1.0, base_confidence + 0.1)
        elif intent == "negative":
            if negative_count > positive_count * 2:
                base_confidence = min(1.0, base_confidence + 0.2)
            elif negative_count > positive_count * 1.5:
                base_confidence = min(1.0, base_confidence + 0.1)
        
        return base_confidence

    def _calculate_overall_confidence(
        self,
        identity: Dict[str, Any],
        life_stage: Dict[str, Any],
        spatial: Dict[str, Any],
        consumption: Dict[str, Any],
        activity: Dict[str, Any],
        age: Dict[str, Any],
        fertility: Dict[str, Any],
    ) -> float:
        """计算整体置信度"""
        confidences = [
            identity.get("confidence", 0.0),
            life_stage.get("confidence", 0.0),
            spatial.get("confidence", 0.0),
            consumption.get("confidence", 0.0),
            activity.get("confidence", 0.0),
            age.get("confidence", 0.0),
            fertility.get("confidence", 0.0),
        ]
        
        # 过滤掉 None 值
        valid_confidences = [c for c in confidences if c is not None]
        
        if not valid_confidences:
            return 0.0
        
        # 计算加权平均置信度
        # 生育状态和生育意愿权重更高
        weights = [1.0, 1.5, 1.0, 1.0, 0.5, 1.0, 1.5]
        weighted_sum = sum(c * w for c, w in zip(valid_confidences, weights[:len(valid_confidences)]))
        total_weight = sum(weights[:len(valid_confidences)])
        
        return round(weighted_sum / total_weight, 2) if total_weight > 0 else 0.0

    def _calculate_evidence_quality(
        self,
        identity: Dict[str, Any],
        life_stage: Dict[str, Any],
        spatial: Dict[str, Any],
        consumption: Dict[str, Any],
        activity: Dict[str, Any],
        age: Dict[str, Any],
        fertility: Dict[str, Any],
    ) -> Dict[str, Any]:
        """计算整体证据质量"""
        qualities = [
            identity.get("evidence_quality", {}).get("overall", 0.0),
            life_stage.get("evidence_quality", {}).get("overall", 0.0),
            spatial.get("evidence_quality", {}).get("overall", 0.0),
            consumption.get("evidence_quality", {}).get("overall", 0.0),
            activity.get("evidence_quality", {}).get("overall", 0.0),
            age.get("evidence_quality", {}).get("overall", 0.0),
            fertility.get("evidence_quality", {}).get("overall", 0.0),
        ]
        
        # 过滤掉 None 值
        valid_qualities = [q for q in qualities if q is not None]
        
        if not valid_qualities:
            return {"overall": 0.0, "relevance": 0.0, "timeliness": 0.0, "credibility": 0.0}
        
        # 计算平均质量
        overall = sum(valid_qualities) / len(valid_qualities)
        
        # 计算各维度平均质量
        relevance_scores = [
            identity.get("evidence_quality", {}).get("relevance", 0.0),
            life_stage.get("evidence_quality", {}).get("relevance", 0.0),
            spatial.get("evidence_quality", {}).get("relevance", 0.0),
            consumption.get("evidence_quality", {}).get("relevance", 0.0),
            activity.get("evidence_quality", {}).get("relevance", 0.0),
            age.get("evidence_quality", {}).get("relevance", 0.0),
            fertility.get("evidence_quality", {}).get("relevance", 0.0),
        ]
        
        timeliness_scores = [
            identity.get("evidence_quality", {}).get("timeliness", 0.0),
            life_stage.get("evidence_quality", {}).get("timeliness", 0.0),
            spatial.get("evidence_quality", {}).get("timeliness", 0.0),
            consumption.get("evidence_quality", {}).get("timeliness", 0.0),
            activity.get("evidence_quality", {}).get("timeliness", 0.0),
            age.get("evidence_quality", {}).get("timeliness", 0.0),
            fertility.get("evidence_quality", {}).get("timeliness", 0.0),
        ]
        
        credibility_scores = [
            identity.get("evidence_quality", {}).get("credibility", 0.0),
            life_stage.get("evidence_quality", {}).get("credibility", 0.0),
            spatial.get("evidence_quality", {}).get("credibility", 0.0),
            consumption.get("evidence_quality", {}).get("credibility", 0.0),
            activity.get("evidence_quality", {}).get("credibility", 0.0),
            age.get("evidence_quality", {}).get("credibility", 0.0),
            fertility.get("evidence_quality", {}).get("credibility", 0.0),
        ]
        
        valid_relevance = [r for r in relevance_scores if r is not None]
        valid_timeliness = [t for t in timeliness_scores if t is not None]
        valid_credibility = [c for c in credibility_scores if c is not None]
        
        return {
            "overall": round(overall, 2),
            "relevance": round(sum(valid_relevance) / len(valid_relevance), 2) if valid_relevance else 0.0,
            "timeliness": round(sum(valid_timeliness) / len(valid_timeliness), 2) if valid_timeliness else 0.0,
            "credibility": round(sum(valid_credibility) / len(valid_credibility), 2) if valid_credibility else 0.0,
        }

    def _generate_evidence_visualization(
        self,
        identity: Dict[str, Any],
        life_stage: Dict[str, Any],
        spatial: Dict[str, Any],
        consumption: Dict[str, Any],
        activity: Dict[str, Any],
        age: Dict[str, Any],
        fertility: Dict[str, Any],
    ) -> Dict[str, Any]:
        """生成证据来源可视化数据"""
        # 特征类型映射
        feature_names = {
            "identity": "身份特征",
            "life_stage": "生活阶段",
            "spatial": "空间偏好",
            "consumption": "消费水平",
            "activity": "活跃度",
            "age": "年龄段",
            "fertility": "生育意愿",
        }
        
        # 收集各维度数据
        visualization_data = {
            "feature_confidence": {},
            "evidence_quality": {},
            "evidence_distribution": {},
            "signal_distribution": {},
        }
        
        # 特征置信度
        features = {
            "identity": identity,
            "life_stage": life_stage,
            "spatial": spatial,
            "consumption": consumption,
            "activity": activity,
            "age": age,
            "fertility": fertility,
        }
        
        for feature_key, feature in features.items():
            visualization_data["feature_confidence"][feature_names[feature_key]] = feature.get("confidence", 0.0)
        
        # 证据质量
        for feature_key, feature in features.items():
            evidence_quality = feature.get("evidence_quality", {})
            visualization_data["evidence_quality"][feature_names[feature_key]] = {
                "relevance": evidence_quality.get("relevance", 0.0),
                "timeliness": evidence_quality.get("timeliness", 0.0),
                "credibility": evidence_quality.get("credibility", 0.0),
                "overall": evidence_quality.get("overall", 0.0),
            }
        
        # 证据分布
        for feature_key, feature in features.items():
            evidence = feature.get("evidence", [])
            if evidence and evidence != ["fallback:insufficient_evidence"]:
                visualization_data["evidence_distribution"][feature_names[feature_key]] = {
                    "count": len(evidence),
                    "sources": evidence[:3],
                }
        
        # 信号分布（仅生育意愿）
        fertility_stats = fertility.get("stats", {})
        visualization_data["signal_distribution"] = {
            "positive": fertility_stats.get("positive_signals", 0),
            "negative": fertility_stats.get("negative_signals", 0),
            "neutral": fertility_stats.get("neutral_signals", 0),
        }
        
        # 生成可视化摘要
        visualization_data["summary"] = self._generate_visualization_summary(visualization_data)
        
        return visualization_data

    def _generate_visualization_summary(self, visualization_data: Dict[str, Any]) -> Dict[str, Any]:
        """生成可视化摘要"""
        # 特征置信度排名
        confidence_ranking = sorted(
            visualization_data["feature_confidence"].items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        # 证据质量排名
        quality_ranking = sorted(
            visualization_data["evidence_quality"].items(),
            key=lambda x: x[1]["overall"],
            reverse=True
        )
        
        # 信号分布
        signal_dist = visualization_data["signal_distribution"]
        total_signals = signal_dist["positive"] + signal_dist["negative"] + signal_dist["neutral"]
        
        return {
            "confidence_ranking": confidence_ranking,
            "quality_ranking": quality_ranking,
            "total_signals": total_signals,
            "dominant_signal": max(signal_dist, key=signal_dist.get),
            "signal_ratio": {
                "positive": round(signal_dist["positive"] / total_signals, 2) if total_signals > 0 else 0.0,
                "negative": round(signal_dist["negative"] / total_signals, 2) if total_signals > 0 else 0.0,
                "neutral": round(signal_dist["neutral"] / total_signals, 2) if total_signals > 0 else 0.0,
            },
        }

    def _feature_value(
        self,
        value: Dict[str, Any],
        evidence: List[str],
        stats: Dict[str, Any],
        confidence: float = 0.0,
        evidence_quality: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        return {
            "value": value,
            "evidence": evidence if evidence else ["fallback:insufficient_evidence"],
            "stats": stats,
            "is_fallback": len(evidence) == 0,
            "confidence": confidence,
            "evidence_quality": evidence_quality or {"relevance": 0.0, "timeliness": 0.0, "credibility": 0.0, "overall": 0.0},
        }

    def _completeness(self, features: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        missing: List[str] = []
        for key, feature in features.items():
            if feature.get("is_fallback"):
                missing.append(key)
        total = len(features)
        score = round((total - len(missing)) / total, 2) if total else 0
        return {
            "score": score,
            "missing_feature_keys": missing,
            "is_complete": len(missing) == 0,
        }

    def _evidence_references(self, features: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        refs: List[Dict[str, Any]] = []
        for feature_key, feature in features.items():
            for idx, snippet in enumerate(feature.get("evidence", [])[:3]):
                refs.append(
                    {
                        "feature_key": feature_key,
                        "evidence_id": f"{feature_key}_{idx}",
                        "snippet": snippet,
                    }
                )
        return refs


def legacy_profile_posts_to_feature_profile(profile: Dict[str, Any], posts: List[Dict[str, Any]]) -> Dict[str, Any]:
    raw = {
        "account_id": str(profile.get("id", "")),
        "raw_data": {
            "profile": profile,
            "posts": posts,
            "likes": [],
            "favorites": [],
            "follows": [],
        },
    }
    return AccountFeatureBuilder().build(raw)
