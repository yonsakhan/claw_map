# Tasks

- [x] Task 1: 定义账号维度原始数据协议并落库
  - [x] SubTask 1.1: 明确账号主键与采集窗口字段（账号ID、时间戳、状态）
  - [x] SubTask 1.2: 增加简介/帖子/点赞/收藏/关注的原始结构定义
  - [x] SubTask 1.3: 为采集失败场景定义错误码与重试标记

- [x] Task 2: 实现账号追踪采集流程
  - [x] SubTask 2.1: 增加按账号拉取多维行为的采集入口
  - [x] SubTask 2.2: 增加采集节流与反爬失败恢复策略
  - [x] SubTask 2.3: 采集完成后写入 Mongo 原始层并记录采集日志

- [x] Task 3: 构建特征化清洗管线
  - [x] SubTask 3.1: 将原始行为映射为 `account_feature_profile`
  - [x] SubTask 3.2: 输出证据片段与统计摘要（特征可解释）
  - [x] SubTask 3.3: 增加特征完整度校验与缺失兜底策略

- [x] Task 4: 升级人设推理与问卷联合输出
  - [x] SubTask 4.1: 重构 Prompt 组装，输入改为账号特征对象
  - [x] SubTask 4.2: 接入问卷上下文并生成结构化答卷结果
  - [x] SubTask 4.3: 保存输出版本信息（prompt_version / questionnaire_version）

- [x] Task 5: 增加结果追溯与审计查询
  - [x] SubTask 5.1: 在结构化结果中保存账号ID、证据引用与模型参数
  - [x] SubTask 5.2: 提供按结果ID回查来源数据的查询能力

- [x] Task 6: 验证端到端流程（小样本）
  - [x] SubTask 6.1: 用 10 个账号跑通采集→清洗→推理→落库
  - [x] SubTask 6.2: 校验输出字段完整性与可追溯性
  - [x] SubTask 6.3: 记录失败样本并形成修复任务

# Task Dependencies
- Task 2 depends on Task 1
- Task 3 depends on Task 2
- Task 4 depends on Task 3
- Task 5 depends on Task 4
- Task 6 depends on Task 2, Task 3, Task 4, Task 5
