# 前端对接文档

本文档给前端说明当前后端 API、字段、任务进度和联调规则。后端默认本地地址是 `http://127.0.0.1:8002`，API 前缀默认是 `/api`。

## 1. 联调入口

| 项 | 地址 |
| --- | --- |
| 后端根地址 | `http://127.0.0.1:8002/` |
| 健康检查 | `GET http://127.0.0.1:8002/api/health` |
| Swagger UI | `http://127.0.0.1:8002/docs` |
| OpenAPI JSON | `http://127.0.0.1:8002/openapi.json` |

默认 CORS 允许本地开发来源：`localhost` 和 `127.0.0.1` 的任意端口。常见前端地址如 `http://localhost:5173`、`http://127.0.0.1:5173`、`http://127.0.0.1:5174` 都会返回 CORS 头。

如果需要接入非本机域名，在后端 `.env` 中配置：

```env
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
CORS_ORIGIN_REGEX=^https?://(localhost|127\.0\.0\.1)(:\d+)?$
```

## 2. 文案拆解

### `POST /api/copy/analyze`

直接提交单条原文案并同步返回 LLM 拆解结果。

请求示例：

```json
{
  "source_text": "如果你总觉得护肤没效果，先别急着换产品，可能是使用顺序错了。",
  "source_url": "https://example.com/post/1",
  "author_name": "护肤研究员",
  "author_url": "https://example.com/u/skin",
  "author_follower_count": 52000,
  "industry": "美妆",
  "audience": "25-35岁女性",
  "platform": "小红书",
  "purpose": "引流",
  "style": "专业/共情",
  "metrics": {
    "likes": 1200,
    "comments": 88,
    "favorites": 300,
    "shares": 42
  }
}
```

响应核心字段：

```json
{
  "topic": "护肤使用顺序",
  "target_user": "护肤效果不明显的人群",
  "core_pain": "投入护肤成本但看不到效果",
  "emotion_buttons": ["共鸣", "好奇"],
  "hook": "如果你总觉得护肤没效果，先别急着换产品。",
  "structure": ["提出问题", "解释原因", "给出建议"],
  "expression_skills": ["反问", "痛点共鸣"],
  "reusable_template": "如果你总觉得____，先别急着____，可能是____。",
  "suitable_scenarios": ["种草", "私域引流"],
  "risk_warnings": [],
  "confidence": 0.8
}
```

常见错误：

- `422`：请求字段类型或必填字段错误。
- `503`：LLM 配置缺失或调用失败。
- `502`：LLM 返回内容无法被后端解析为有效结构。

## 3. CSV 导入

### `POST /api/copy/import`

前端读取 CSV 文件内容后，把完整文本放入 `csv_text` 提交。后端会创建导入任务，并逐行调用 LLM 拆解。

请求示例：

```json
{
  "csv_text": "source_text,platform,author_name,author_follower_count\n如果你总觉得护肤没效果，小红书,护肤研究员,52000"
}
```

响应示例：

```json
{
  "task_id": "580f3445-6c14-4a19-89f5-b66da6b0c416",
  "status": "running",
  "result": null,
  "error": null,
  "progress": {
    "phase": "queued",
    "model": "gpt-4.1-mini",
    "current_row": 0,
    "total_rows": 0,
    "processed_count": 0,
    "success_count": 0,
    "failed_count": 0,
    "percent": 0,
    "current_message": "任务已入队",
    "errors": []
  }
}
```

CSV 表头要求：

| 列名 | 必填 | 类型/说明 |
| --- | --- | --- |
| `source_text` | 是 | 原文案，不能为空 |
| `source_url` | 否 | 来源链接 |
| `author_name` | 否 | 作者或账号名 |
| `author_url` | 否 | 作者主页链接 |
| `author_follower_count` | 否 | 非负整数 |
| `platform` | 否 | 平台 |
| `industry` | 否 | 行业 |
| `audience` | 否 | 人群 |
| `purpose` | 否 | 内容目标 |
| `style` | 否 | 风格 |
| `likes` | 否 | 整数 |
| `comments` | 否 | 整数 |
| `favorites` | 否 | 整数 |
| `shares` | 否 | 整数 |

前端上传注意事项：

- 建议用 UTF-8 或 UTF-8 BOM CSV，避免中文乱码。
- 单次最多 50 行数据，不含表头。
- `likes`、`comments`、`favorites`、`shares`、`author_follower_count` 传空表示未知；非空时必须是整数。

## 4. 任务轮询与进度条

### `GET /api/tasks/{task_id}`

前端在导入后用 `task_id` 轮询该接口。建议每 1 到 2 秒轮询一次，直到 `status` 为 `finished` 或 `failed`。

响应示例：

```json
{
  "task_id": "580f3445-6c14-4a19-89f5-b66da6b0c416",
  "status": "finished",
  "result": {
    "imported_count": 2,
    "failed_count": 0,
    "asset_ids": [
      "0c61bc84-f3db-4e70-8dc6-8da703e2c598"
    ]
  },
  "error": null,
  "progress": {
    "phase": "finished",
    "model": "gpt-4.1-mini",
    "current_row": 3,
    "total_rows": 2,
    "processed_count": 2,
    "success_count": 2,
    "failed_count": 0,
    "percent": 100,
    "current_message": "导入完成。",
    "errors": []
  }
}
```

前端展示规则建议：

- 进度条使用 `progress.percent`，没有 `progress` 时显示 0 或不展示进度条。
- LLM 状态显示 `progress.phase` 和 `progress.model`。
- 当前处理信息显示 `progress.current_message`，但不要用它做逻辑判断。
- `status === "finished"` 后，使用 `result.asset_ids` 拉取详情，或刷新资产列表。
- `status === "failed"` 时展示 `error`，同时展示 `progress.errors` 中的行级错误。

`progress.phase` 当前常见值：

| 值 | 前端含义 |
| --- | --- |
| `queued` | 已创建或已入队 |
| `parsing_csv` | 正在解析 CSV |
| `calling_llm` | 正在调用 LLM 拆解 |
| `saving_asset` | 正在保存资产 |
| `finished` | 已完成 |
| `failed` | 已失败 |

## 5. 文案资产

### `GET /api/copy/assets`

分页查询资产。

查询参数：

| 参数 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `page` | number | `1` | 从 1 开始 |
| `page_size` | number | `20` | 1 到 100 |
| `status` | string | 无 | 可选：`pending_review`、`approved`、`rejected` |
| `industry` | string | 无 | 行业筛选 |
| `platform` | string | 无 | 平台筛选 |

响应示例：

```json
{
  "items": [
    {
      "id": "0c61bc84-f3db-4e70-8dc6-8da703e2c598",
      "source_text": "如果你总觉得护肤没效果...",
      "source_url": "https://example.com/post/1",
      "author_name": "护肤研究员",
      "author_url": "https://example.com/u/skin",
      "author_follower_count": 52000,
      "platform": "小红书",
      "industry": "美妆",
      "audience": "25-35岁女性",
      "purpose": "引流",
      "style": "专业/共情",
      "structure_type": null,
      "content_type": null,
      "metrics": {
        "likes": 1200
      },
      "status": "pending_review",
      "auto_analysis": null,
      "reviewed_analysis": null
    }
  ],
  "page": 1,
  "page_size": 20,
  "total": 1
}
```

### `GET /api/copy/assets/{asset_id}`

查看单条资产详情。资产不存在返回 `404`。

### `PATCH /api/copy/assets/{asset_id}/review`

提交人工审核后的拆解结果。

请求示例：

```json
{
  "status": "approved",
  "reviewed_analysis": {
    "topic": "护肤使用顺序",
    "target_user": "护肤效果不明显的人群",
    "core_pain": "投入护肤成本但看不到效果",
    "emotion_buttons": ["共鸣"],
    "hook": "如果你总觉得护肤没效果，先别急着换产品。",
    "structure": ["提出问题", "解释原因", "给出建议"],
    "expression_skills": ["痛点共鸣"],
    "reusable_template": "如果你总觉得____，先别急着____。",
    "suitable_scenarios": ["种草"],
    "risk_warnings": [],
    "confidence": 0.8
  }
}
```

`status` 只能是：

- `pending_review`
- `approved`
- `rejected`

## 6. 前端需要遵守的契约

- 业务判断使用结构化字段，不解析中文提示文案。
- 作者相关字段都是可选字段；前端展示时需要处理 `null`。
- `auto_analysis` 可能为 `null`，例如历史数据或异常导入数据。
- `reviewed_analysis` 只有人工审核后才有值。
- 导入完成后不保证列表自动排序方式长期不变；如果要展示刚导入数据，优先用 `result.asset_ids` 获取详情。
- 后端字段名当前统一使用 snake_case；前端如转 camelCase，需要在 API 层统一转换。

## 7. 知识库 API

后端新增统一知识库命名空间 `/api/knowledge`。现有 `/api/copy/assets` 保持兼容；新页面建议优先接入知识库 API。

### 端点总览

| 知识库 | 端点 | 用途 |
| --- | --- | --- |
| 集合 | `/api/knowledge/collections` | 管理“美妆库”“高转化库”“某账号库”等集合 |
| 原始文案库 | `/api/knowledge/raw-copies` | 保存原文、来源、作者、指标、所属集合 |
| 结构化拆解库 | `/api/knowledge/analyses` | 保存自动拆解和人工审核结果 |
| 模板库 | `/api/knowledge/templates` | 人工维护句式、框架、适用场景 |
| 标签库 | `/api/knowledge/tags` | 人工维护行业、情绪、目的、人群、钩子类型 |
| 案例库 | `/api/knowledge/cases` | 人工维护高表现案例及原因 |
| 禁用库 | `/api/knowledge/blocks` | 人工维护敏感词、违规表达、不要复刻内容 |

每个端点都支持标准 CRUD：

```text
GET    /api/knowledge/<resource>?page=1&page_size=20
POST   /api/knowledge/<resource>
GET    /api/knowledge/<resource>/{id}
PATCH  /api/knowledge/<resource>/{id}
DELETE /api/knowledge/<resource>/{id}
```

删除为软删除语义：删除成功返回 `204`，后续列表和详情不再显示。

### 集合

创建集合：

```json
{
  "name": "美妆库",
  "description": "美妆相关文案",
  "metadata": {}
}
```

响应：

```json
{
  "id": "collection-id",
  "name": "美妆库",
  "description": "美妆相关文案",
  "metadata": {}
}
```

### 原始文案库

创建原始文案：

```json
{
  "source_text": "先别急着换产品，可能是护肤顺序错了。",
  "source_url": "https://example.com/post/1",
  "author_name": "护肤研究员",
  "author_url": "https://example.com/u/skin",
  "author_follower_count": 52000,
  "platform": "小红书",
  "industry": "美妆",
  "audience": "25-35岁女性",
  "purpose": "引流",
  "style": "专业/共情",
  "metrics": {
    "likes": 1200
  },
  "collection_ids": ["collection-id"]
}
```

列表支持按集合筛选：

```text
GET /api/knowledge/raw-copies?collection_id=collection-id
```

响应中的每条原始文案会包含：

- `collection_ids`
- `collections`
- 原有文案资产字段，例如 `source_text`、`source_url`、`author_name`、`metrics`、`auto_analysis`

CSV 导入成功后，文案也会出现在原始文案库和结构化拆解库中。

### 来源追溯字段

模板、标签、案例、禁用项都支持可选 `source`：

```json
{
  "source": {
    "source_type": "raw_copy",
    "source_id": "raw-copy-id"
  }
}
```

`source_type` 可选：

- `raw_copy`
- `analysis`

### 模板库示例

```json
{
  "title": "问题反转模板",
  "content": "如果你总觉得____，先检查____。",
  "structure": ["提出问题", "解释原因", "行动建议"],
  "suitable_scenarios": ["种草", "私域引流"],
  "source": {
    "source_type": "raw_copy",
    "source_id": "raw-copy-id"
  },
  "metadata": {}
}
```

### 标签库示例

```json
{
  "name": "共鸣",
  "category": "emotion",
  "description": "用于标记情绪共鸣型表达",
  "source": {
    "source_type": "raw_copy",
    "source_id": "raw-copy-id"
  },
  "metadata": {}
}
```

`category` 可选：`industry`、`emotion`、`purpose`、`audience`、`hook_type`、`custom`。

### 案例库示例

```json
{
  "title": "高收藏护肤案例",
  "reason": "开头直接命中使用误区。",
  "performance_summary": "收藏率高，评论集中在求步骤。",
  "source": {
    "source_type": "raw_copy",
    "source_id": "raw-copy-id"
  },
  "metadata": {}
}
```

### 禁用库示例

```json
{
  "content": "百分百有效",
  "block_type": "violation",
  "reason": "绝对化承诺",
  "severity": "high",
  "source": {
    "source_type": "raw_copy",
    "source_id": "raw-copy-id"
  },
  "metadata": {}
}
```

`block_type` 可选：`sensitive_word`、`violation`、`do_not_copy`、`custom`。  
`severity` 可选：`low`、`medium`、`high`。

## 8. 片段级拆解库

片段级拆解库用于保存一条原文案被拆分后的片段、片段上下文、片段角色和弱标签。当前接口只负责持久化和查询，不会自动调用 LLM；前端可以在人工拆分或后端拆分任务完成后写入。

端点：

```text
GET    /api/knowledge/fragments?page=1&page_size=20
POST   /api/knowledge/fragments
GET    /api/knowledge/fragments/{id}
PATCH  /api/knowledge/fragments/{id}
DELETE /api/knowledge/fragments/{id}
```

列表支持筛选：

```text
GET /api/knowledge/fragments?source_copy_id=raw-copy-id
GET /api/knowledge/fragments?fragment_role=hook&position=opening&industry=beauty
```

创建示例：

```json
{
  "source_copy_id": "raw-copy-id",
  "analysis_id": "analysis-id",
  "sequence_order": 0,
  "previous_fragment": null,
  "next_fragment": "然后解释为什么会这样",
  "before_context": null,
  "after_context": "承接痛点后的原因解释",
  "fragment_text": "先别急着换产品",
  "fragment_role": "hook",
  "position": "opening",
  "industry": "beauty",
  "source_quality": "high",
  "risk_level": "low",
  "metadata": {}
}
```

字段说明：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `source_copy_id` | string | 是 | 来源原文案 ID，对应 `/api/knowledge/raw-copies/{id}` |
| `analysis_id` | string \| null | 否 | 来源拆解结果 ID，对应 `/api/knowledge/analyses/{id}` |
| `sequence_order` | number | 是 | 片段在原文里的顺序 |
| `previous_fragment` | string \| null | 否 | 上一个片段文本 |
| `next_fragment` | string \| null | 否 | 下一个片段文本 |
| `before_context` | string \| null | 否 | 片段前置上下文 |
| `after_context` | string \| null | 否 | 片段后置上下文 |
| `fragment_text` | string | 是 | 当前片段正文 |
| `fragment_role` | string | 是 | 片段角色，例如 `hook`、`pain_point`、`proof`、`cta` |
| `position` | string | 是 | 位置，例如 `opening`、`middle`、`ending` |
| `industry` | string \| null | 否 | 行业弱标签 |
| `source_quality` | string | 否 | `unknown`、`low`、`medium`、`high` |
| `risk_level` | string | 否 | `low`、`medium`、`high` |
| `metadata` | object | 否 | 扩展字段 |

## 9. 纯文字导入

`POST /api/copy/import` 现在支持两种输入，二选一：

- `csv_text`：原有 CSV 导入。
- `text`：纯文字导入，后端会把整段文字作为单条原文案调用 LLM 拆解并保存为文案资产。

纯文字请求示例：

```json
{
  "text": "先别急着换产品，可能是护肤顺序错了。"
}
```

响应仍然是 `TaskResponse`，字段和 CSV 导入一致：

```json
{
  "task_id": "task-id",
  "status": "finished",
  "result": {
    "imported_count": 1,
    "failed_count": 0,
    "asset_ids": ["asset-id"]
  },
  "error": null,
  "progress": {
    "phase": "finished",
    "model": "glm-5.1",
    "current_row": 1,
    "total_rows": 1,
    "processed_count": 1,
    "success_count": 1,
    "failed_count": 0,
    "percent": 100,
    "current_message": "Plain text import finished.",
    "errors": []
  }
}
```

前端约束：

- `csv_text` 和 `text` 只能传一个。
- `text` 不能为空字符串。
- 导入完成后用 `result.asset_ids` 拉取 `/api/copy/assets/{asset_id}` 或刷新资产列表。
