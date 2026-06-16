# Knowledge API

## Scenario: Multi-Library Knowledge Persistence

### 1. Scope / Trigger

- Trigger: backend work that changes `/api/knowledge/*`, copy asset persistence, or knowledge database tables.
- Applies to the seven system libraries: raw copies, analyses, fragments, templates, tags, cases, and blocks.
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
GET|PATCH|DELETE /api/knowledge/fragments/{id}

GET|POST   /api/knowledge/templates
GET|PATCH|DELETE /api/knowledge/templates/{id}

GET|POST   /api/knowledge/tags
GET|PATCH|DELETE /api/knowledge/tags/{id}

GET|POST   /api/knowledge/cases
GET|PATCH|DELETE /api/knowledge/cases/{id}

GET|POST   /api/knowledge/blocks
GET|PATCH|DELETE /api/knowledge/blocks/{id}
```

Database tables:

```text
knowledge_collections
copy_source_collections
knowledge_analyses
knowledge_fragments
knowledge_templates
knowledge_tags
knowledge_cases
knowledge_blocks
```

### 3. Contracts

- All list endpoints accept `page` and `page_size`.
- `raw-copies` also accepts optional `collection_id`.
- `fragments` also accepts optional `source_copy_id`, `fragment_role`, `position`, and `industry`.
- Delete endpoints return `204` and use soft-delete semantics where the backing table has `is_deleted`.
- Templates, tags, cases, and blocks accept optional source traceability:

```json
{"source": {"source_type": "raw_copy", "source_id": "<id>"}}
```

`source_type` is `raw_copy` or `analysis`.

### 4. Validation & Error Matrix

| Condition | Behavior |
| --- | --- |
| Invalid request shape | FastAPI/Pydantic `422` |
| Missing resource by ID | `404` |
| Delete existing resource | `204` |
| Deleted resource fetched again | `404` |
| Database unavailable in local dev | Service falls back to in-memory store where implemented |

### 5. Good/Base/Bad Cases

- Good: CSV import creates a raw copy and auto analysis; both appear through `/api/knowledge/raw-copies` and `/api/knowledge/analyses`.
- Base: manually created templates/tags/cases/blocks persist with optional source reference.
- Base: manually created fragments persist with explicit `source_copy_id`, sequence/context fields, and optional `analysis_id`.
- Bad: do not create a fake empty analysis just to store a raw copy; raw copies may have `auto_analysis = null`.
- Bad: do not store fragment provenance only inside `metadata`; use the first-class `source_copy_id`.

### 6. Tests Required

- API test for collection CRUD and raw copy collection assignment.
- API test for template/tag/case/block CRUD with `source`.
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
- Weak tags are plain API fields for now: `industry`, `source_quality`, and `risk_level`. Do not hard-code product taxonomy in service logic until a taxonomy service exists.
- List filters currently supported by backend contract: `source_copy_id`, `fragment_role`, `position`, and `industry`.
- Fragment CRUD must follow the same DB-first, in-memory fallback pattern as templates/tags/cases/blocks and must be covered by API tests.

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
- CSV import must tolerate a UTF-8 BOM before the `source_text` header.
- LLM review is the primary first pass:
  - If `auto_analysis.confidence >= COPY_AUTO_APPROVE_MIN_CONFIDENCE`, the imported asset starts with `status = approved`.
  - Otherwise it starts with `status = pending_review` and should be shown to a human reviewer.
- `COPY_AUTO_APPROVE_MIN_CONFIDENCE` defaults to `0.85` and must stay configurable through backend settings.

## Copy Asset Delete Contract

- `DELETE /api/copy/assets/{asset_id}` deletes imported copy assets that are still pending review.
- Only `status = pending_review` assets may be deleted. Approved or rejected assets return `409`.
- Successful delete returns `204`; subsequent asset detail requests return `404` and list endpoints omit the asset.
- Database-backed delete is a soft delete using `copy_sources.metadata_json.deleted = true`.
- Redis and in-memory fallbacks remove the asset id from the active cache/order.

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
