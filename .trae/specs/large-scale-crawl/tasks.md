# Tasks
- [x] Task 1: 明确“用户记录”最低字段集与存储协议
  - [x] SubTask 1.1: 定义 user/profile/collections 的标准 JSON schema（含必填/可选/缺省）
  - [x] SubTask 1.2: 定义缺失率计算规则与 incomplete 标记规则
  - [x] SubTask 1.3: 定义导出格式（JSONL/CSV）字段映射

- [x] Task 2: 实现任务队列与断点续爬
  - [x] SubTask 2.1: 任务表/集合设计（pending/processing/success/failed/dead）
  - [x] SubTask 2.2: 领取锁与超时回收机制（worker crash 可恢复）
  - [x] SubTask 2.3: 重试策略与失败归因字典（原因标准化）

- [x] Task 3: 实现多 Worker 并行执行框架（4–6 实例）
  - [x] SubTask 3.1: Worker 进程入口与配置（worker_id、并发度、速率限制）
  - [x] SubTask 3.2: 支持独立代理配置与会话隔离（每 worker 独立代理池）
  - [x] SubTask 3.3: 运行守护与优雅退出（SIGTERM/SIGINT）

- [x] Task 4: 实现采集逻辑的“队列化”适配
  - [x] SubTask 4.1: 将现有采集入口改为从任务队列取 URL/账号
  - [x] SubTask 4.2: 将采集结果实时写入原始层，并更新任务状态
  - [x] SubTask 4.3: 采集失败时写入失败原因与证据（HTML标题/关键字/截图可选）
  - [x] SubTask 4.4: 入口页账号发现：从 `/explore` 列表抽取账号候选并去重
  - [x] SubTask 4.5: 主页字段解析：用户名、小红书号、IP属地、简介、关注/粉丝/获赞收藏等结构化提取
  - [x] SubTask 4.6: 收藏夹采集：进入“收藏”页，抓取收藏夹名称、收藏内容、收藏时间（按分页/滚动）
  - [x] SubTask 4.7: 搜索页账号发现：从 `search_result` 关键词页切换“用户”tab，滚动抽取用户卡片并去重入队
  - [x] SubTask 4.8: 账号去重策略：按 xhs_id / profile_url / account_id 多键去重，保证 10,000 唯一用户

- [x] Task 5: 数据质量与统计报告
  - [x] SubTask 5.1: 产出字段缺失率统计、成功率、失败原因分布
  - [x] SubTask 5.2: 产出吞吐指标（用户/小时、每 worker 产能）
  - [x] SubTask 5.3: 产出人工抽样核对包（随机 100 条的导出与字段对照表）

- [ ] Task 6: 可选对接 Apify（作为托管执行/数据集存储后端）
  - [ ] SubTask 6.1: 增加 Apify token 配置与运行封装（start/call）
  - [ ] SubTask 6.2: 将任务分片映射到 Actor input，并回收 dataset 输出
  - [ ] SubTask 6.3: 保持与本地队列一致的状态与统计口径

- [ ] Task 7: 生产级验证与交付
  - [ ] SubTask 7.1: 压测：单 worker ≥50 用户/小时（在授权/可用数据源前提下）
  - [ ] SubTask 7.2: 并发：整体 ≥200 用户/小时（4 worker）
  - [ ] SubTask 7.3: 质量：缺失率 <5%，抽样核对准确率 >95%
  - [ ] SubTask 7.4: 交付：可运行代码、部署配置文档、运行日志、统计报告与导出文件
  - [ ] SubTask 7.5: 明确交付边界：采集数据文件为运行产物，不写入仓库版本控制

# Task Dependencies
- Task 2 depends on Task 1
- Task 3 depends on Task 2
- Task 4 depends on Task 2, Task 3
- Task 5 depends on Task 4
- Task 7 depends on Task 5
- Task 6 is optional and can be done in parallel after Task 2
