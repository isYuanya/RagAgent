# 重启电脑后的服务启动清单

本文档用于本地开发环境重启后，按顺序恢复 RagAgent 项目的相关服务。

项目目录：

```powershell
cd C:\RagAgent
```

## 1. 最小可用启动

如果只是打开页面、访问普通接口，通常只需要启动后端 API 和前端页面。

### 1.1 启动后端 API

打开一个 PowerShell 窗口：

```powershell
cd C:\RagAgent
C:\RagAgent\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8002
```

后端地址：

```text
http://127.0.0.1:8002
```

启动后验证：

```powershell
Invoke-WebRequest http://127.0.0.1:8002/api/health -UseBasicParsing
Invoke-WebRequest http://127.0.0.1:8002/api/knowledge/collections -UseBasicParsing
```

正常情况：

- `/api/health` 返回 `200`
- `/api/knowledge/collections` 返回知识库集合列表

说明：本地开发推荐不要加 `--reload`。Windows 上有时会残留 reload 子进程，导致旧路由仍在响应。

### 1.2 启动前端页面

再打开一个 PowerShell 窗口：

```powershell
cd C:\RagAgent\frontend
npm run dev
```

浏览器打开 Vite 输出的地址，通常是：

```text
http://localhost:5173
```

如果 `5173` 被占用，Vite 会自动换到 `5174`、`5175` 等端口。以后端 CORS 配置为准，当前本地开发一般允许 `localhost` 和 `127.0.0.1`。

## 2. 完整功能启动

如果要使用 CSV 异步导入、后台任务、知识库持久化、智能组稿语义匹配和 Milvus 向量检索，建议按下面顺序启动。

推荐顺序：

```text
1. PostgreSQL
2. Redis
3. Milvus 依赖服务（etcd、MinIO）
4. Milvus
5. 后端 API
6. 后台 worker
7. 前端页面
```

### 2.1 PostgreSQL

知识库、文案、草稿、审核数据等持久化默认使用 PostgreSQL：

```text
DATABASE_URL=postgresql+psycopg://rag:rag@localhost:5432/rag
```

如果使用 Docker Compose，推荐从项目根目录启动：

```powershell
cd C:\RagAgent
docker compose up -d postgres
```

如果容器已经存在，也可以单独启动：

```powershell
docker start ragagent-postgres
```

启动后执行数据库迁移：

```powershell
cd C:\RagAgent
C:\RagAgent\.venv\Scripts\alembic.exe upgrade head
```

如果 PostgreSQL 没有启动，部分知识库接口可能会退回内存模式：页面可能能打开，但数据不会真正持久化保存。

### 2.2 Redis

CSV 导入和后台任务队列需要 Redis：

```text
REDIS_URL=redis://localhost:6379/0
```

使用 Docker Compose：

```powershell
cd C:\RagAgent
docker compose up -d redis
```

如果容器已经存在，也可以单独启动：

```powershell
docker start ragagent-redis
```

验证 Redis 容器：

```powershell
docker ps
```

### 2.3 Milvus

智能组稿已升级为优先使用 Embedding + Milvus 向量检索进行语义匹配；关键词匹配仍保留为降级方案。

Milvus 默认配置：

```text
MILVUS_URI=http://localhost:19530
EMBEDDING_MODEL=text-embedding-3-small
OPENAI_API_KEY=<你的 API Key>
```

Milvus standalone 依赖 etcd 和 MinIO。推荐直接启动 Compose 中的完整向量检索依赖：

```powershell
cd C:\RagAgent
docker compose up -d etcd minio milvus
```

也可以一次性启动全部基础服务：

```powershell
cd C:\RagAgent
docker compose up -d postgres redis etcd minio milvus
```

验证容器：

```powershell
docker ps
```

应能看到以下容器处于运行状态：

```text
ragagent-etcd
ragagent-minio
ragagent-milvus
```

Milvus 端口：

```text
19530  Milvus 服务端口
9091   Milvus 健康/监控端口
9000   MinIO API
9001   MinIO 控制台
```

注意：

- 如果 Milvus 未启动，智能组稿会自动降级到关键词匹配。
- 如果 `OPENAI_API_KEY` 未配置，Embedding 无法生成，语义检索也会降级。
- 文案新增、修改、删除时会尝试同步 Milvus 向量；向量同步失败会记录日志，但不会阻断原有数据库流程。

### 2.4 后台 worker

worker 用于处理 CSV 导入等异步任务。启动 worker 前，请先确认 Redis 已经启动。

打开新的 PowerShell 窗口：

```powershell
cd C:\RagAgent
C:\RagAgent\.venv\Scripts\python.exe C:\RagAgent\scripts\worker.py
```

当前 worker 监听队列：

```text
copy_import
```

如果 Redis 没启动，worker 通常会报类似错误：

```text
Redis is not reachable. Start Redis first or update REDIS_URL in .env.
```

## 3. 更新后功能检查

### 3.1 智能组稿语义匹配

完整语义匹配需要：

- 后端 API 已启动
- PostgreSQL 已启动并完成迁移
- Milvus、etcd、MinIO 已启动
- `.env` 中配置了可用的 `OPENAI_API_KEY`
- `MILVUS_URI` 指向当前 Milvus 服务

验证方式：

```powershell
Invoke-WebRequest http://127.0.0.1:8002/api/health -UseBasicParsing
Invoke-WebRequest http://127.0.0.1:8002/api/knowledge/collections -UseBasicParsing
```

业务验证：

1. 在知识库新增或审核通过一条文案。
2. 使用智能组稿输入相近语义但不同关键词的主题。
3. 如果 Milvus 和 Embedding 可用，应优先返回语义相关文案。
4. 关闭 Milvus 或移除 API Key 后，再次组稿应仍可通过关键词降级完成。

### 3.2 批量删除

本次更新后，审核工作台和知识库支持按筛选结果批量删除，并同步清理相关数据和向量。

相关接口：

```text
POST /api/copy/assets/bulk-delete
POST /api/knowledge/raw-copies/bulk-delete
```

删除行为：

- 删除数据库中的目标文案数据。
- 清理知识库派生引用、片段等关联数据。
- 如果存在 Milvus 向量，会同步删除对应向量。
- 附件处理遵循现有存储设计，不在归档流程中删除附件。

### 3.3 草稿批量归档

草稿工作台支持批量选择归档。

相关接口：

```text
POST /api/drafts/bulk-archive
```

归档行为：

- 只修改草稿状态为已归档。
- 保留历史数据。
- 不删除原文案。
- 不删除附件。

## 4. 常见故障

### 4.1 前端显示“加载集合失败”

先检查后端接口：

```powershell
Invoke-WebRequest http://127.0.0.1:8002/api/knowledge/collections -UseBasicParsing
```

如果返回 `404`，通常说明当前 `8002` 端口上运行的是旧后端实例，或者后端启动入口不对。

查看占用 `8002` 的进程：

```powershell
netstat -ano | Select-String ':8002'
```

结束占用进程：

```powershell
taskkill /PID <PID> /F
```

然后重新启动后端：

```powershell
cd C:\RagAgent
C:\RagAgent\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8002
```

### 4.2 worker 启动时报 Redis 连接失败

说明 Redis 没启动，或者 `.env` 里的 `REDIS_URL` 不正确。

处理顺序：

```text
1. 先启动 Redis
2. 检查 .env 里的 REDIS_URL
3. 再启动 worker
```

### 4.3 端口被占用

查看后端端口：

```powershell
netstat -ano | Select-String ':8002'
```

查看前端端口：

```powershell
netstat -ano | Select-String ':5173'
```

查看 Milvus 端口：

```powershell
netstat -ano | Select-String ':19530'
```

结束指定进程：

```powershell
taskkill /PID <PID> /F
```

### 4.4 后端启动后接口还是旧的

优先怀疑有旧的 `uvicorn --reload` 子进程残留。

处理方式：

```powershell
netstat -ano | Select-String ':8002'
taskkill /PID <PID> /F
```

然后用无 reload 模式重新启动：

```powershell
cd C:\RagAgent
C:\RagAgent\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8002
```

### 4.5 智能组稿没有语义匹配效果

按顺序检查：

```text
1. docker ps 中是否有 ragagent-milvus、ragagent-etcd、ragagent-minio
2. .env 中 MILVUS_URI 是否为 http://localhost:19530
3. .env 中 OPENAI_API_KEY 是否可用
4. 后端启动日志是否有向量同步或向量检索异常
5. 相关文案是否已经新增、更新或审核通过，从而触发向量同步
```

如果 Milvus 或 Embedding 不可用，系统会自动降级到关键词匹配，所以功能仍可用，但匹配质量会回到旧模式。

### 4.6 删除后搜索结果仍出现旧文案

先确认删除接口返回成功，再检查：

```text
1. PostgreSQL 中目标文案是否已经删除
2. 关联知识库片段是否已清理
3. Milvus 是否处于运行状态
4. 后端日志是否出现向量删除失败
```

如果删除时 Milvus 未启动，数据库删除会完成，但向量删除可能失败。重新启动 Milvus 后，建议重新同步或重建相关向量数据，避免旧向量继续参与语义召回。

## 5. 一次性检查清单

后端健康检查：

```text
http://127.0.0.1:8002/api/health
```

知识库集合接口：

```text
http://127.0.0.1:8002/api/knowledge/collections
```

Swagger 文档：

```text
http://127.0.0.1:8002/docs
```

前端页面：

```text
http://localhost:5173
```

Docker 基础服务：

```powershell
docker ps
```

应重点确认：

```text
ragagent-postgres
ragagent-redis
ragagent-etcd
ragagent-minio
ragagent-milvus
```

worker：

```text
终端显示正在监听 copy_import 队列
```

附件存储：

```text
STORAGE_DIR=storage
```

归档不会删除附件；删除文案时按现有数据关联和存储设计处理附件，避免产生数据库记录与本地文件不一致。
