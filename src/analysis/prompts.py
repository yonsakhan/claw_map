from langchain_core.prompts import ChatPromptTemplate

# ============================================================
# 原版英文 Prompt（保留向后兼容）
# ============================================================

PERSONA_EXTRACTION_PROMPT = ChatPromptTemplate.from_template("""
You are an expert social science researcher. Your task is to analyze a user's social media profile and posts to construct a "Digital Persona" for fertility research.

User Profile:
{profile_json}

Recent Posts:
{posts_json}

Based on the above information, infer the following attributes. If an attribute cannot be inferred with confidence, use "Unknown".

1. **Age Group**: (e.g., "18-24", "25-29", "30-34", "35-39", "40+")
2. **Location**: (City and District if available)
3. **Fertility Status**: (e.g., "Unmarried", "Married-No-Kids", "Pregnant", "Parent-1-Child", "Parent-2-Child+")
4. **Estimated Income Level**: (Based on lifestyle, spending, brands mentioned. "Low", "Medium", "High")
5. **Spatial Preferences**: (What urban elements do they care about? e.g., "Commute time", "Parks", "Hospitals", "Schools", "Safety")
6. **Fertility Intent Score**: (0-5, where 0 is strongly against having kids/more kids, 5 is actively planning. Infer from sentiment.)

Output the result in valid JSON format only, with no markdown formatting. The JSON keys should be:
"age_group", "location", "fertility_status", "income_level", "spatial_preferences" (list of strings), "fertility_intent_score" (int).
""")

ACCOUNT_FEATURE_QUESTIONNAIRE_PROMPT = ChatPromptTemplate.from_template("""
You are an expert social science researcher for fertility-friendly urban planning.

Account Feature Profile:
{account_feature_profile_json}

Questionnaire Context:
{questionnaire_context_json}

Model Parameters:
{model_params_json}

Generate one valid JSON object with these keys:
- age_group (string)
- location (string)
- fertility_status (string)
- income_level (string)
- spatial_preferences (array of strings)
- fertility_intent_score (integer 0-5)
- questionnaire_answers (array of objects with question_id, question, answer, reason_summary, tendency_score, confidence)
- reasoning_summary (string)

Rules:
1) Infer from feature clues and evidence snippets only.
2) If uncertain, set value to "Unknown" and lower confidence.
3) Keep answers concise and structured.
4) Output valid JSON only without markdown.
""")


# ============================================================
# 新增：小红书中文语境优化版 Prompt（提升准确度版）
# ============================================================

XHS_PERSONA_EXTRACTION_PROMPT = ChatPromptTemplate.from_template("""
你是一位资深社会学研究员，专注于超大城市生育友好型空间研究。请基于以下用户特征画像，进行精准的生育意愿推断。

## 用户特征画像
{account_feature_profile_json}

## 问卷上下文
{questionnaire_context_json}

## 模型参数
{model_params_json}

## 分析任务

请基于特征画像中的**证据片段**，进行多维度交叉验证推断。**必须基于文本证据，不要臆测。**

### 推断规则

#### 1. 年龄段推断（必须结合多个证据）
- **18-24岁**：出现"大学"、"考研"、"应届"、"实习"、"毕业"、"校园"、"宿舍"等关键词
- **25-29岁**：出现"工作"、"职场"、"加班"、"升职"、"跳槽"、"租房"、"独居"等关键词
- **30-34岁**：出现"备孕"、"怀孕"、"宝宝"、"育儿"、"家庭"、"事业"、"稳定"等关键词
- **35-39岁**：出现"二胎"、"高龄"、"35岁"、"中年危机"、"孩子上学"等关键词
- **40+岁**：出现"孩子上学"、"中考"、"高考"、"青春期"、"更年期"等关键词

**交叉验证**：如果年龄与生育状态矛盾（如18-24岁但已育2孩），需要重新评估。

#### 2. 生育状态推断（按优先级排序）
- **备孕中**（优先级最高）：
  * 强信号：备孕、排卵、验孕、造人、排卵试纸、基础体温、叶酸
  * 弱信号：期待小生命、准备要孩子、计划怀孕
- **怀孕中**：
  * 强信号：怀孕、孕检、产检、胎动、孕吐、孕期、NT检查、唐筛、四维
  * 弱信号：孕妇、孕妈、待产、预产期
- **已育1孩**：
  * 强信号：宝宝、婴儿、奶粉、辅食、月子、产后、新生儿
  * 弱信号：育儿、带娃、遛娃、一岁、两岁、三岁
- **已育2孩+**：
  * 强信号：大宝、二宝、三宝、俩娃、二胎、三胎、双胞胎
  * 弱信号：老大、老二、哥哥、姐姐、弟弟、妹妹
- **已婚未育**：
  * 强信号：结婚、老公、老婆、丈夫、妻子、已婚、婚礼
  * 弱信号：二人世界、夫妻、结婚纪念日
- **未婚**：
  * 强信号：单身、一个人、独居、没有男朋友
  * 弱信号：相亲、找对象、谈恋爱

#### 3. 收入水平推断（需要多个信号交叉验证）
- **高收入**（至少2个信号）：
  * 生活方式：奢侈品、高端、五星、名牌、豪华
  * 医疗选择：私立医院、月子中心、VIP
  * 教育选择：国际学校、海外、进口
  * 消费习惯：定制、限量、高尔夫、马术、滑雪
- **低收入**（至少2个信号）：
  * 消费习惯：平价、省钱、优惠、折扣、团购、打折、促销
  * 生活压力：分期、贷款、负债、月光
  * 购物平台：拼多多、淘宝、二手、闲置
- **中等收入**：无明显高低收入信号

#### 4. 空间偏好推断（基于实际需求场景）
- **通勤便利**：
  * 通勤场景：地铁、通勤、上班、挤地铁、公交、打车
  * 时间成本：早高峰、晚高峰、通勤时间、换乘
  * 距离相关：地铁站、公交站、通勤距离
- **公园绿地**：
  * 休闲需求：公园、遛娃、户外、绿地、散步、跑步
  * 环境需求：小区绿化、花园、植物园、森林公园
  * 自然接触：河边、湖边、海边、爬山、徒步
- **医疗资源**：
  * 孕产需求：医院、产检、妇幼保健院、儿童医院
  * 日常医疗：儿科、看病、挂号、门诊、社区医院
  * 健康管理：体检、疫苗、打针、吃药、保健
- **教育资源**：
  * 学前教育：幼儿园、托班、早教
  * 基础教育：小学、中学、高中、学区
  * 课外培训：培训班、兴趣班、辅导班、家教
- **生活配套**：
  * 购物需求：超市、商场、便利店、菜市场、生鲜
  * 生活服务：外卖、快递、洗衣、理发
  * 金融服务：银行、ATM
- **出行安全**：
  * 人身安全：安全、治安、监控、路灯、保安
  * 出行便利：门禁、小区安全、夜间出行
  * 特殊群体：女性安全、独居安全
- **居住空间**：
  * 住房需求：房子、户型、面积、租房、买房
  * 居住环境：装修、家具、收纳、阳台
  * 空间功能：卧室、客厅、厨房、卫生间

#### 5. 生育意愿评分（0-5分，必须有明确证据）
- **0分**（明确拒绝）：
  * 关键词：丁克、不生、不要孩子、讨厌小孩、不喜欢小孩
  * 语境：明确表示不打算生育
- **1分**（强烈顾虑）：
  * 关键词：压力大、养不起、不想生、恐婚恐育
  * 语境：对生育有明显负面情绪
- **2分**（犹豫观望）：
  * 关键词：还在考虑、看情况、顺其自然、不着急、还没想好
  * 语境：对生育持中立态度
- **3分**（有一定意愿）：
  * 关键词：以后会生、计划中、可能会生
  * 语境：对生育有初步想法
- **4分**（积极准备）：
  * 关键词：备孕中、准备要孩子、计划怀孕、期待宝宝
  * 语境：正在为生育做准备
- **5分**（已育且满意）：
  * 关键词：幸福、值得、还想生、再生一个
  * 语境：对生育有正面体验

### 输出格式

**必须输出有效的 JSON，不要添加 markdown 格式或额外说明。**

JSON 结构示例：
- age_group: 字符串，如 "25-29"
- location: 字符串，如 "上海浦东"
- fertility_status: 字符串，如 "备孕中"
- income_level: 字符串，如 "中"
- spatial_preferences: 数组，如 ["通勤便利", "医疗资源"]
- fertility_intent_score: 整数，如 4
- confidence: 浮点数，如 0.85
- evidence_summary: 对象，包含 age_evidence, fertility_evidence, income_evidence, spatial_evidence
- reasoning_summary: 字符串，一句话概括判断依据

### 质量控制规则

1. **证据优先**：每个推断必须有至少1个证据片段支持
2. **交叉验证**：年龄与生育状态必须逻辑一致
3. **置信度标注**：对不确定的推断降低置信度
4. **避免臆测**：如果证据不足，填写"Unknown"
5. **保持简洁**：reasoning_summary 用一句话概括

**重要提醒：**
- 如果某个维度无法确定，填写 "Unknown"
- 不要臆测，必须基于文本证据
- reasoning_summary 用一句话概括判断依据
""")


# ============================================================
# 新增：带问卷的中文版 Prompt（提升准确度版）
# ============================================================

XHS_QUESTIONNAIRE_PROMPT = ChatPromptTemplate.from_template("""
你是一位资深社会学研究员，专注于超大城市生育友好型空间研究。请基于以下用户特征画像和问卷上下文，进行精准的生育意愿推断。

## 用户特征画像
{account_feature_profile_json}

## 问卷上下文
{questionnaire_context_json}

## 模型参数
{model_params_json}

## 分析任务

基于用户特征画像和问卷上下文，生成生育意愿分析结果。**必须基于文本证据，不要臆测。**

### 推断规则

#### 1. 年龄段推断
- 基于特征画像中的年龄线索
- 结合问卷回答中的相关信息
- 交叉验证一致性

#### 2. 生育状态推断
- 优先使用特征画像中的生育状态
- 结合问卷回答验证
- 注意生育状态的时序性

#### 3. 收入水平推断
- 基于消费特征和生活方式
- 结合问卷中的经济状况
- 避免主观臆断

#### 4. 空间偏好推断
- 基于特征画像中的空间偏好
- 结合问卷中的居住需求
- 考虑实际生活场景

#### 5. 生育意愿评分
- 综合特征画像和问卷回答
- 考虑生育状态的影响
- 提供置信度评估

### 输出格式

**必须输出有效的 JSON，不要添加 markdown 格式或额外说明。**

JSON 结构示例：
- age_group: 字符串，如 "25-29"
- location: 字符串，如 "上海浦东"
- fertility_status: 字符串，如 "备孕中"
- income_level: 字符串，如 "中"
- spatial_preferences: 数组，如 ["通勤便利", "医疗资源"]
- fertility_intent_score: 整数，如 4
- confidence: 浮点数，如 0.85
- questionnaire_answers: 数组，包含问题答案
- evidence_summary: 对象，包含 age_evidence, fertility_evidence, income_evidence, spatial_evidence
- reasoning_summary: 字符串，一句话概括判断依据

### 质量控制规则

1. **证据优先**：每个推断必须有证据支持
2. **交叉验证**：特征画像与问卷回答必须一致
3. **置信度标注**：对不确定的推断降低置信度
4. **避免臆测**：如果证据不足，填写"Unknown"
5. **保持简洁**：reasoning_summary 用一句话概括

### 评分说明
- tendency_score: 1-5分，表示用户对该问题的倾向程度
- confidence: 0-1，表示推断的置信度

### 规则
1. 只基于特征线索和证据片段推断
2. 如果不确定，填写 "Unknown" 并降低 confidence
3. 保持回答简洁、结构化
""")


# ============================================================
# 新增：特征提取专用 Prompt（提升准确度版）
# ============================================================

FEATURE_EXTRACTION_PROMPT = ChatPromptTemplate.from_template("""
你是一位资深数据分析师，专注于小红书用户行为分析。请基于以下用户资料，提取结构化特征。

## 用户资料
{profile_json}

## 笔记内容
{posts_json}

## 提取任务

请提取以下特征，每个特征都需要提供**证据片段**和**置信度**。

### 1. 身份特征
- display_name: 用户昵称
- location: 所在城市（从笔记、IP属地推断）
- bio: 个人简介
- evidence: 支持判断的文本片段（最多3条）

### 2. 生活阶段特征
- life_stage: 未婚 / 已婚未育 / 备孕中 / 怀孕中 / 已育1孩 / 已育2孩+
- evidence: 支持判断的文本片段（最多3条）
- confidence: 推断置信度（0-1）

### 3. 空间偏好特征
- top_preferences: 最关注的空间要素（最多3个）
  * 通勤便利 / 公园绿地 / 医疗资源 / 教育资源 / 生活配套 / 出行安全 / 居住空间
- evidence: 支持判断的文本片段（最多4条）
- confidence: 推断置信度（0-1）

### 4. 消费特征
- consumption_level: 低 / 中 / 高
- evidence: 支持判断的文本片段（最多3条）
- confidence: 推断置信度（0-1）

### 5. 活跃度特征
- activity_level: 低 / 中 / 高
- stats: 帖子数、点赞数、收藏数、关注数
- confidence: 推断置信度（0-1）

### 6. 年龄段特征（新增）
- age_group: 18-24 / 25-29 / 30-34 / 35-39 / 40+
- evidence: 支持判断的文本片段（最多3条）
- confidence: 推断置信度（0-1）

### 7. 生育意愿特征（新增）
- fertility_intent: 正面 / 负面 / 中性 / 未知
- fertility_score: 0-5分
- evidence: 支持判断的文本片段（最多3条）
- confidence: 推断置信度（0-1）

## 输出格式

**必须输出有效的 JSON，不要添加 markdown 格式或额外说明。**

JSON 结构示例：
- identity: 对象，包含 display_name, location, bio, evidence
- life_stage: 对象，包含 stage, evidence, confidence
- spatial_preferences: 对象，包含 top_preferences, evidence, confidence
- consumption: 对象，包含 level, evidence, confidence
- activity: 对象，包含 level, stats, confidence
- age_group: 对象，包含 group, evidence, confidence
- fertility_intent: 对象，包含 intent, score, evidence, confidence

### 质量控制规则

1. **证据优先**：每个特征必须有至少1个证据片段支持
2. **置信度标注**：根据证据强度标注置信度
3. **避免臆测**：如果证据不足，填写"Unknown"并降低置信度
4. **保持简洁**：证据片段必须是原文，不要改写
5. **结构清晰**：JSON 结构必须规范

**重要提醒：**
- 如果某个特征无法确定，填写 "Unknown"
- evidence 必须是原文片段，不要改写
- 保持 JSON 结构简洁
""")
