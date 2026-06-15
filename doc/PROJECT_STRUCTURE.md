# RagAgent 项目结构说明

RagAgent 是面向短视频/口播文案资产的后端服务。当前阶段以后端 API、LLM 拆解、CSV 导入、任务进度、资产沉淀和审核流为主。

## 职责边界

- 后端由本项目继续维护：FastAPI、Pydantic schema、任务队列、LLM 调用、资产存储、测试和后端文档。
- 前端由使用方自行维护：页面、交互、视觉、前端状态管理和构建流程。
- `frontend/` 目录保留在仓库中作为历史实现或本地参考；除非明确要求，后续不再主动修改。
- 前端接入以 `doc/FRONTEND_INTEGRATION.md` 和 FastAPI `/openapi.json` 为准。

## 技术选型

- Web 框架：FastAPI
- 数据校验：Pydantic
- 后台任务：Redis + RQ，Windows 本地 worker 使用 `SimpleWorker`
- 结构化存储：PostgreSQL + SQLAlchemy + Alembic
- 缓存/兜底资产读取：Redis，本地内存兜底
- LLM：OpenAI 兼容接口，配置项为 `OPENAI_API_KEY`、`OPENAI_BASE_URL`、`OPENAI_MODEL`
- RAG 预留：LlamaIndex / Milvus 边界仍保留
- 默认后端端口：`8002`

## 目录说明

```text
app/
  api/          FastAPI 路由，统一挂载到 /api
  core/         配置、LLM 客户端等基础能力
  db/           SQLAlchemy engine/session/base
  models/       ORM 模型
  schemas/      Pydantic 请求/响应模型
  services/     文案拆解、CSV 导入、资产存储、生成、反馈等业务逻辑
  workflows/    工作流边界
  rag/          RAG ingestion/retrieval 预留边界
  workers/      Redis/RQ 队列、任务状态和导入任务入口
alembic/        数据库迁移
doc/            PRD、Schema、前端对接和项目结构文档
scripts/        本地 worker 等脚本
storage/        本地测试数据和文件
tests/          后端测试
frontend/       前端历史实现；默认不再由后端工作修改
```

## 当前后端能力

- `GET /api/health`：健康检查。
- `POST /api/copy/analyze`：直接拆解单条文案，返回结构化分析。
- `POST /api/copy/import`：提交 CSV 文本，创建导入任务。
- `GET /api/tasks/{task_id}`：查询导入任务状态、LLM 模型、进度和错误。
- `GET /api/copy/assets`：分页查询文案资产，支持状态、行业、平台筛选。
- `GET /api/copy/assets/{asset_id}`：查看单条文案资产详情。
- `PATCH /api/copy/assets/{asset_id}/review`：提交人工审核后的拆解结果。
- `/api/knowledge/*`：知识库 API，覆盖集合、原始文案、结构化拆解、模板、标签、案例和禁用库。
- `POST /api/generate`、`POST /api/feedback`：保留现有生成和反馈接口。

## 本地启动

安装依赖：

```powershell
pip install -e ".[dev]"
```

准备环境变量：

```powershell
Copy-Item .env.example .env
```

启动 Redis/PostgreSQL 等基础设施：

```powershell
docker compose up -d
```

启动后端：

```powershell
python main.py
```

启动导入 worker：

```powershell
python scripts/worker.py
```

常用访问地址：

- 后端根地址：`http://127.0.0.1:8002/`
- 健康检查：`http://127.0.0.1:8002/api/health`
- Swagger UI：`http://127.0.0.1:8002/docs`
- OpenAPI JSON：`http://127.0.0.1:8002/openapi.json`

## 配置项

| 环境变量 | 默认值 | 说明 |
| --- | --- | --- |
| `APP_NAME` | `RagAgent` | 应用名称 |
| `APP_ENV` | `local` | 运行环境 |
| `API_PREFIX` | `/api` | API 前缀 |
| `CORS_ORIGINS` | `http://localhost:5173` | 允许跨域来源，多个值用逗号分隔 |
| `CORS_ORIGIN_REGEX` | `^https?://(localhost\|127\.0\.0\.1)(:\d+)?$` | 本地开发跨域来源正则 |
| `DATABASE_URL` | `postgresql+psycopg://rag:rag@localhost:5432/rag` | PostgreSQL 连接 |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis 连接 |
| `OPENAI_API_KEY` | 空 | LLM 密钥 |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | OpenAI 兼容接口地址 |
| `OPENAI_MODEL` | `gpt-4.1-mini` | 默认拆解模型 |

## 验证命令

```powershell
python -m pytest
python -m compileall app scripts tests
```

后端接口契约发生变化时，需要同步更新：

- `doc/FRONTEND_INTEGRATION.md`
- `doc/SCHEMAS.md`
- FastAPI schema 对应的 `app/schemas/*.py`
