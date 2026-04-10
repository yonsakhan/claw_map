# 贡献指南（Contributing）

## 分支策略

- `main`：发布分支，禁止直接提交
- `develop`：开发主分支（建议后续创建并作为默认开发分支）
- 功能分支：`feature/<功能描述>`
- 修复分支：`bugfix/<问题描述>`
- 紧急修复：`hotfix/<问题描述>`

推荐流程：

1. 从 `develop` 拉取最新
2. 创建分支开发
3. 提交前自测 + 通过 lint/format
4. 提交 PR 合并回 `develop`
5. 测试通过后合并 `develop` → `main`

## Commit Message 规范

使用前缀 + 简要说明（动词开头）：

- `feat: ...` 新功能
- `fix: ...` 修复 bug
- `refactor: ...` 重构（不改变功能）
- `docs: ...` 文档
- `test: ...` 测试
- `chore: ...` 构建/依赖/配置

示例：

- `feat: add mongo task leasing`
- `fix: handle login block in scraper`

## 本地检查（必须）

```bash
pip install -r requirements-dev.txt
pre-commit install
pre-commit run -a
```

## 不要提交的内容

- 密钥与环境：`.env`、token/cookie、`src/storage/xhs_state.json`
- 运行产物：`reports/`、`data/`、`*.jsonl`、`*.db`
- IDE/系统文件：`.idea/`、`.vscode/`、`.DS_Store`

