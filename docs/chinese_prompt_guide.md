# 中文 Prompt 优化说明

## 📋 概述

本次优化为 `claw_map` 项目新增了针对小红书中文语境的 Prompt 模板，专门用于生育意愿研究。

## 🎯 优化内容

### 1. 新增 Prompt 模板

| 模板名称 | 用途 | 输入变量 |
|---------|------|---------|
| `XHS_PERSONA_EXTRACTION_PROMPT` | 中文人设推断 | account_feature_profile_json, questionnaire_context_json, model_params_json |
| `XHS_QUESTIONNAIRE_PROMPT` | 中文问卷分析 | 同上 |
| `FEATURE_EXTRACTION_PROMPT` | 特征提取 | profile_json, posts_json |

### 2. 中文 Prompt 特点

#### 生育状态识别
- 备孕中：备孕、排卵、验孕、造人
- 怀孕中：怀孕、孕检、产检、胎动、孕吐
- 已育：宝宝、婴儿、奶粉、辅食、月子
- 已育2孩+：大宝、二宝、俩娃、三胎

#### 空间偏好识别
- 通勤便利：地铁、通勤、上班、挤地铁
- 公园绿地：公园、遛娃、户外、绿地
- 医疗资源：医院、产检、儿科、看病
- 教育资源：学校、幼儿园、学区、托班
- 生活配套：超市、商场、买菜、生活
- 出行安全：安全、夜路、人少、治安
- 居住空间：房子、户型、面积、搬家

#### 收入水平判断
- 高：奢侈品、高端、私立医院、月子中心
- 低：平价、省钱、团购、打折
- 中：其他情况

#### 生育意愿评分（0-5分）
- 0分：丁克、不生、讨厌小孩
- 1分：压力大、养不起、不想生
- 2分：还在考虑、看情况、顺其自然
- 3分：以后会生、计划中
- 4分：备孕中、准备要孩子
- 5分：幸福、值得、还想生

## 🚀 使用方法

### 1. 使用中文 Prompt（默认）

```python
from src.analysis.persona_extractor import PersonaExtractor

# 默认使用中文 Prompt
extractor = PersonaExtractor(
    api_key="your_api_key",
    use_chinese_prompt=True,  # 默认为 True
)

persona = extractor.extract_persona(profile, posts)
print(persona)
```

### 2. 使用英文 Prompt（向后兼容）

```python
from src.analysis.persona_extractor import PersonaExtractor

# 使用英文 Prompt
extractor = PersonaExtractor(
    api_key="your_api_key",
    use_chinese_prompt=False,
)

persona = extractor.extract_persona(profile, posts)
print(persona)
```

### 3. 批量处理

```python
from src.analysis.batch_processor import BatchProcessor

# 使用中文 Prompt 批量处理
processor = BatchProcessor(
    input_file="data.jsonl",
    output_file="personas.jsonl",
    use_chinese_prompt=True,  # 默认为 True
)

await processor.process(limit=100)
```

## 📊 测试结果

### 测试数据

```python
MOCK_PROFILE = {
    "id": "test_user_001",
    "display_name": "备孕小助手",
    "bio": "90后备孕中 | 分享备孕日常 | 期待小生命降临",
    "location": "上海",
}

MOCK_POSTS = [
    {"title": "备孕第3个月，分享我的排卵监测经验"},
    {"title": "上海哪家医院产检比较好？求推荐"},
    {"title": "每天挤地铁上班真的很累，但为了宝宝要坚持"},
    {"title": "开始准备婴儿用品了，买了好多小衣服"},
    {"title": "和老公商量了一下，决定明年要孩子"},
]
```

### 中文 Prompt 结果

```
年龄段：25-34
所在城市：上海
生育状态：备孕中
收入水平：中
空间偏好：['通勤便利', '医疗资源']
生育意愿评分：4
推断依据：用户笔记中提到'90后备孕中'，表明处于备孕阶段；同时关注通勤便利和医疗资源，如'每天挤地铁上班'和'上海哪家医院产检比较好'
```

### 英文 Prompt 结果

```
Age Group：25-29
Location：上海
Fertility Status：Trying
Income Level：Medium
Spatial Preferences：['Transit', 'Hospitals']
Fertility Intent Score：2
Reasoning：基于账号特征线索生成模拟结果。
```

## 🔧 技术实现

### 1. Prompt 模板设计

中文 Prompt 采用结构化设计：
- 明确的判断依据
- 关键词映射表
- 评分标准
- 输出格式要求

### 2. 向后兼容

- 保留原有英文 Prompt
- 通过 `use_chinese_prompt` 参数切换
- 默认使用中文 Prompt

### 3. 错误处理

- 无 API Key 时自动切换到 Mock 模式
- 推断失败时返回 "Unknown"
- 提供详细的错误日志

## 📝 注意事项

1. **API Key 配置**
   - 需要配置 OpenAI API Key 或兼容 API
   - 支持 Moonshot Kimi 等国内模型

2. **数据质量**
   - 笔记内容越丰富，推断越准确
   - 建议抓取 3-5 条笔记详情

3. **频率控制**
   - 小红书反爬严格，建议分批采集
   - 每次间隔 30 分钟以上

4. **结果验证**
   - 建议人工抽检推断结果
   - 根据实际情况调整 Prompt

## 🎯 下一步优化

1. **优化特征提取**
   - 增加更多生育相关关键词
   - 优化空间偏好识别算法

2. **增加问卷模块**
   - 设计生育意愿问卷
   - 支持用户主动填写

3. **提升推断准确度**
   - 收集更多标注数据
   - 微调 Prompt 模板

4. **支持更多平台**
   - 扩展到微博、抖音等平台
   - 统一数据格式

## 📚 相关文件

- `src/analysis/prompts.py` - Prompt 模板定义
- `src/analysis/persona_extractor.py` - 人设推断器
- `src/analysis/batch_processor.py` - 批量处理器
- `tests/test_chinese_prompt.py` - 测试脚本

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 项目
2. 创建功能分支
3. 提交更改
4. 发起 Pull Request

## 📄 许可证

本项目采用 MIT 许可证。
