# claw_map

面向“超大城市生育友好型空间要素研究”的数据平台：**采集（小红书）→ 原始存储 → 特征化清洗 → LLM 人设推断 → 访谈/情景模拟**。

## 目录结构

- `src/crawler/`：Playwright 采集（账号主页 / 帖子 / 收藏等）
- `src/storage/`：MongoDB 任务队列 + 原始数据存储 + 结果追溯
- `src/analysis/`：特征对象构建 + Persona 提取
- `src/simulation/`：基于 Persona 的虚拟访谈模拟
- `reports/`：运行报告输出（默认忽略，不提交）

## 快速开始

### 1) 安装依赖

```bash
pip install -r requirements.txt
python -m playwright install
```

## 推荐入口

- 主抓取入口：`python -m src.crawler.run_large_scale_crawl`
- 登录态刷新：`python -m scripts.local_login`
- 无数据库抓取排障：`python -m src.crawler.smoke_no_db --url "<xhs-profile-url>"`
- 数据库初始化/缺列补齐：`python -m scripts.db_setup`

以下顶层文件目前仅保留为兼容入口，不建议作为长期主入口：

- `main.py`
- `worker.py`
- `scheduler.py`
- `batch_processor.py`
- `local_login.py`
- `db_setup.py`
- `fix_display_name.py`

### 2) 配置环境变量

复制 `.env.example` 为 `.env`，填入 MongoDB / LLM key / 小红书登录信息等。

### 3) 刷新小红书登录态

```bash
python -m scripts.local_login
```

成功后会生成/更新 `src/storage/xhs_state.json`（该文件已在 `.gitignore` 中忽略）。

也支持显式指定模式或状态文件路径：

```bash
python -m scripts.local_login --mode manual
python -m scripts.local_login --mode cookie --cookie '<cookie-string>'
python -m scripts.local_login --state-path /tmp/xhs_state.json
```

### 4) 冒烟测试（建议先跑通）

```bash
python -m src.crawler.smoke_run
cat reports/smoke_run.json
```

若 `task_error` 为 `profile fetch returned None`，通常表示登录态失效或被拦截，需要重新登录/调整采集策略。

### 5) 无数据库冒烟（推荐用于快速定位登录拦截）

如果本地 MongoDB 还没就绪，或想先单独验证 Playwright 抓取/拦截原因：

```bash
python -m src.crawler.smoke_no_db --url "https://www.xiaohongshu.com/user/profile/<id>"
cat reports/smoke_no_db.json
```

若输出 `status=blocked` 且 `error_code=login_required`，说明需要刷新登录态（`python -m scripts.local_login`）。

## 维护脚本

- `python -m scripts.local_login`：刷新/保存小红书登录态。
- `python -m scripts.db_setup`：创建数据库表并为 `agent_personas` 补齐历史缺失字段。
- `python -m scripts.fix_display_name <jsonl-path>`：修复 `keyword_scout` 输出 JSONL 中的异常 `display_name`，属于人工修复工具，不参与主链路。

## 开发规范与 Git 工作流

本仓库按《代码开发规范》落地了基础工具链与约束：

- 代码格式化：`black`
- import 排序：`isort`
- 基础静态检查：`ruff`
- 类型检查：`mypy`（逐步加强）
- 提交前钩子：`pre-commit`（见 `.pre-commit-config.yaml`）

安装 pre-commit：

```bash
pip install -r requirements-dev.txt
pre-commit install
```

更多协作约定见 `CONTRIBUTING.md`。
