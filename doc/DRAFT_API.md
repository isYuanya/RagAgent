# Phase 3 草稿工作台后端接口

本文档给前端说明 Phase 3 新增的草稿工作台 API。后端默认地址仍是 `http://127.0.0.1:8002`，统一前缀是 `/api`。

## 1. 草稿模型

草稿用于把片段库里的素材按顺序加入一个可编辑的写作空间。后端保存有序 item，前端可以直接渲染 `current_text` 作为全文预览。

### DraftDetail

```json
{
  "id": "draft-id",
  "title": "美妆发布草稿",
  "goal": "形成一篇可审核的发布文案",
  "audience": "新手护肤用户",
  "platform": "小红书",
  "purpose": "转化",
  "status": "draft",
  "current_text": "第一段\n\n第二段",
  "item_count": 2,
  "metadata": {},
  "items": []
}
```

`status` 可选值：

- `draft`：默认状态，正常编辑中。
- `ready`：已经组装到可进入后续 AI 诊断、推荐、改写的状态。
- `archived`：归档隐藏。`DELETE /api/drafts/{draft_id}` 实际上会把草稿改成这个状态。

## 2. 草稿 CRUD

```text
GET    /api/drafts?page=1&page_size=20&status=draft
POST   /api/drafts
GET    /api/drafts/{draft_id}
PATCH  /api/drafts/{draft_id}
DELETE /api/drafts/{draft_id}
```

### 创建草稿

```json
{
  "title": "美妆发布草稿",
  "goal": "形成一篇可审核的发布文案",
  "audience": "新手护肤用户",
  "platform": "小红书",
  "purpose": "转化",
  "metadata": {}
}
```

新草稿默认是空的，响应里的 `current_text` 是空字符串，`items` 是空数组。

### 更新草稿

`PATCH /api/drafts/{draft_id}` 支持部分更新：

```json
{
  "title": "新版标题",
  "status": "ready"
}
```

### 归档草稿

`DELETE /api/drafts/{draft_id}` 返回 `204`，不会物理删除草稿和版本历史，只会把 `status` 设为 `archived`。

列表默认只查 `status=draft`。归档列表用：

```text
GET /api/drafts?status=archived
```

## 3. 草稿 item

草稿 item 是草稿里的一个有序片段。它可以来自片段库，也可以是手工输入文本。

```json
{
  "id": "item-id",
  "draft_id": "draft-id",
  "source_fragment_id": "fragment-id",
  "source_copy_id": "raw-copy-id",
  "order_index": 0,
  "original_fragment_text": "原片段文本",
  "edited_text": "用户编辑后的文本",
  "role": "hook",
  "position": "opening",
  "metadata": {}
}
```

`original_fragment_text` 保存加入草稿时的片段原文。之后用户编辑 `edited_text` 不会改变它。

### 添加 item

```text
POST /api/drafts/{draft_id}/items
```

从片段库添加：

```json
{
  "source_fragment_id": "fragment-id"
}
```

后端会自动从 `/api/knowledge/fragments/{fragment_id}` 复制：

- `fragment_text` -> `original_fragment_text`
- `fragment_text` -> `edited_text`
- `fragment_role` -> `role`
- `position` -> `position`
- `source_copy_id` -> `source_copy_id`

也可以添加手工文本：

```json
{
  "edited_text": "手工写入的一段文案",
  "role": "transition",
  "position": "middle"
}
```

`source_fragment_id` 和 `edited_text` 至少传一个，否则返回 `422`。

### 编辑 item

```text
PATCH /api/drafts/{draft_id}/items/{item_id}
```

```json
{
  "edited_text": "修改后的句子",
  "role": "proof",
  "position": "body",
  "metadata": {}
}
```

返回完整 `DraftDetail`，前端可直接用新的 `current_text` 刷新预览。

### 重排 item

```text
PATCH /api/drafts/{draft_id}/items/reorder
```

```json
{
  "items": [
    {"item_id": "item-a", "order_index": 1},
    {"item_id": "item-b", "order_index": 0}
  ]
}
```

返回完整 `DraftDetail`。

### 删除 item

```text
DELETE /api/drafts/{draft_id}/items/{item_id}
```

返回 `204`。item 会从当前草稿中物理删除，但已经保存的版本快照不会被修改。

## 4. 版本快照

版本是人工保存的快照，不会自动保存。

```text
POST /api/drafts/{draft_id}/versions
GET  /api/drafts/{draft_id}/versions
GET  /api/drafts/{draft_id}/versions/{version_id}
```

### 保存版本

```json
{
  "label": "第一版可审核稿",
  "metadata": {}
}
```

响应：

```json
{
  "id": "version-id",
  "draft_id": "draft-id",
  "version_number": 1,
  "label": "第一版可审核稿",
  "current_text": "快照全文",
  "item_count": 2,
  "metadata": {},
  "items": []
}
```

版本保存的是当时的 `current_text` 和 ordered item snapshot。之后删除或修改当前草稿 item，不会影响历史版本。

## 5. 错误规则

| 场景 | 状态码 |
| --- | --- |
| 请求字段不合法 | `422` |
| 草稿不存在 | `404` |
| item 不存在 | `404` |
| source fragment 不存在 | `404` |
| 删除成功 | `204` |

## 6. 前端建议

- 草稿列表默认请求 `/api/drafts?status=draft`。
- 全文预览优先使用响应里的 `current_text`，不要自己拼接后再作为保存依据。
- 拖拽排序后调用 reorder 接口，再用响应覆盖本地 item 列表。
- 保存版本按钮调用 `POST /api/drafts/{draft_id}/versions`。
- 删除草稿在界面上叫“归档”更准确，因为后端不会硬删除。
