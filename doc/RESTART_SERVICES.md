# 重启电脑后的服务启动清单

本文档用于本地开发环境重启后，按顺序恢复 RagAgent 项目服务。

项目目录：

```powershell
cd C:\RagAgent
```

## 1. 必须启动的服务
sudo service redis-server start
C:\RagAgent\.venv\Scripts\python.exe C:\RagAgent\scripts\worker.py
C:\RagAgent\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8002
### 1.1 后端 API

后端默认地址：

```text
http://127.0.0.1:8002
```

推荐用无 reload 模式启动，避免 Windows 上残留 reload 子进程导致旧路由继续响应：

```powershell
C:\RagAgent\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8002
```

启动后验证：

```powershell
Invoke-WebRequest http://127.0.0.1:8002/api/health -UseBasicParsing
Invoke-WebRequest http://127.0.0.1:8002/api/knowledge/collections -UseBasicParsing
```

正常情况下：

- `/api/health` 返回 `200`
- `/api/knowledge/collections` 返回类似：

```json
{"items":[],"page":1,"page_size":20,"total":0}
```

### 1.2 前端页面

前端目录：

```powershell
cd C:\RagAgent\frontend
```

开发模式启动：

```powershell
npm run dev
```

浏览器打开 Vite 输出的地址，通常是：

```text
http://localhost:5173
```

如果 5173 被占用，Vite 会自动换到 5174、5175 等端口。后端 CORS 当前允许 `localhost` 和 `127.0.0.1` 的本地端口。

## 2. 按需启动的服务

### 2.1 Redis

CSV 导入使用后台队列时需要 Redis。默认配置：

```text
REDIS_URL=redis://localhost:6379/0
```

如果不启动 Redis，worker 会报：

```text
Redis is not reachable. Start Redis first or update REDIS_URL in .env.
```

Redis 启动方式取决于你的安装方式：

```powershell
# 如果你用 Docker
docker run --name ragagent-redis -p 6379:6379 -d redis:7

# 如果容器已经存在
docker start ragagent-redis
```

验证 Redis：

```powershell
docker ps
```

### 2.2 后台 Worker

worker 用于处理 CSV 导入任务队列。启动前先确保 Redis 已启动。

```powershell
cd C:\RagAgent
C:\RagAgent\.venv\Scripts\python.exe C:\RagAgent\scripts\worker.py
```

当前 worker 监听队列：

```text
copy_import
```

### 2.3 PostgreSQL

知识库持久化默认使用 PostgreSQL：

```text
DATABASE_URL=postgresql+psycopg://rag:rag@localhost:5432/rag
```

如果 PostgreSQL 没启动，部分知识库接口会退回内存模式；页面可能能打开，但数据不会真正持久化。

如果你使用 Docker，可以按自己的容器名启动，例如：

```powershell
docker start ragagent-postgres
```

数据库启动后，确认迁移已执行：

```powershell
cd C:\RagAgent
C:\RagAgent\.venv\Scripts\alembic.exe upgrade head
```

## 3. 推荐启动顺序

```text
1. PostgreSQL
2. Redis
3. 后端 API: uvicorn app.main:app --port 8002
4. 后台 worker: scripts\worker.py
5. 前端: npm run dev
```

最小可用模式：

```text
1. 后端 API
2. 前端
```

最小可用模式适合只查看页面和普通接口；CSV 异步导入和持久化能力需要 Redis/PostgreSQL。

## 4. 常见故障

### 4.1 前端显示“加载集合失败”

先检查后端接口：

```powershell
Invoke-WebRequest http://127.0.0.1:8002/api/knowledge/collections -UseBasicParsing
```

如果返回 `404`，说明当前 8002 上运行的是旧后端实例，或者启动入口不对。处理方式：

```powershell
netstat -ano | Select-String ':8002'
```

找到占用 8002 的 PID 后结束它：

```powershell
taskkill /PID <PID> /F
```

然后用推荐命令重新启动后端：

```powershell
C:\RagAgent\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8002
```

### 4.2 worker 启动时报 Redis 连接失败

说明 Redis 没启动，或者 `.env` 里的 `REDIS_URL` 不对。先启动 Redis，再启动 worker。

### 4.3 端口被占用

查看 8002：

```powershell
netstat -ano | Select-String ':8002'
```

查看前端端口：

```powershell
netstat -ano | Select-String ':5173'
```

结束指定进程：

```powershell
taskkill /PID <PID> /F
```

## 5. 一次性检查清单

- 后端健康检查：`http://127.0.0.1:8002/api/health`
- 知识库集合：`http://127.0.0.1:8002/api/knowledge/collections`
- Swagger 文档：`http://127.0.0.1:8002/docs`
- 前端页面：`http://localhost:5173`
- Redis：`docker ps` 中能看到 Redis 容器，或本机 6379 端口可用
- worker：终端显示正在监听 `copy_import`
