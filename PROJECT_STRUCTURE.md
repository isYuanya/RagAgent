# RagAgent 项目框架说明

## 项目目标

RagAgent 是一个面向短视频/口播文案的 Agent RAG 项目。首版框架覆盖文案拆解、模板沉淀、知识库检索、内容生成、合规评审和反馈回流的主要边界，但默认使用 stub LLM 输出，方便本地先跑通工程结构。

## 技术选型

- 后端：FastAPI
- 工作流编排：LangGraph 边界预留在 `app/workflows/`
- RAG：LlamaIndex 边界预留在 `app/rag/`
- 结构化数据：PostgreSQL + SQLAlchemy + Alembic
- 向量库：Milvus
- 缓存和任务队列：Redis + RQ
- 对象存储：本地 `storage/`
- 数据校验：Pydantic
- 前端：Vite + React + TypeScript
- 模型接口：OpenAI 兼容配置
- 观测：LangSmith 环境变量预留
- 部署：本地 Docker Compose

## 目录说明

```text
app/
  api/          HTTP 路由，提供健康检查、文案拆解、生成、任务状态和反馈接口
  core/         配置、LLM 抽象、应用级基础能力
  db/           SQLAlchemy Base、engine、session
  models/       PostgreSQL ORM 模型
  schemas/      Pydantic 请求和响应模型
  services/     文案拆解、生成、合规检查、反馈等业务服务
  workflows/    LangGraph 编排边界
  rag/          LlamaIndex ingestion/retrieval 边界
  workers/      Redis/RQ 任务队列边界
  prompts/      拆解、生成、合规评审 Prompt 模板
frontend/       React 工作台
storage/        本地文件和索引存储目录
alembic/        数据库迁移目录
docker-compose.yml
```

## 当前已实现的能力

后端已经提供最小可运行 API：

- `GET /api/health`：健康检查。
- `POST /api/copy/analyze`：提交文案并返回结构化拆解结果。
- `POST /api/generate`：根据行业、人群、目的、风格等参数生成文案版本。
- `GET /api/tasks/{task_id}`：查询任务状态。
- `POST /api/feedback`：记录用户反馈。

文案拆解输出包含主题、目标用户、核心痛点、情绪按钮、开头钩子、结构、表达技巧、可复用模板、适用场景、风险提醒和置信度。

文案生成输出包含选题方向、钩子、完整口播文案、分镜建议、标题、评论区引导、可替换版本和风险提醒。

## 数据流

1. 用户在前端输入文案和筛选条件。
2. 前端调用 FastAPI。
3. API route 将请求交给 `app/workflows/`。
4. Workflow 调用业务服务、RAG 检索和合规检查。
5. 结构化结果返回前端展示。
6. 用户反馈通过 `/api/feedback` 记录，后续可写入 PostgreSQL 并进入优化流程。

## 模型与 RAG 接入方式

当前 `app/core/llm.py` 使用 OpenAI 兼容配置作为稳定边界：

```env
OPENAI_API_KEY=
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4.1-mini
EMBEDDING_MODEL=text-embedding-3-small
```

如果没有配置密钥，系统会使用 stub 返回，保证本地框架可以先跑通。后续接真实模型时，优先替换 `OpenAICompatibleLLMClient.complete()` 的内部实现，不需要改 API 和前端。

`app/rag/ingestion.py` 和 `app/rag/retriever.py` 目前是 LlamaIndex/Milvus 的接口边界。后续可以把批量 ingestion、metadata、embedding、索引构建和检索逻辑填入这些模块。

## 本地启动

准备 Python 环境后安装依赖：

```powershell
pip install -e ".[dev]"
```

复制环境变量：

```powershell
Copy-Item .env.example .env
```

启动基础设施：

```powershell
docker compose up -d
```

启动后端：

```powershell
python main.py
```

启动前端：

```powershell
cd frontend
npm install
npm run dev
```

访问：

- 后端健康检查：`http://127.0.0.1:8000/api/health`
- 前端工作台：`http://127.0.0.1:5173`

## 验证命令

```powershell
python -m py_compile main.py
python -m pytest
cd frontend
npm run build
```

如果 Python 3.14 下某些三方依赖暂未完全兼容，可以先锁定兼容版本，或临时使用 Python 3.12/3.11 运行依赖安装。当前项目按你的选择保留 `requires-python = ">=3.14"`。

## 后续扩展

- 将 stub LLM 替换为真实 OpenAI 兼容调用。
- 用 LlamaIndex 接入批量文案 ingestion、metadata、embedding、Milvus 检索。
- 用 LangGraph 完整编排“理解需求 -> 检索 -> 生成 -> 评审 -> 多版本输出 -> 反馈”的状态图。
- 将当前内存任务状态替换为 RQ job 状态。
- 将反馈、拆解结果、模板和标签写入 PostgreSQL。
- 增加原创性/相似度检查、A/B 测试、账号风格学习和发布数据回流。
