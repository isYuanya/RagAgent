# Service Status Monitor

## Goal

Provide a backend service status monitor so the user can quickly see whether required local dependencies, especially Redis and PostgreSQL, are running before using import and persistence features.

## What I Already Know

- The backend uses FastAPI with routes under `app/api/routes`.
- Existing `/api/health` only reports the API process status and does not check dependencies.
- PostgreSQL is configured through `settings.database_url` and SQLAlchemy `engine` in `app/db/session.py`.
- Redis is configured through `settings.redis_url` and used by import queue/task cache code.
- Milvus is configured through `settings.milvus_uri`, but vector retrieval appears less critical than PostgreSQL and Redis for the current import/persistence workflow.
- Copy import jobs are queued to Redis queue `copy_import`; if Redis is running but the worker is not running, imports can remain queued and never finish.
- Frontend work is owned by the user, so backend must expose a clear API contract and update docs.

## Assumptions

- MVP should be backend-only.
- PostgreSQL and Redis should be classified as required services.
- The `copy_import` worker should be monitored because it is required for queued import tasks to complete.
- Milvus should be included in the first version as optional. If it fails, the system should report degraded but not down.
- The endpoint should never crash when a dependency is down; it should return structured status for each service.

## Requirements

- Add a backend endpoint for service/dependency status, proposed path: `GET /api/system/status`.
- Check PostgreSQL by opening a short-timeout DB connection and running `SELECT 1`.
- Check Redis by connecting to `settings.redis_url` and running `PING`.
- Check copy import worker health through Redis/RQ worker registration or queue metadata for queue `copy_import`.
- Include Milvus as an optional dependency check.
- Return a stable JSON shape with:
  - overall status: `ok`, `degraded`, or `down`.
  - one item per dependency with name, required flag, status, latency, and message.
  - configured URL/host summary that is safe to display and does not leak passwords.
- Keep `/api/health` lightweight and unchanged unless implementation finds a strong reason to include the new summary there.
- Add backend tests for healthy and failed dependency checks using monkeypatches/mocks.
- Update backend-facing docs so frontend knows which endpoint and fields to use.

## Acceptance Criteria

- [ ] `GET /api/system/status` returns `200` even when PostgreSQL or Redis is down.
- [ ] If PostgreSQL and Redis checks pass, overall status is `ok`.
- [ ] If PostgreSQL, Redis, or required worker checks fail, overall status is `down`.
- [ ] If only optional services fail, overall status is `degraded`.
- [ ] If Milvus fails but required services pass, overall status is `degraded`.
- [ ] If the copy import worker is not running while Redis is reachable, the response clearly says import tasks may stay queued.
- [ ] Response does not expose passwords from connection URLs.
- [ ] Tests cover successful checks and dependency failure checks.
- [ ] Lint and tests pass.

## Definition of Done

- Backend API and schemas implemented.
- Tests added or updated.
- Frontend integration notes documented.
- Trellis spec updated if a new backend monitoring contract is introduced.
- Code committed separately from Trellis archive/journal bookkeeping.

## Out of Scope

- Frontend page implementation.
- Auto-starting Redis/PostgreSQL.
- Long-running background monitoring, alerts, metrics dashboards, or Prometheus integration.
- Docker orchestration changes.

## Technical Notes

- Likely files:
  - `app/api/router.py`
  - `app/api/routes/system.py` or similar
  - `app/services/system_status.py`
  - `app/schemas/system.py`
  - `tests/test_api.py` or a new `tests/test_system_status.py`
  - frontend contract documentation under `doc/`
- Use short connection timeouts so the status endpoint does not hang when a service is off.
- Avoid secrets in response by redacting usernames/passwords from service URLs.

## Open Questions

- Resolved: Milvus is included as optional.
- Resolved: worker absence makes the whole status `down` because async import is a core workflow and missing worker caused prior user-facing failures.

## Decision (ADR-lite)

Context: The user has repeatedly hit local development failures where Redis, PostgreSQL, or the import worker was not running, causing import and persistence workflows to appear broken.

Decision: Add a backend-only dependency status endpoint. PostgreSQL, Redis, and `copy_import_worker` are required. Milvus is reported as optional. The endpoint always returns a structured response instead of failing when dependencies are unavailable.

Consequences: Frontend can show actionable startup diagnostics without guessing from failed feature calls. The endpoint is intentionally local-development oriented and does not start services automatically.
