# Phase 5 AI 自动组稿 API

Phase 5 adds an async auto-composition flow under `/api/compositions`. It reuses the standard `TaskResponse` polling contract and the existing draft persistence model.

## Endpoints

```text
POST /api/compositions/auto-draft
POST /api/compositions/accepted
GET  /api/tasks/{task_id}
```

`POST /api/compositions/auto-draft` creates a task and returns `TaskResponse`.

Request:

```json
{
  "brief": {
    "product": "routine",
    "audience": "new users",
    "platform": "xhs",
    "purpose": "conversion",
    "style": "practical",
    "key_selling_points": ["order"],
    "constraints": "avoid medical claims",
    "target_length": "short post"
  }
}
```

Finished task `result` is `AutoCompositionResult`:

```json
{
  "brief": {},
  "model": "gpt-4.1-mini",
  "fallback_reason": null,
  "candidates": [
    {
      "candidate_id": "id",
      "title": "candidate title",
      "strategy": "composition strategy",
      "items": [
        {
          "role": "hook",
          "position": "opening",
          "text": "sentence",
          "quote_mode": "direct",
          "reference_fragment_ids": ["fragment-id"],
          "source_copy_id": "copy-id",
          "reason": "why this item was generated"
        }
      ],
      "reference_fragment_ids": ["fragment-id"]
    }
  ],
  "reference_fragments": []
}
```

Rules:

- The task result always contains exactly 3 candidates.
- Each candidate always contains exactly 5 items in fixed roles: `hook`, `pain_point`, `solution`, `proof`, `cta`.
- Reference material comes only from approved fragments filtered by `platform`, `purpose`, `audience`, and brief keywords.
- If no matching approved fragments exist, `fallback_reason` is `no_matching_fragments`; all item `quote_mode` values are `original` and references are empty.
- Unaccepted candidates are transient task result data and are not persisted as standalone rows.

## Accepting A Candidate

`POST /api/compositions/accepted`

```json
{
  "task_id": "task-id",
  "candidate_id": "candidate-id",
  "metadata": {}
}
```

Response:

```json
{
  "accepted": {
    "id": "accepted-id",
    "task_id": "task-id",
    "candidate_id": "candidate-id",
    "draft_id": "draft-id",
    "brief": {},
    "candidate_title": "candidate title",
    "model": "gpt-4.1-mini",
    "reference_fragment_ids": ["fragment-id"],
    "metadata": {}
  },
  "draft": {}
}
```

Acceptance creates one real `Draft` and five ordered `draft_items`. Each accepted item stores provenance in metadata:

- `quote_mode`
- `reference_fragment_ids`
- `generation_task_id`
- `generation_candidate_id`
- `generation_reason`

When an item has a primary source fragment, backend also sets first-class `source_fragment_id` and lets the draft service populate `source_copy_id`.
