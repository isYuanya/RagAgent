# 智能组稿助手接口说明

本文档给前端接入 `智能组稿助手` 使用。后端接口前缀为 `/api/assistant`。

## 目标

智能组稿助手把已有的能力串起来：

1. 接收结构化 brief。
2. 检索片段库素材。
3. 生成 3 个组稿候选。
4. 规则排序后交给 LLM 选择候选，失败时记录规则兜底。
5. 创建草稿并保存初稿版本。
6. 对初稿做文案诊断。
7. 规则排序后交给 LLM 选择改写，失败时记录规则兜底。
8. 替换草稿为终稿并保存终稿版本。

## 接口

### 获取选项

`GET /api/assistant/options`

返回：

```json
{
  "collections": [],
  "platforms": [{ "value": "xhs", "label": "小红书" }],
  "purposes": [{ "value": "conversion", "label": "转化" }],
  "audiences": [{ "value": "new_users", "label": "新用户" }],
  "styles": [{ "value": "practical", "label": "干货型" }]
}
```

### 自然语言预填

`POST /api/assistant/brief-prefill`

请求：

```json
{
  "text": "给小红书新用户写一篇护肤顺序转化文案"
}
```

返回 `brief`、`confidence`、`notes`、`model`。预填只填表，不会自动开始生成。

### 创建工作流

`POST /api/assistant/runs`

请求：

```json
{
  "mode": "auto",
  "brief": {
    "product": "护肤顺序",
    "audience": "new_users",
    "platform": "xhs",
    "purpose": "conversion",
    "style": "practical",
    "key_selling_points": ["先补水再封层"],
    "constraints": "不要绝对化表达",
    "target_length": "300 字以内",
    "collection_ids": [],
    "extra_notes": null
  }
}
```

`mode` 可选：

- `auto`：一键跑到终稿。
- `guided`：当前后端会生成候选并暂停为 `waiting_for_user`。后续确认端点会继续补。

返回核心字段：

- `status`：`pending`、`running`、`waiting_for_user`、`finished`、`failed`
- `timeline`：步骤进度、状态、模型、原因
- `draft_id`：生成的草稿 ID
- `initial_version_id`：初稿版本 ID
- `final_version_id`：终稿版本 ID
- `result.composition`：组稿结果
- `result.diagnosis`：诊断结果
- `result.composition_selection`：组稿选择方式和理由
- `result.rewrite_selection`：改写选择方式和理由
- `result.draft.current_text`：当前终稿文本

### 查询历史

`GET /api/assistant/runs?page=1&page_size=30`

用于左侧历史列表。

### 查询详情

`GET /api/assistant/runs/{run_id}`

用于打开历史详情。

## 前端展示建议

- 主流程按钮默认使用 `auto`。
- `timeline.percent` 可用于进度条，`timeline.status` 用于步骤图标。
- 模型展示优先取步骤上的 `model`，其次取 `result.composition.model` 和 `result.diagnosis.model`。
- 如果 `status=waiting_for_user`，展示当前候选和“等待确认”的状态，不要当作失败。
- 如果选择方式是 `rule_fallback`，把 `fallback_reason` 显示为弱提示，方便排查 LLM 选择 JSON 失败。
