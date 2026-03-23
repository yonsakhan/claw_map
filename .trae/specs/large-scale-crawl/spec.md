# 大规模用户数据采集方案 Spec

## Why
现有采集链路在登录拦截、字段完整性、断点续爬与并发吞吐方面不稳定，无法支撑可重复的规模化研究/分析。  
需要将采集系统升级为“可调度、可扩展、可审计”的数据采集平台，并提供生产级验证证据。

## What Changes
- 建立可扩展的任务调度与多 Worker 并行采集框架（4–6 个 worker 进程/实例）。
- 建立实时写入与断点续爬：任务状态、重试、失败归因、可恢复运行。
- 建立数据质量门禁：字段缺失率统计、采样核对流程、吞吐/成功率监控。
- 支持结构化输出（JSONL/CSV）与运行报告（成功率、失败原因分布、吞吐曲线）。
- 支持对接托管执行平台（例如 Apify）作为可选“分布式执行与数据集存储”后端。
- **BREAKING**：采集入口从“脚本直跑单条 URL”升级为“任务队列驱动的批量采集”。

## Impact
- Affected specs: 采集、存储、质量控制、运行可观测性、断点续爬、并行执行
- Affected code: 爬虫模块、存储模块、数据库 schema、运行脚本与配置管理

## Crawler Review（现状检查）
- 现有爬虫已具备：登录态（state/cookie）使用、登录拦截识别、基础主页字段粗解析、从 explore 列表发现账号入口并抓取账号主页。
- 现有爬虫缺失：收藏夹（收藏夹名称/收藏内容/收藏时间）采集；任务队列化调度；多 worker 并行与断点续爬；质量统计与导出。
- 采集策略建议：以 `https://www.xiaohongshu.com/explore` 作为入口页，从同层级账号节点（如 `span.name`）提取账号链接/候选，进入账号主页后解析结构化字段，并进一步进入“收藏”页采集收藏夹与收藏内容。

## Tech Decisions
- 标准采集引擎：Playwright（统一处理动态加载、滚动、分页、打开新页面/新标签页）。
- 账号发现策略：以“入口页账号候选 + 搜索页账号候选 + 关系扩展（关注/粉丝）”组合覆盖，统一进入任务队列去重。

## Crawl Plan（采集覆盖方案）
- **入口 1：Explore 推荐流**：从 `/explore` 列表页抽取账号候选（例如昵称节点 `span.name`），点击进入账号主页，采集 profile + collections。
- **入口 2：Search 关键词页**：从 `https://www.xiaohongshu.com/search_result?keyword={keyword}&source=web_search_result_notes` 进入搜索结果，切换到“用户”tab，滚动分页抽取用户卡片候选并去重。
  - 关键词建议覆盖城市：北京/上海/广州/深圳（可按业务扩展更多城市与人群标签）。
  - 注意：搜索结果页通常需要登录；如果出现登录提示，记录失败原因并暂停该任务，等待人工更新登录态后续跑。

## Data Contract（用户最小字段集）
- **Profile（主页）**：username/display_name、xhs_id（小红书号）、ip_location、location、bio、follow_count、fans_count、likes_favorites_count、profile_url、captured_at、source_entry（explore/search/graph）。
- **Collections（收藏夹）**：
  - folders[]：folder_name、folder_id（如可得）、items_count（如可得）
  - items[]：note_id/url、title（如可得）、author（如可得）、saved_at（收藏时间，如可得）、folder_name
  - 如果收藏时间无法稳定获取，必须显式标记 `saved_at=null` 并计入缺失率统计。

## ADDED Requirements
### Requirement: 分布式采集与断点续爬
系统 SHALL 支持 4–6 个并行 Worker 实例在同一任务队列下协同采集，并在任意实例重启后继续从断点恢复。

#### Scenario: Worker 异常重启后继续采集
- **WHEN** Worker 在采集中断（崩溃/重启/网络断开）
- **THEN** 未完成任务会回滚或超时释放为可再领取状态
- **THEN** 重启后的 Worker 能继续领取并完成剩余任务

### Requirement: 用户结构化数据输出
系统 SHALL 将采集结果输出为结构化数据（JSONL/CSV），并保证每个用户记录包含最低要求字段集。

#### Scenario: 导出结构化文件
- **WHEN** 采集任务运行结束或达到指定阈值
- **THEN** 可导出 JSONL 与 CSV
- **THEN** 每条用户记录至少包含：主页基础信息字段与收藏夹摘要字段

### Requirement: 数据质量验证
系统 SHALL 计算并输出字段缺失率，并提供抽样核对数据包用于人工复核。

#### Scenario: 质量门禁失败
- **WHEN** 单用户字段缺失率 > 5%
- **THEN** 该用户记录被标记为 `incomplete`
- **THEN** 统计报告中输出缺失字段分布与失败原因

### Requirement: 运行统计与失败归因
系统 SHALL 输出运行日志与统计报告，至少包含成功率、失败原因分布、吞吐（用户/小时）与重试次数。

#### Scenario: 生成统计报告
- **WHEN** 采集运行结束
- **THEN** 生成包含成功率、失败原因、吞吐曲线与各 Worker 产能的报告

### Requirement: 合规与安全（约束）
系统 SHALL 不包含验证码识别绕过、未授权访问或数据注入相关功能；仅在具备合法授权、符合目标站点条款与适用法律法规前提下运行。

#### Scenario: 遇到登录/验证码拦截
- **WHEN** 采集过程中出现登录或验证码拦截
- **THEN** 系统记录为可追溯失败原因并停止该任务的自动推进
- **THEN** 不尝试自动化破解验证码

## MODIFIED Requirements
### Requirement: 账号维度采集输入输出协议
现有账号采集 SHALL 兼容队列化任务输入，并统一输出 `raw_data.profile` 与 `raw_data.collections` 的结构化对象，供后续特征化与人设推理复用。

## REMOVED Requirements
### Requirement: 单脚本一次性全量跑完
**Reason**: 不可扩展、不可恢复、不可审计，无法满足生产级验证。  
**Migration**: 使用任务队列 + Worker 并行执行替代，所有运行状态落库记录。
