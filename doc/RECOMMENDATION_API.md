# Phase 4 下一句推荐后端接口

本文档给前端说明 Phase 4 新增的 AI 下一句推荐 API。后端默认地址仍是 `http://127.0.0.1:8002`，统一前缀是 `/api`。

## 1. 创建推荐任务

```text
POST /api/recommendations/next-sentence
```

请求：

```json
{
  "draft_id": "draft-id",
  "candidate_count": 3,
  "cursor_item_id": null,
  "q": null,
  "metadata": {}
}
```

字段说明：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `draft_id` | string | 是 | 当前草稿 ID |
| `candidate_count` | number | 否 | 默认 3，范围 1-5 |
| `cursor_item_id` | string \| null | 否 | 预留字段，后续可支持从指定 item 后推荐 |
| `q` | string \| null | 否 | 可选检索关键词；不传时后端用草稿当前文本 |
| `metadata` | object | 否 | 前端扩展信息 |

响应是标准 `TaskResponse`：

```json
{
  "task_id": "task-id",
  "status": "running",
  "result": null,
  "error": null,
  "progress": {
    "phase": "queued",
    "model": "glm-5.1",
    "percent": 0,
    "current_message": "Recommendation task created.",
    "errors": []
  }
}
```

前端继续轮询：

```text
GET /api/tasks/{task_id}
```

## 2. 推荐任务结果

任务完成后，`TaskResponse.result` 结构如下：

```json
{
  "draft_id": "draft-id",
  "current_text": "当前草稿全文",
  "next_function": "proof",
  "model": "glm-5.1",
  "reference_fragments": [
    {
      "id": "fragment-id",
      "text": "参考片段文本",
      "role": "proof",
      "position": "body",
      "source_copy_id": "raw-copy-id",
      "source_display": "原文摘要"
    }
  ],
  "candidates": [
    {
      "candidate_id": "candidate-id",
      "text": "候选句或 1-2 句话的微段落",
      "function": "proof",
      "reason": "为什么适合接在这里",
      "tone": "specific and calm",
      "suggested_order_index": 1,
      "risk_warnings": [],
      "reference_fragment_ids": ["fragment-id"],
      "reference_fragments": []
    }
  ]
}
```

前端展示建议：

- 用 `next_function` 显示本次 AI 判断的下一句功能。
- 每个候选展示 `text`、`reason`、`tone`、`risk_warnings`。
- 来源展示优先用 `reference_fragments[*].text` 和 `source_display`，不要只展示 ID。
- `candidate_id` 是采纳接口必需字段。

## 3. 采纳推荐

```text
POST /api/recommendations/accepted
```

请求：

```json
{
  "draft_id": "draft-id",
  "task_id": "task-id",
  "candidate_id": "candidate-id",
  "order_index": null,
  "metadata": {}
}
```

字段说明：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `draft_id` | string | 是 | 当前草稿 ID |
| `task_id` | string | 是 | 推荐任务 ID |
| `candidate_id` | string | 是 | 被采纳候选 ID |
| `order_index` | number \| null | 否 | 自定义插入顺序；不传时使用候选的 `suggested_order_index` |
| `metadata` | object | 否 | 前端扩展信息 |

响应：

```json
{
  "accepted": {
    "id": "accepted-id",
    "draft_id": "draft-id",
    "task_id": "task-id",
    "candidate_id": "candidate-id",
    "inserted_draft_item_id": "draft-item-id",
    "candidate_text": "候选句",
    "function": "proof",
    "tone": "specific and calm",
    "reason": "为什么适合接在这里",
    "model": "glm-5.1",
    "reference_fragment_ids": ["fragment-id"],
    "metadata": {}
  },
  "draft": {
    "id": "draft-id",
    "current_text": "插入推荐后的草稿全文",
    "item_count": 2,
    "items": []
  }
}
```

采纳接口由后端同时完成两件事：

- 把候选文本作为新的 draft item 插入草稿。
- 保存 accepted recommendation 记录，供后续分析采纳效果。

未采纳的候选不会持久化。

## 4. 错误规则

| 场景 | 状态码 |
| --- | --- |
| 请求字段不合法 | `422` |
| 草稿不存在 | `404` |
| 推荐任务不存在 | `404` |
| 候选不存在或不属于该草稿 | `404` |

## 5. 当前 MVP 边界

- 不做自动整篇组稿。
- 不引入 Milvus/vector/reranker。
- 推荐候选是 1-2 句话，仍作为一个 draft item 插入。
- 推荐使用 PostgreSQL 片段库结构化过滤和关键词召回作为参考材料。
