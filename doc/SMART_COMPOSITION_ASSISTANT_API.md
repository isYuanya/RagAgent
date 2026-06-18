# 智能组稿助手接口说明

本文档给前端接入 `智能组稿助手` 使用。后端接口前缀为 `/api/assistant`。

## 目标

智能组稿助手使用 LangGraph `StateGraph` 编排已有能力：

1. 接收结构化 brief。
2. 检索片段库素材。
3. 生成 3 个组稿候选。
4. 自动模式用规则排序 + LLM judge 选择候选。
5. 向导模式用 LangGraph `interrupt()` 暂停，等待用户选择。
6. 创建草稿并保存初稿版本。
7. 对初稿做文案诊断。
8. 自动模式选择改写，向导模式等待用户选择改写。
9. 替换草稿为终稿并保存终稿版本。

## 工作流模式

- `auto`：一键跑到终稿。
- `guided`：在素材确认、组稿确认、改写确认三个点暂停。

当前 MVP 使用内存 checkpointer。后端进程重启后，未完成的 guided interrupt 执行态会丢失；`smart_composition_runs` 业务历史仍会保留。

## 接口

### 获取选项

`GET /api/assistant/options`

返回 collections、platforms、purposes、audiences、styles。

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

返回核心字段：

- `status`：`pending`、`running`、`waiting_for_user`、`finished`、`failed`
- `timeline`：步骤进度、状态、模型、原因
- `metadata.pending_interrupt.type`：当前等待确认类型
- `draft_id`：生成的草稿 ID
- `initial_version_id`：初稿版本 ID
- `final_version_id`：终稿版本 ID
- `result.materials`：检索到的素材
- `result.composition`：组稿结果
- `result.diagnosis`：诊断结果
- `result.composition_selection`：组稿选择方式和理由
- `result.rewrite_selection`：改写选择方式和理由
- `result.draft.current_text`：当前终稿文本

### 确认素材

`POST /api/assistant/runs/{run_id}/confirm-materials`

请求：

```json
{
  "material_ids": ["fragment-id"]
}
```

成功后继续执行，通常会暂停到 `confirm_composition`。

### 确认组稿

`POST /api/assistant/runs/{run_id}/confirm-composition`

请求：

```json
{
  "candidate_id": "candidate-id"
}
```

成功后创建初稿、保存初稿版本、执行诊断，通常会暂停到 `confirm_rewrite`。

### 确认改写

`POST /api/assistant/runs/{run_id}/confirm-rewrite`

请求：

```json
{
  "rewrite_candidate_id": "safe"
}
```

成功后保存终稿并返回 `status = finished`。

### 查询历史

`GET /api/assistant/runs?page=1&page_size=30`

用于左侧历史列表。

### 查询详情

`GET /api/assistant/runs/{run_id}`

用于打开历史详情。

## 前端展示建议

- 主流程按钮默认使用 `auto`。
- `timeline.percent` 可用于进度条，`timeline.status` 用于步骤图标。
- 如果 `status = waiting_for_user`，读取 `metadata.pending_interrupt.type` 判断展示哪个确认面板。
- `confirm_materials` 展示 `result.materials`。
- `confirm_composition` 展示 `result.composition.candidates`。
- `confirm_rewrite` 展示 `result.diagnosis.rewrite_candidates`。
- 如果选择方式是 `rule_fallback`，把 `fallback_reason` 显示为弱提示，方便排查 LLM 选择 JSON 失败。
