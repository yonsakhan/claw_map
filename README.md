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

### 2) 配置环境变量

复制 `.env.example` 为 `.env`，填入 MongoDB / LLM key / 小红书登录信息等。

### 3) 刷新小红书登录态

```bash
python local_login.py
```

成功后会生成/更新 `src/storage/xhs_state.json`（该文件已在 `.gitignore` 中忽略）。

### 4) 冒烟测试（建议先跑通）

```bash
python -m src.crawler.smoke_run
cat reports/smoke_run.json
```

若 `task_error` 为 `profile fetch returned None`，通常表示登录态失效或被拦截，需要重新登录/调整采集策略。

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

