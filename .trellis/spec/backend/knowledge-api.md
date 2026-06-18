# Knowledge API

## Scenario: Multi-Library Knowledge Persistence

### 1. Scope / Trigger

- Trigger: backend work that changes `/api/knowledge/*`, copy asset persistence, or knowledge database tables.
- Applies to the active system libraries: raw copies, analyses, fragments, and templates.
- Also applies to collections, which group raw copies across business contexts.

### 2. Signatures

API namespace:

```text
GET|POST   /api/knowledge/collections
GET|PATCH|DELETE /api/knowledge/collections/{id}

GET|POST   /api/knowledge/raw-copies
GET|PATCH|DELETE /api/knowledge/raw-copies/{id}

GET|POST   /api/knowledge/analyses
GET|PATCH|DELETE /api/knowledge/analyses/{id}

GET|POST   /api/knowledge/fragments
POST       /api/knowledge/fragments/extract-approved
POST       /api/knowledge/fragments/extract/{source_copy_id}
GET|PATCH|DELETE /api/knowledge/fragments/{id}

GET|POST   /api/knowledge/templates
GET|PATCH|DELETE /api/knowledge/templates/{id}
```

Database tables:

```text
knowledge_collections
copy_source_collections
knowledge_analyses
knowledge_fragments
knowledge_templates
```

### 3. Contracts

- All list endpoints accept `page` and `page_size`.
- `raw-copies` also accepts optional `collection_id`.
- `fragments` also accepts optional `source_copy_id`, `fragment_role`, `position`, and `industry`.
- Delete endpoints return `204` and use soft-delete semantics where the backing table has `is_deleted`.
- `DELETE /api/knowledge/raw-copies/{id}` deletes the underlying copy asset record, not only
  the knowledge service's process-local view. PostgreSQL-backed raw copies are soft-deleted by
  setting `copy_sources.metadata_json.deleted = true`; Redis-only records are removed from Redis.
- If a PostgreSQL-backed raw copy cannot be deleted because the database is unavailable, return
  `503`; do not return `204` from an in-memory/cache-only fallback.
- Templates accept optional source traceability:

```json
{"source": {"source_type": "raw_copy", "source_id": "<id>", "source_display": "original copy excerpt"}}
```

`source_type` is `raw_copy` or `analysis`.
- `source_display` is an optional response/display field. For raw-copy sources, backend resolves it from the source copy text so frontend does not need to display raw UUIDs.

### 4. Validation & Error Matrix

| Condition | Behavior |
| --- | --- |
| Invalid request shape | FastAPI/Pydantic `422` |
| Missing resource by ID | `404` |
| Delete existing resource | `204` |
| Deleted resource fetched again | `404` |
| Database unavailable while deleting a PostgreSQL-backed raw copy through `/api/knowledge/raw-copies/{id}` | `503` and the cached copy is not treated as durably deleted |
| Database unavailable in local dev | Service falls back to in-memory store where implemented |

### 5. Good/Base/Bad Cases

- Good: CSV import creates a raw copy and auto analysis; both appear through `/api/knowledge/raw-copies` and `/api/knowledge/analyses`.
- Good: CSV/text import derives reusable template records from the analysis when the relevant fields are present.
- Base: manually created templates persist with optional source reference.
- Base: manually created fragments persist with explicit `source_copy_id`, sequence/context fields, and optional `analysis_id`.
- Bad: do not create a fake empty analysis just to store a raw copy; raw copies may have `auto_analysis = null`.
- Bad: do not store fragment provenance only inside `metadata`; use the first-class `source_copy_id`.

### 6. Tests Required

- API test for collection CRUD and raw copy collection assignment.
- API/service regression test that raw copy deletion does not fall back to cache-only deletion for PostgreSQL-backed copy assets.
- API test for template CRUD with `source`.
- API test for fragment CRUD and filters by `source_copy_id`, `fragment_role`, `position`, or `industry`.
- API test that CSV import populates raw copy and analysis libraries.
- Full backend regression: `python -m pytest`.
- Static check: `python -m ruff check app tests alembic`.

### 7. Wrong vs Correct

#### Wrong

```python
# Creates a meaningless analysis row for a raw-only item.
create_copy_asset(payload, empty_analysis)
```

#### Correct

```python
# Raw copies can exist before analysis.
create_copy_asset(payload, None)
```

#### Wrong

```text
/api/knowledge/items?type=template
```

#### Correct

```text
/api/knowledge/templates
```

Each library has an explicit endpoint and schema so frontend and backend contracts stay stable.

#### Wrong

```json
{"metadata": {"source_copy_id": "<id>"}, "fragment_text": "..."}
```

#### Correct

```json
{"source_copy_id": "<id>", "sequence_order": 0, "fragment_text": "..."}
```

Fragment provenance and ordering are first-class fields so filtering and future retrieval stay stable.

## Fragment Library

- The fragment-level breakdown library is exposed at `/api/knowledge/fragments`.
- A fragment must keep explicit provenance through `source_copy_id`; `analysis_id` is optional because manually split fragments may not have a persisted analysis row.
- Fragment records store local sequence and context fields: `sequence_order`, `previous_fragment`, `next_fragment`, `before_context`, `after_context`, `fragment_text`, `fragment_role`, and `position`.
- Weak tags and source metadata are plain API fields for now: `industry`, `platform`, `purpose`, `audience`, `source_quality`, and `risk_level`. Do not hard-code product taxonomy in service logic until a taxonomy service exists.
- Generated fragments have `status` and `confidence`. Fragments with `confidence >= FRAGMENT_AUTO_APPROVE_MIN_CONFIDENCE` start as `approved`; lower-confidence fragments start as `pending_review`.
- Reviewing a copy asset as `approved` automatically triggers function-level fragment extraction. The extraction must be idempotent by `source_copy_id` so repeated approvals do not duplicate fragments.
- Imported copy assets that are auto-approved by LLM confidence must also automatically trigger function-level fragment extraction during import post-processing.
- Imported copy assets that remain `pending_review` must not create generated fragments until they are approved or manually extracted.
- Fragment extraction failures must not fail the copy approval request.
- Historical approved copy assets are not implicitly processed by server startup. Use `POST /api/knowledge/fragments/extract-approved?limit=50` to backfill approved copy assets that do not yet have fragments.
- Use `POST /api/knowledge/fragments/extract/{source_copy_id}` to manually retry extraction for one approved copy asset.
- Manual and batch extraction endpoints return per-copy status: `created`, `skipped`, or `failed`. LLM/configuration failures must be visible in `message` instead of being swallowed.
- List filters currently supported by backend contract: `source_copy_id`, `fragment_role`, `position`, `industry`, `status`, `platform`, `purpose`, `audience`, `risk_level`, and `q`.
- The `q` filter is keyword search against fragment text and context, not vector retrieval.
- Fragment CRUD must follow the same DB-first, in-memory fallback pattern as templates and must be covered by API tests.
- Backfill extraction must be idempotent by `source_copy_id`; if fragments already exist, return `skipped` with the existing fragment count.

## Copy Import Contract

- `POST /api/copy/import` accepts exactly one import source:
  - `csv_text`: existing CSV content path.
  - `text`: plain text path; backend treats it as one `CopyAnalysisRequest.source_text`, calls the LLM, and saves one copy asset.
- `POST /api/copy/import` also accepts optional `collection_ids`; imported copy assets must be linked to those collections when the collection IDs exist.
- Sending both `csv_text` and `text`, or neither, must fail request validation with `422`.
- Plain text import returns the same `TaskResponse` shape as CSV import. On success, `result.asset_ids` contains one asset id and `progress.percent` is `100`.
- Plain text import uses the same worker queue (`copy_import`) and same Redis fallback behavior as CSV import.
- Plain text import should first ask the LLM to extract import metadata from the pasted text:
  - `source_text`, `source_url`, `author_name`, `author_url`, `author_follower_count`, `platform`, `industry`, `audience`, `purpose`, `style`, and `metrics`.
  - If metadata extraction fails or returns invalid JSON, import must continue with the raw pasted text as `source_text`.
  - Extracted numeric strings such as `52,000`, `5.2万`, or `52k` should be normalized to non-negative integers where possible.
  - If the LLM returns blank metadata, backend should apply Chinese pattern fallback for common pasted labels such as `平台：小红书`, `作者：护肤研究员`, `粉丝：5.2万`, `正文：...`, and `指标：点赞120 评论8 收藏35 分享4`.
  - Fallback metadata must be stored on `CopyAssetSummary` first-class fields so frontend review chips can display author, platform, follower count, industry, audience, purpose, style, content type, structure type, metrics, and storage backend from `/api/copy/assets`.
- LLM prompts for copy import and analysis are part of the backend contract:
  - They must require a single valid JSON object and forbid Markdown/code fences/explanatory text.
  - Metadata extraction prompts must say to extract only information explicitly present in the pasted text and return `null` or `{}` for unknown fields.
  - Analysis prompts must define every response field, require string arrays for list fields, and require `risk_warnings[*]` to include `level: low | medium | high`, `message`, and `suggestion`.
  - Prompt contract changes should be covered by tests that capture the prompt text at the LLM boundary.
- CSV import must tolerate a UTF-8 BOM before the `source_text` header.
- LLM review is the primary first pass:
  - If `auto_analysis.confidence >= COPY_AUTO_APPROVE_MIN_CONFIDENCE`, the imported asset starts with `status = approved`.
  - Otherwise it starts with `status = pending_review` and should be shown to a human reviewer.
- `COPY_AUTO_APPROVE_MIN_CONFIDENCE` defaults to `0.85` and must stay configurable through backend settings.
- After a copy asset is imported and analyzed, backend synchronizes selected analysis fields into specialized knowledge libraries:
  - `reusable_template`, `structure`, and `suitable_scenarios` create one template item.
- Derived template items are idempotent by source asset id, derived kind, and derived content key, so repeated imports/reviews do not create duplicates for the same analysis content.
- Derived templates must keep `source.source_type = raw_copy`, `source.source_id = copy asset id`, and a frontend-friendly `source.source_display` excerpt.
- Import post-processing must also trigger fragment extraction when the imported asset status is already `approved`, using the same idempotent path as manual extraction.

## Copy Asset Delete Contract

- `DELETE /api/copy/assets/{asset_id}` deletes imported copy assets that are still pending review.
- Only `status = pending_review` assets may be deleted. Approved or rejected assets return `409`.
- Successful delete returns `204`; subsequent asset detail requests return `404` and list endpoints omit the asset.
- Database-backed delete is a soft delete using `copy_sources.metadata_json.deleted = true`.
- Redis and in-memory fallbacks remove the asset id from the active cache/order.
- A PostgreSQL-backed asset must not fall back to Redis or in-memory deletion when the database delete cannot be confirmed.
- If the database is unavailable for a PostgreSQL-backed asset delete, return `503`; do not return `204` because the copy would reappear after backend restart.

## Scenario: System Status Diagnostics

### 1. Scope / Trigger

- Trigger: backend work that changes local dependency diagnostics, startup checks, import queue health, or frontend-visible system status contracts.
- Applies to the FastAPI system endpoint and the service checks for PostgreSQL, Redis, RQ worker registration, and Milvus.

### 2. Signatures

```text
GET /api/system/status
```

Response schema:

```json
{
  "status": "ok | degraded | down",
  "services": [
    {
      "name": "postgres | redis | copy_import_worker | milvus",
      "required": true,
      "status": "ok | degraded | down",
      "latency_ms": 1,
      "endpoint": "safe display endpoint",
      "message": "human readable status"
    }
  ]
}
```

### 3. Contracts

- The endpoint returns `200` even when dependencies are unavailable; failure details live in `services[*]`.
- Required services:
  - `postgres`: checks the configured SQLAlchemy database with a short `SELECT 1`.
  - `redis`: checks `settings.redis_url` with `PING`.
  - `copy_import_worker`: checks whether an RQ worker is registered for queue `copy_import`.
- Optional services:
  - `milvus`: checks `settings.milvus_uri`; failure makes the overall status `degraded`, not `down`.
- Response endpoints must be safe to display and must not expose passwords or query strings from configured URLs.

### 4. Validation & Error Matrix

| Condition | Behavior |
| --- | --- |
| All required and optional services ok | overall `status = ok` |
| Any required service down | overall `status = down` |
| Required services ok and optional service degraded/down | overall `status = degraded` |
| PostgreSQL unavailable | `postgres.status = down`, endpoint still returns `200` |
| Redis unavailable | `redis.status = down`; worker check also reports it cannot inspect workers |
| No RQ worker listening on `copy_import` | `copy_import_worker.status = down` and message warns imports may stay queued |
| Milvus unavailable | `milvus.status = degraded`; endpoint still returns `200` |

### 5. Good/Base/Bad Cases

- Good: frontend calls `/api/system/status` on startup and shows explicit warnings before users import data.
- Base: local development with PostgreSQL and Redis running but Milvus down returns `degraded`.
- Bad: do not infer worker health only from Redis availability; Redis can accept jobs while no worker consumes `copy_import`.
- Bad: do not return raw `DATABASE_URL` if it contains a password or query string.

### 6. Tests Required

- API test that `/api/system/status` returns the expected response shape.
- Unit test that a required service failure makes overall status `down`.
- Unit test that an optional service failure makes overall status `degraded`.
- Unit test that URL redaction removes passwords and query strings.
- Unit tests that worker status is `ok` when a worker listens to `copy_import` and `down` when none do.

### 7. Wrong vs Correct

#### Wrong

```python
return {"redis": "ok"}  # Worker may still be missing.
```

#### Correct

```python
return {
    "name": "copy_import_worker",
    "required": True,
    "status": "down",
    "message": "No worker is listening on copy_import; import tasks may stay queued.",
}
```

The worker is a first-class required dependency because queued imports need a running consumer.

## Scenario: Draft Workspace

### 1. Scope / Trigger

- Trigger: backend work that changes the Phase 3 manual drafting workspace, draft persistence, draft items, or draft versions.
- Applies to `/api/drafts/*`, the `drafts`, `draft_items`, and `draft_versions` tables, and services that copy fragment data into draft items.
- Drafts are backend-owned persistence objects. Frontend renders the workspace but should use backend responses as the source of truth after each write.

### 2. Signatures

```text
GET    /api/drafts?page=1&page_size=20&status=draft
POST   /api/drafts
GET    /api/drafts/{draft_id}
PATCH  /api/drafts/{draft_id}
DELETE /api/drafts/{draft_id}

POST   /api/drafts/{draft_id}/items
PATCH  /api/drafts/{draft_id}/items/reorder
PATCH  /api/drafts/{draft_id}/items/{item_id}
DELETE /api/drafts/{draft_id}/items/{item_id}

POST   /api/drafts/{draft_id}/versions
GET    /api/drafts/{draft_id}/versions
GET    /api/drafts/{draft_id}/versions/{version_id}
```

Database tables:

```text
drafts
draft_items
draft_versions
```

### 3. Contracts

- Draft status is one of `draft`, `ready`, or `archived`.
- New drafts default to `draft` and start empty.
- `DELETE /api/drafts/{draft_id}` archives the draft by setting `status = archived`; it must not hard-delete versions.
- Draft item deletion hard-deletes the item from the current draft only.
- Saved versions are immutable snapshots of `current_text` and ordered item data.
- `current_text` is assembled from ordered `draft_items.edited_text` joined with blank lines.
- Adding an item accepts either `source_fragment_id` or `edited_text`.
- When `source_fragment_id` is provided, backend copies fragment text, role, position, and source copy id into first-class draft item fields.
- Frontend should use returned `DraftDetail` after every write to refresh local state.

### 4. Validation & Error Matrix

| Condition | Behavior |
| --- | --- |
| Invalid request shape | FastAPI/Pydantic `422` |
| Missing draft | `404` |
| Missing draft item | `404` |
| Missing source fragment | `404` |
| Delete draft | `204`, draft status becomes `archived` |
| Delete draft item | `204`, current draft no longer includes that item |
| Database unavailable in tests/local fallback | Service falls back to in-memory store where implemented |

### 5. Good/Base/Bad Cases

- Good: create an empty draft, add selected fragments one by one, edit item text, reorder items, then save a version snapshot.
- Good: a saved version remains readable after one current draft item is deleted.
- Base: manually typed draft item can be added with `edited_text` and no source fragment.
- Bad: do not expose raw UUIDs as the only user-visible content. Use `edited_text`, `original_fragment_text`, or source copy display fields where available.
- Bad: do not treat archived drafts as deleted data; they are hidden from the default list but still retrievable.

### 6. Tests Required

- API test for draft creation/list/detail/update/archive.
- API test for adding a fragment-backed item and preserving copied source fields.
- API test for item edit, reorder, and delete.
- API test for manual version save/list/detail and immutable snapshots after current item deletion.
- Static check: `python -m ruff check app tests alembic`.
- Full backend regression: `python -m pytest`.

### 7. Wrong vs Correct

#### Wrong

```text
DELETE /api/drafts/{draft_id} hard-deletes draft_versions.
```

#### Correct

```text
DELETE /api/drafts/{draft_id} sets status = archived and preserves version history.
```

#### Wrong

```json
{"metadata": {"source_fragment_id": "<id>"}, "edited_text": "..."}
```

#### Correct

```json
{"source_fragment_id": "<id>", "original_fragment_text": "...", "edited_text": "..."}
```

Draft provenance must stay in first-class fields so later AI diagnosis, recommendation, and source display can use it reliably.

## Scenario: Next-Sentence Recommendations

### 1. Scope / Trigger

- Trigger: backend work that changes Phase 4 AI next-sentence recommendation, recommendation tasks, accepted recommendation persistence, or recommendation acceptance.
- Applies to `/api/recommendations/*`, task polling through `/api/tasks/{task_id}`, draft insertion, fragment retrieval, and the `accepted_recommendations` table.
- The frontend owns display and selection; the backend owns recommendation generation and accept/insert consistency.

### 2. Signatures

```text
POST /api/recommendations/next-sentence
POST /api/recommendations/accepted
GET  /api/tasks/{task_id}
```

`POST /api/recommendations/next-sentence` returns `TaskResponse`.

`TaskResponse.result` is a `NextSentenceRecommendationResult` when finished.

Database table:

```text
accepted_recommendations
```

### 3. Contracts

- Recommendation generation is asynchronous and must expose task progress/model visibility.
- `candidate_count` defaults to 3 and is constrained to 1-5.
- Candidates may contain 1-2 sentences, but must remain short enough to insert as one draft item.
- The MVP uses PostgreSQL-backed fragment structured filters and keyword search. Do not require Milvus, vector retrieval, or reranking for Phase 4 MVP.
- The recommendation result must include reference fragment summaries so the frontend does not display raw UUIDs.
- Unaccepted candidates are not persisted as durable records.
- Accepted recommendations are persisted only when the user accepts a candidate.
- Accepting a recommendation inserts a new draft item and records the accepted recommendation in one backend operation.
- The accept endpoint validates that the task result belongs to the requested draft and that the candidate id exists.

### 4. Validation & Error Matrix

| Condition | Behavior |
| --- | --- |
| Invalid request shape | FastAPI/Pydantic `422` |
| Missing draft | `404` |
| Missing recommendation task | `404` |
| Missing candidate or candidate belongs to another draft | `404` |
| LLM failure | task status becomes `failed` with progress/error details |
| Redis unavailable in local dev | service falls back to synchronous in-memory task execution |

### 5. Good/Base/Bad Cases

- Good: frontend creates a recommendation task, polls task status, displays candidates with reasons and reference fragments, then accepts one candidate.
- Good: accepted recommendation creates a draft item with `edited_text` equal to the candidate text and metadata linking `task_id` and `candidate_id`.
- Base: when no strongly matching fragments exist, backend can still ask the LLM to use draft context and any approved fragments available.
- Bad: do not persist every generated candidate before recommendation quality is validated.
- Bad: do not make the frontend insert the draft item and then separately record acceptance; this can create broken acceptance analytics.

### 6. Tests Required

- API test that recommendation task returns structured candidates and reference fragment summaries.
- API test that accepting a recommendation inserts a draft item and persists the accepted recommendation.
- API test or service test for missing task/candidate behavior.
- Static check: `python -m ruff check app tests alembic`.
- Full backend regression: `python -m pytest`.

### 7. Wrong vs Correct

#### Wrong

```text
Frontend calls POST /api/drafts/{draft_id}/items and then separately records acceptance.
```

#### Correct

```text
Frontend calls POST /api/recommendations/accepted, and backend inserts the draft item plus acceptance record together.
```

#### Wrong

```json
{"candidate_id": "1", "reference_fragment_ids": ["uuid-only"]}
```

#### Correct

```json
{
  "candidate_id": "stable-id",
  "text": "Candidate text",
  "reference_fragment_ids": ["fragment-id"],
  "reference_fragments": [{"id": "fragment-id", "text": "fragment excerpt"}]
}
```

Recommendation responses must be directly displayable by the frontend without showing raw ids as the primary source information.

## Scenario: Auto Composition

### 1. Scope / Trigger

- Trigger: backend work that changes Phase 5 AI auto-composition, composition tasks, accepted composition persistence, or draft creation from accepted candidates.
- Applies to `/api/compositions/*`, task polling through `/api/tasks/{task_id}`, approved-fragment retrieval, draft creation, and the `accepted_compositions` table.
- The frontend owns brief input and candidate selection; backend owns candidate generation, provenance, and acceptance consistency.

### 2. Signatures

```text
POST /api/compositions/auto-draft
POST /api/compositions/accepted
GET  /api/tasks/{task_id}
```

`POST /api/compositions/auto-draft` returns `TaskResponse`.

`TaskResponse.result` is an `AutoCompositionResult` when finished.

Database table:

```text
accepted_compositions
```

### 3. Contracts

- Auto-composition generation is asynchronous and reuses the `recommendation` queue.
- The result must contain exactly three transient candidates.
- Each candidate must contain exactly five items in fixed order: `hook`, `pain_point`, `solution`, `proof`, and `cta`.
- The MVP may use only approved fragments as reference material. Do not require templates, Milvus, vector retrieval, or reranking.
- Fragment retrieval must keep structured filters from the brief: `platform`, `purpose`, and `audience`, plus keyword queries from `product` and `key_selling_points`.
- If no approved fragments match, generation must continue from the brief with `fallback_reason = "no_matching_fragments"`.
- Fallback items must use `quote_mode = "original"` and empty `reference_fragment_ids`.
- Direct copying of source fragment text is allowed only when `quote_mode = "direct"` and provenance is retained.
- Unaccepted candidates are not persisted as standalone durable rows.
- Accepting a candidate creates a real `Draft`, creates five ordered `draft_items`, and records one accepted composition in one backend operation.
- Accepted draft item metadata must include `quote_mode`, `reference_fragment_ids`, `generation_task_id`, `generation_candidate_id`, and `generation_reason`.
- When an item has reference fragments, the first valid fragment is the primary `source_fragment_id`; the draft service should populate `source_copy_id`.

### 4. Validation & Error Matrix

| Condition | Behavior |
| --- | --- |
| Invalid request shape | FastAPI/Pydantic `422` |
| Missing composition task | `404` |
| Missing candidate | `404` |
| LLM failure | task status becomes `failed` with progress/error details |
| Redis unavailable in local dev | service falls back to synchronous in-memory task execution |

### 5. Good/Base/Bad Cases

- Good: frontend creates a composition task, polls status, previews three candidates with references, accepts one, and opens the returned draft.
- Good: accepted direct quotes preserve source fragment ids and quote mode in draft item metadata.
- Base: no matching fragments still returns three candidates generated from the brief.
- Bad: do not persist every generated candidate before user acceptance.
- Bad: do not let the frontend create the draft and separately record acceptance; this can break provenance and analytics.

### 6. Tests Required

- API test that auto-composition task returns exactly three candidates and five items each.
- API test that matching approved fragments are included as references.
- API test that no matching fragments produces fallback candidates, not task failure.
- API test that accepting a candidate creates one draft with five items and provenance metadata.
- API test for missing task/candidate behavior.
- Static check: `python -m ruff check app tests alembic`.
- Full backend regression: `python -m pytest`.

## Scenario: Smart Composition Assistant Workflow

### 1. Scope / Trigger

- Trigger: backend work that changes the smart composition assistant workflow, `/api/assistant/*` endpoints, or the `smart_composition_runs` table.
- Applies across composition generation, draft creation/versioning, copy diagnosis, rewrite selection, and workflow history.
- This is a cross-layer contract: frontend displays the same `timeline`, `status`, model fields, draft ids, and selection reasons returned by the backend.

### 2. Signatures

```text
GET  /api/assistant/options
POST /api/assistant/brief-prefill
POST /api/assistant/runs
POST /api/assistant/runs/{run_id}/confirm-materials
POST /api/assistant/runs/{run_id}/confirm-composition
POST /api/assistant/runs/{run_id}/confirm-rewrite
GET  /api/assistant/runs
GET  /api/assistant/runs/{run_id}
```

Database table:

```text
smart_composition_runs
```

Important response fields:

```text
status: pending | running | waiting_for_user | finished | failed
timeline[].status: pending | running | completed | waiting_for_user | failed
draft_id
initial_version_id
final_version_id
result.composition
result.diagnosis
result.composition_selection
result.rewrite_selection
result.draft.current_text
metadata.pending_interrupt.type: confirm_materials | confirm_composition | confirm_rewrite
```

### 3. Contracts

- Smart composition workflow orchestration is implemented with LangGraph `StateGraph`.
- `run_id` is the LangGraph `thread_id`.
- MVP LangGraph checkpointing uses in-memory checkpoint storage. Backend restart can lose an unfinished guided interrupt execution state; durable checkpointing is a later task.
- `POST /api/assistant/runs` with `mode = "auto"` runs through final draft creation through the graph.
- `mode = "guided"` uses real LangGraph `interrupt()` and returns `status = "waiting_for_user"` at confirmation points.
- Guided confirmation payloads are selection-only:
  - `confirm-materials`: `{ "material_ids": ["..."] }`
  - `confirm-composition`: `{ "candidate_id": "..." }`
  - `confirm-rewrite`: `{ "rewrite_candidate_id": "..." }`
- The workflow must save both an initial draft version and a final draft version for auto mode.
- Candidate selection and rewrite selection must use rule scoring first, then an LLM judge over top candidates.
- If the LLM judge returns invalid JSON, selects an unknown id, or fails, the backend must choose the highest rule-scored option and record `method = "rule_fallback"` plus `fallback_reason`.
- Failed workflow runs must be persisted with `status = "failed"`, `error`, and the running step marked `failed`.
- Workflows must follow the same DB-first, in-memory fallback convention used by knowledge and draft services in test/local unavailable DB paths.
- `smart_composition_runs` remains the durable product history/read model; LangGraph checkpoint state is execution state only.

### 4. Validation & Error Matrix

| Condition | Behavior |
| --- | --- |
| Invalid brief fields | FastAPI/Pydantic `422` |
| Brief prefill LLM JSON invalid | `422` with detail |
| Auto workflow LLM/service failure | run persisted as `failed`; API surfaces the exception through route handling |
| Missing run id | `404` |
| Guided run created | `200` with `waiting_for_user` at material confirmation; not a failure |
| Confirm endpoint called for the wrong current checkpoint | `409` |
| Confirm endpoint receives an unknown selected id | `422` |

### 5. Good/Base/Bad Cases

- Good: auto mode returns `finished`, a real `draft_id`, `initial_version_id`, `final_version_id`, and `result.draft.current_text`.
- Good: frontend can render progress only from `timeline` without inferring hidden backend state.
- Good: guided mode resumes through `confirm-materials`, `confirm-composition`, and `confirm-rewrite` without frontend manually stitching lower-level composition/diagnostic APIs.
- Base: LLM judge fails; backend still finishes using rule fallback and explains the fallback.
- Bad: frontend calls `/compositions/accepted` and `/diagnostics/accepted-rewrite` separately for the assistant; the assistant service owns orchestration and history.
- Bad: guided mode silently proceeds past a confirmation point.
- Bad: do not put draft/version side effects before an interrupt unless the node is idempotent.

### 6. Tests Required

- API test that auto mode finishes and saves both draft versions.
- API test that guided mode returns `waiting_for_user` at material confirmation.
- API test that guided mode resumes through all confirmation endpoints and saves the final draft.
- API test that unknown guided selections are rejected.
- API test that brief prefill returns structured brief fields.
- Regression test: `python -m pytest tests`.
- Compile check: `python -m compileall app`.

### 7. Wrong vs Correct

#### Wrong

```text
POST /api/compositions/auto-draft
POST /api/compositions/accepted
POST /api/diagnostics/copy
POST /api/diagnostics/accepted-rewrite
```

The UI manually stitches the workflow together and loses workflow history.

#### Correct

```text
POST /api/assistant/runs
GET  /api/assistant/runs/{run_id}
```

The assistant service owns orchestration, version ids, selection reasons, and durable history.
