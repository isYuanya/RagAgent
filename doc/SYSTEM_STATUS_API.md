# System Status API

后端提供依赖服务状态接口，前端可用它判断 Redis、PostgreSQL、worker、Milvus 是否已启动。

## Endpoint

```http
GET /api/system/status
```

该接口即使依赖服务未启动也应返回 `200`，依赖失败会体现在响应体里。

## Response

```json
{
  "status": "down",
  "services": [
    {
      "name": "postgres",
      "required": true,
      "status": "ok",
      "latency_ms": 3,
      "endpoint": "postgresql+psycopg://rag:***@localhost:5432/rag",
      "message": "PostgreSQL is reachable."
    },
    {
      "name": "redis",
      "required": true,
      "status": "ok",
      "latency_ms": 1,
      "endpoint": "redis://localhost:6379/0",
      "message": "Redis is reachable."
    },
    {
      "name": "copy_import_worker",
      "required": true,
      "status": "down",
      "latency_ms": 1,
      "endpoint": "copy_import",
      "message": "No worker is listening on copy_import; import tasks may stay queued."
    },
    {
      "name": "milvus",
      "required": false,
      "status": "degraded",
      "latency_ms": 1000,
      "endpoint": "http://localhost:19530",
      "message": "Milvus is not reachable: URLError."
    }
  ]
}
```

## Overall Status

- `ok`: 所有 required 和 optional 服务都正常。
- `down`: 至少一个 required 服务异常。当前 required 服务包括 `postgres`、`redis`、`copy_import_worker`。
- `degraded`: required 服务正常，但 optional 服务异常。当前 optional 服务是 `milvus`。

## Frontend Usage Notes

- 页面顶部可以显示整体状态：
  - `ok`: 正常
  - `degraded`: 可用但部分能力受限
  - `down`: 核心能力不可用
- 导入功能依赖 `redis` 和 `copy_import_worker`。如果 `copy_import_worker.status = down`，前端应提示“导入任务可能会一直停留在队列中，请启动 worker”。
- 数据持久化依赖 `postgres`。如果 `postgres.status = down`，前端应提示“数据可能无法真正落库”。
- `endpoint` 已做密码脱敏，可以直接展示给开发者。
