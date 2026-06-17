# Phase 6 Diagnostic API

This document is the frontend integration contract for Phase 6 copy diagnosis, rewrite, and compliance review.

## Overview

Diagnosis is an async backend task. The frontend submits either pasted text or a draft id, then polls the shared task endpoint until the task is finished.

The backend returns diagnosis results through `TaskResponse.result`. Diagnosis results are not persisted as standalone history in Phase 6. When the user accepts a rewrite for a draft, the backend applies the rewrite to the draft and saves a draft version snapshot.

## Start Diagnosis

```text
POST /api/diagnostics/copy
```

### Request

At least one of `text` or `draft_id` is required.

```json
{
  "text": "用户粘贴的文案，可选",
  "draft_id": "已有草稿 ID，可选",
  "platform": "xhs",
  "audience": "new users",
  "purpose": "conversion",
  "style": "practical",
  "industry": "beauty",
  "constraints": ["不要使用绝对承诺"],
  "rewrite_modes": ["conservative", "conversion", "compliance_safe"],
  "metadata": {}
}
```

If both `text` and `draft_id` are provided, the backend diagnoses `text` first.

### Response

Returns the standard task shape:

```json
{
  "task_id": "uuid",
  "status": "queued",
  "result": null,
  "error": null,
  "progress": {
    "phase": "queued",
    "model": "configured-model",
    "percent": 0,
    "current_message": "Copy diagnosis task created."
  }
}
```

## Poll Task

```text
GET /api/tasks/{task_id}
```

Frontend should show:

- `progress.phase`
- `progress.percent`
- `progress.model`
- `progress.current_message`
- `error` when `status = failed`

Typical phases:

- `queued`
- `preparing_context`
- `calling_llm`
- `finished`
- `failed`

## Finished Result

When `status = finished`, `result` is a `CopyDiagnosisResult`.

```json
{
  "source": {
    "source_type": "draft",
    "text": "被诊断的正文",
    "draft_id": "draft-id",
    "platform": "xhs",
    "audience": "new users",
    "purpose": "conversion",
    "style": null,
    "industry": null
  },
  "summary": "整体表达清楚，但开头吸引力偏弱。",
  "overall_level": "fair",
  "dimensions": [
    {
      "dimension": "opening_attractiveness",
      "level": "weak",
      "reason": "开头没有快速指出用户正在经历的问题。",
      "suggestion": "先用更具体的场景切入。"
    }
  ],
  "sentence_issues": [
    {
      "text": "这个方法绝对有效。",
      "dimension": "compliance_risk",
      "level": "high_risk",
      "reason": "绝对化表达容易带来合规风险。",
      "suggestion": "改成更审慎、可验证的表达。",
      "replacement": "这个方法适合先作为检查思路。"
    }
  ],
  "rewrite_candidates": [
    {
      "candidate_id": "safe",
      "mode": "compliance_safe",
      "title": "合规安全版",
      "text": "改写后的完整文案",
      "reason": "弱化绝对承诺，并保留原始意图。"
    }
  ],
  "risk_warnings": [
    {
      "level": "high",
      "message": "包含绝对化表达。",
      "suggestion": "替换为审慎表达。"
    }
  ],
  "model": "model-used-by-backend"
}
```

Level values are stable strings, not numeric scores:

- `weak`
- `fair`
- `strong`
- `risk`
- `high_risk`

## Accept Rewrite

```text
POST /api/diagnostics/accepted-rewrite
```

Use this only when the diagnosis result came from a draft.

### Request

```json
{
  "draft_id": "draft-id",
  "task_id": "diagnosis-task-id",
  "candidate_id": "rewrite-candidate-id",
  "label": "AI 诊断改写",
  "metadata": {}
}
```

### Response

```json
{
  "accepted": {
    "draft_id": "draft-id",
    "task_id": "diagnosis-task-id",
    "candidate_id": "rewrite-candidate-id",
    "rewrite_text": "被接受的完整改写文本",
    "model": "model-used-by-backend",
    "metadata": {}
  },
  "draft": {
    "id": "draft-id",
    "current_text": "被接受的完整改写文本",
    "item_count": 1,
    "items": []
  },
  "version": {
    "id": "version-id",
    "draft_id": "draft-id",
    "version_number": 2,
    "label": "AI 诊断改写",
    "current_text": "被接受的完整改写文本",
    "item_count": 1,
    "items": []
  }
}
```

After a successful accept response, frontend should replace local draft state with `draft`. The backend has already saved a version snapshot in `version`.

## Error Behavior

- Invalid request shape returns `422`.
- Missing draft returns `404`.
- Missing diagnosis task returns `404`.
- Missing candidate returns `404`.
- LLM failures mark the task as `failed`; frontend should read `error` and `progress.current_message`.
