# 大规模用户数据采集系统规格说明书

## 1. 目标
构建高可用、高隐蔽的分布式爬虫系统，实现 10,000 个真实小红书用户及其收藏数据的完整采集，满足准确率 > 95% 和缺失率 < 5% 的质量标准。

## 2. 核心架构
- **调度层 (Scheduler)**: 负责任务分发、去重、断点记录与 Agent 生命周期管理。
- **执行层 (Agent Workers)**: 4-6 个独立进程，每个进程绑定独立代理 IP 与浏览器指纹。
- **存储层 (Storage)**: 
  - MongoDB: 实时存取 raw json 数据（支持高并发写入）。
  - PostgreSQL: 存储任务队列与状态（pending/processing/success/failed）。
- **反爬策略 (Anti-Scraping)**:
  - 动态代理池轮换（每请求/每会话）。
  - 浏览器指纹随机化（User-Agent, Canvas, WebGL）。
  - 行为拟人化（随机滚动、鼠标轨迹、阅读停顿）。

## 3. 详细设计

### 3.1 数据模型
- **Task**: `{"url": str, "status": str, "retry_count": int, "agent_id": str, "updated_at": datetime}`
- **UserRaw**: 包含 `profile` (基础信息), `collections` (收藏夹列表 + 详情), `crawl_meta` (采集元数据)。

### 3.2 Agent 逻辑
1. 从调度器领取任务 (加锁)。
2. 检查本地/全局代理状态，获取新 IP。
3. 初始化 Playwright Context (注入指纹 + Cookie/State)。
4. 执行采集：
   - 访问主页 -> 提取基础信息。
   - 点击“收藏” Tab -> 遍历收藏夹 -> 提取收藏内容。
5. 数据校验 (字段完整性检查)。
6. 写入 MongoDB -> 更新调度器状态。
7. 随机休眠 -> 循环。

### 3.3 容错与断点续爬
- **任务重试**: 失败任务回滚至 pending，重试次数 > 3 进入 dead letter queue。
- **进程守护**: 主控进程监控 Worker 存活，异常退出自动拉起。
- **断点记录**: 每次写入 DB 即为断点，重启后通过 DB 状态恢复队列。

## 4. 交付物清单
1. `src/crawler/scheduler.py`: 调度核心。
2. `src/crawler/worker.py`: 采集执行单元。
3. `src/crawler/proxy_manager.py`: 代理池管理。
4. `config/agent_config.yaml`: 部署配置文件。
5. `data/crawled_10k_users.jsonl`: 结果数据。
6. `reports/crawl_report.md`: 统计报告。

## 5. 测试计划
- **阶段一**: 单 Agent 跑通 50 个用户，验证字段完整性。
- **阶段二**: 多 Agent (4个) 并发跑 500 个用户，验证调度与 IP 隔离。
- **阶段三**: 全量 10,000 用户采集，并在过程中进行抽样核对。

## 6. 环境依赖
- Python 3.10+
- Playwright
- MongoDB & PostgreSQL
- 代理 IP 服务 (需用户提供或使用免费池测试)
