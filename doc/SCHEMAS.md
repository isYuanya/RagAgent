# 后端 Schema 说明

本文档说明 `app/schemas/` 中对外可见的数据契约。前端实际接入时，以本文件和 FastAPI 自动生成的 `/openapi.json` 为准。

## 1. 基础上下文

多个文案接口共享以下上下文字段，字段名保持 snake_case：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `industry` | `string \| null` | 否 | 行业或赛道，例如美妆、教育、本地生活 |
| `audience` | `string \| null` | 否 | 目标人群 |
| `platform` | `string \| null` | 否 | 内容平台，例如抖音、小红书、视频号 |
| `purpose` | `string \| null` | 否 | 内容目标，例如引流、成交、涨粉 |
| `style` | `string \| null` | 否 | 表达风格 |
| `structure_type` | `string \| null` | 否 | 结构类型 |
| `content_type` | `string \| null` | 否 | 内容类型枚举值 |

`content_type` 当前枚举值来自 `ContentType`，接口值是中文字符串：`种草`、`情绪`、`知识`、`反转`、`故事`、`干货`、`争议`。

## 2. 文案拆解

### CopyAnalysisRequest

用于 `POST /api/copy/analyze`，也是 CSV 导入时每一行转换后的内部请求结构。

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `source_text` | `string` | 是 | 原文案，最少 1 个字符 |
| `source_url` | `string \| null` | 否 | 原文案来源链接 |
| `author_name` | `string \| null` | 否 | 发布作者或账号名 |
| `author_url` | `string \| null` | 否 | 作者主页链接 |
| `author_follower_count` | `number \| null` | 否 | 作者粉丝数，必须是非负整数 |
| `metrics` | `Record<string, number> \| null` | 否 | 表现数据，例如 likes、comments、favorites、shares |

同时可传入第 1 节中的上下文字段。

### CopyAnalysisResponse

LLM 拆解后的结构化结果。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `topic` | `string` | 内容主题 |
| `target_user` | `string` | 目标用户 |
| `core_pain` | `string` | 核心痛点 |
| `emotion_buttons` | `string[]` | 情绪按钮 |
| `hook` | `string` | 开头钩子 |
| `structure` | `string[]` | 内容结构步骤 |
| `expression_skills` | `string[]` | 表达技巧 |
| `reusable_template` | `string` | 可复用模板或句式 |
| `suitable_scenarios` | `string[]` | 适用场景 |
| `risk_warnings` | `RiskWarning[]` | 风险提示 |
| `confidence` | `number` | 置信度，范围 0 到 1 |

### RiskWarning

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `level` | `string` | 否 | 风险等级，默认 `low` |
| `message` | `string` | 是 | 风险说明 |
| `suggestion` | `string \| null` | 否 | 修改建议 |

## 3. 文案资产

### CopyAssetSummary

用于资产列表、资产详情和审核更新响应。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | `string` | 后端生成的资产 ID |
| `source_text` | `string` | 原文案 |
| `source_url` | `string \| null` | 来源链接 |
| `author_name` | `string \| null` | 作者或账号名 |
| `author_url` | `string \| null` | 作者主页 |
| `author_follower_count` | `number \| null` | 作者粉丝数 |
| `metrics` | `Record<string, number>` | 表现数据，默认 `{}` |
| `status` | `string` | 审核状态：`pending_review`、`approved`、`rejected` |
| `auto_analysis` | `CopyAnalysisResponse \| null` | LLM 自动拆解结果 |
| `reviewed_analysis` | `CopyAnalysisResponse \| null` | 人工确认后的拆解结果 |

同时包含基础上下文字段：`industry`、`audience`、`platform`、`purpose`、`style`、`structure_type`、`content_type`。

### CopyAssetListResponse

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `items` | `CopyAssetSummary[]` | 当前页资产 |
| `page` | `number` | 当前页，从 1 开始 |
| `page_size` | `number` | 每页数量，1 到 100 |
| `total` | `number` | 符合筛选条件的总数 |

### CopyAssetReviewRequest

用于 `PATCH /api/copy/assets/{asset_id}/review`。

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `status` | `string` | 是 | 只能是 `pending_review`、`approved`、`rejected` |
| `reviewed_analysis` | `CopyAnalysisResponse` | 是 | 前端提交的人工确认版本 |

## 4. CSV 导入

### CopyImportRequest

用于 `POST /api/copy/import`。

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `csv_text` | `string \| null` | 否 | 前端读取 CSV 文件后提交的完整文本 |
| `text` | `string \| null` | 否 | 纯文字原文案，后端作为单条文案调用 LLM 拆解 |

`csv_text` 和 `text` 必须二选一，不能同时为空，也不能同时传。

CSV 必须包含表头 `source_text`。当前支持的列：

| CSV 列名 | 必填 | 说明 |
| --- | --- | --- |
| `source_text` | 是 | 原文案 |
| `source_url` | 否 | 来源链接 |
| `author_name` | 否 | 作者或账号名 |
| `author_url` | 否 | 作者主页链接 |
| `author_follower_count` | 否 | 非负整数 |
| `platform` | 否 | 平台 |
| `industry` | 否 | 行业 |
| `audience` | 否 | 人群 |
| `purpose` | 否 | 目的 |
| `style` | 否 | 风格 |
| `likes` | 否 | 整数 |
| `comments` | 否 | 整数 |
| `favorites` | 否 | 整数 |
| `shares` | 否 | 整数 |

当前单次导入最多处理 50 行数据。超过限制时任务会失败，并在 `progress.errors` 中返回原因。

## 5. 任务状态

### TaskResponse

用于 `POST /api/copy/import` 的返回值，以及 `GET /api/tasks/{task_id}` 的轮询结果。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `task_id` | `string` | 任务 ID |
| `status` | `string` | 任务状态，常见值：`queued`、`running`、`finished`、`failed` |
| `result` | `object \| null` | 完成后的结果 |
| `error` | `string \| null` | 失败原因 |
| `progress` | `TaskProgress \| null` | 进度信息 |

导入完成时，`result` 当前结构为：

```json
{
  "imported_count": 2,
  "failed_count": 0,
  "asset_ids": ["asset-id-1", "asset-id-2"]
}
```

### TaskProgress

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `phase` | `string` | 当前阶段：`queued`、`parsing_csv`、`calling_llm`、`saving_asset`、`finished`、`failed` |
| `model` | `string \| null` | 当前任务使用的 LLM 模型 |
| `current_row` | `number` | 当前处理到的 CSV 行号，包含表头偏移 |
| `total_rows` | `number` | CSV 数据总行数，不含表头 |
| `processed_count` | `number` | 已处理行数 |
| `success_count` | `number` | 成功导入数量 |
| `failed_count` | `number` | 失败行数 |
| `percent` | `number` | 进度百分比，0 到 100 |
| `current_message` | `string \| null` | 当前状态说明 |
| `errors` | `object[]` | 行级错误列表，通常包含 `row_number` 和 `message` |

## 6. 兼容性约定

- 后端新增字段时优先使用可选字段，避免破坏前端。
- 前端不要依赖 `current_message` 的固定文案；它只适合展示，不适合作为业务判断条件。
- 前端业务判断应优先使用 `status`、`progress.phase`、`progress.percent`、`result.asset_ids`。
- FastAPI 默认校验错误会返回 `422`，错误结构由 FastAPI/Pydantic 生成。

## 7. knowledge.py

`knowledge.py` 定义六类知识库和集合层的 API 契约。

主要对象：

| 对象 | 说明 |
| --- | --- |
| `KnowledgeCollection` | 知识库集合，例如美妆库、高转化库、某账号库 |
| `RawCopySummary` | 原始文案库条目，继承文案资产字段，并增加 `collection_ids` 和 `collections` |
| `AnalysisSummary` | 结构化拆解库条目，包含 `raw_copy_id`、`auto_analysis`、`reviewed_analysis`、`status` |
| `TemplateItem` | 模板库条目，保存句式、框架、适用场景 |
| `TagItem` | 标签库条目，保存行业、情绪、目的、人群、钩子类型 |
| `CaseItem` | 案例库条目，保存高表现原因 |
| `BlockItem` | 禁用库条目，保存敏感词、违规表达、不要复刻内容 |

模板、标签、案例、禁用项共享来源追溯字段：

```json
{
  "source": {
    "source_type": "raw_copy",
    "source_id": "raw-copy-id"
  }
}
```

`source_type` 当前支持 `raw_copy` 和 `analysis`。

所有列表响应都包含：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `items` | `array` | 当前页数据 |
| `page` | `number` | 当前页 |
| `page_size` | `number` | 每页数量 |
| `total` | `number` | 总数 |

### FragmentItem

片段级拆解库条目，用于保存原文案拆分后的片段及其上下文。接口路径为 `/api/knowledge/fragments`。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | `string` | 片段 ID |
| `source_copy_id` | `string` | 来源原文案 ID |
| `analysis_id` | `string \| null` | 来源拆解结果 ID |
| `sequence_order` | `number` | 片段顺序 |
| `previous_fragment` | `string \| null` | 上一个片段文本 |
| `next_fragment` | `string \| null` | 下一个片段文本 |
| `before_context` | `string \| null` | 前置上下文 |
| `after_context` | `string \| null` | 后置上下文 |
| `fragment_text` | `string` | 片段正文 |
| `fragment_role` | `string` | 片段角色 |
| `position` | `string` | 片段位置 |
| `industry` | `string \| null` | 行业弱标签 |
| `platform` | `string \| null` | 来源平台，用于筛选 |
| `purpose` | `string \| null` | 来源文案目的，用于筛选 |
| `audience` | `string \| null` | 来源目标人群，用于筛选 |
| `source_quality` | `"unknown" \| "low" \| "medium" \| "high"` | 来源质量弱标签 |
| `risk_level` | `"low" \| "medium" \| "high"` | 风险弱标签 |
| `status` | `"pending_review" \| "approved" \| "rejected"` | 片段审核状态；高置信度自动拆解片段为 `approved`，低置信度为 `pending_review` |
| `confidence` | `number` | 片段拆解置信度，范围 0 到 1 |
| `metadata` | `object` | 扩展字段 |

`GET /api/knowledge/fragments` 支持筛选参数：`source_copy_id`、`fragment_role`、`position`、`industry`、`status`、`platform`、`purpose`、`audience`、`risk_level`、`q`。`q` 是基于片段正文和上下文的关键词搜索，当前不是向量检索。

### Fragment Extraction

用于给已审核文案生成或补生成片段。

- `POST /api/knowledge/fragments/extract/{source_copy_id}`：对单篇已审核文案触发片段拆解。
- `POST /api/knowledge/fragments/extract-approved?limit=50`：批量扫描已审核文案，只给尚未生成片段的文案补生成片段。

响应结构：

```json
{
  "source_copy_id": "copy-id",
  "status": "created | skipped | failed",
  "fragment_count": 1,
  "message": "optional detail"
}
```

批量接口响应：

```json
{
  "items": [],
  "processed_count": 1,
  "created_count": 1,
  "failed_count": 0
}
```

## 8.1 Derived Knowledge Sync

After CSV or plain-text import finishes, backend derives specialized knowledge records from
the copy analysis.

- Template library: `reusable_template`, `structure`, and `suitable_scenarios`.
- Tag library: source `industry`, `purpose`, `audience`, analysis `target_user`,
  `emotion_buttons`, `hook`, and `expression_skills`.
- Block library: `risk_warnings`.
- Case library: positive performance `metrics`.

Template, tag, case, and block responses keep source traceability:

```json
{
  "source": {
    "source_type": "raw_copy",
    "source_id": "raw-copy-id",
    "source_display": "source copy excerpt"
  }
}
```

Frontend should render `source.source_display` when present. Keep `source.source_id`
for detail navigation and API calls.

If the imported copy asset is auto-approved by LLM confidence, backend also triggers
function-level fragment extraction immediately. If the asset stays `pending_review`,
fragments are created later when the asset is approved or when the manual extraction
endpoint is called.

### CopyAsset Delete

用于 `DELETE /api/copy/assets/{asset_id}`。

- 仅允许删除 `status = pending_review` 的资产。
- 删除成功返回 `204`，响应体为空。
- 资产不存在或已删除返回 `404`。
- 资产已经审核通过或拒绝返回 `409`。
