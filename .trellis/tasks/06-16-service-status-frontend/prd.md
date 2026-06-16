# Service Status Frontend

## Goal

Add a frontend service monitoring experience for the new `GET /api/system/status` backend endpoint, so users can see whether PostgreSQL, Redis, copy import worker, and Milvus are healthy before starting import or review workflows.

## What I Already Know

- Backend exposes `GET /api/system/status`.
- The endpoint returns `200` even when dependencies are unavailable; failures are represented in the response body.
- Overall status values are `ok`, `degraded`, and `down`.
- Required services are `postgres`, `redis`, and `copy_import_worker`.
- Optional service is `milvus`.
- Import depends on `redis` and `copy_import_worker`.
- Data persistence depends on `postgres`.
- `endpoint` values are password-redacted and safe to display to developers.
- Current frontend uses React + Vite + TypeScript, a state-driven `AppView`, `Sidebar`, `lib/api.ts`, and `lib/types.ts`.

## Requirements

- Add typed frontend contracts for system status responses.
- Add a `fetchSystemStatus()` API function in the frontend API layer.
- Add a `服务状态` top-level view in the sidebar.
- Add a service status page with:
  - overall status
  - last checked time
  - manual refresh
  - auto-refresh toggle
  - per-service rows showing name, required/optional, status, latency, endpoint, and message
- Add a compact global status indicator in the workbench and knowledge views, clickable to open the service status page.
- Show actionable dependency warnings in the import area:
  - if `copy_import_worker.status === "down"`, warn that import tasks may remain queued, but do not disable import buttons.
  - if `redis.status === "down"`, disable import buttons and explain that the queue is unavailable.
  - if `postgres.status === "down"`, warn that data may not persist correctly.
- Keep UI copy in Chinese and source files UTF-8.
- Follow existing frontend patterns: state-up / props-down, typed API layer, semantic Tailwind classes, lucide icons.

## Acceptance Criteria

- [ ] Sidebar has a `服务状态` entry.
- [ ] Frontend calls `GET /api/system/status` through `lib/api.ts`, not directly in components.
- [ ] Service status page renders all services with required/optional, status, latency, endpoint, and message.
- [ ] Manual refresh updates the status and last checked time.
- [ ] Auto-refresh can be toggled on and off.
- [ ] Workbench top area shows a compact overall status indicator.
- [ ] Redis down disables CSV and text import buttons with a visible explanation.
- [ ] Worker down shows a warning but still allows import.
- [ ] PostgreSQL down shows a data persistence warning.
- [ ] `npm run build` passes.
- [ ] Browser smoke test shows page loads without console errors.

## Definition of Done

- Frontend build passes.
- Browser smoke test covers `ok`, `degraded`, and `down` status rendering with mocked API responses.
- No unrelated dirty files are committed.
- Existing service status backend changes are not modified by this frontend task.

## Technical Approach

- Extend `AppView` to include `system`.
- Add `SystemStatusView` under `frontend/src/features/system/`.
- Add a compact `SystemStatusBadge` component under the same feature folder.
- Let `App.tsx` own status fetching and pass `systemStatus`, loading state, refresh handler, and navigation callback to consumers.
- Keep service-specific derivation in small frontend helpers, based on service `name` fields.
- Use existing `Button`, `Badge`, `Card`, and `cn` patterns.

## Decision (ADR-lite)

**Context**: Service health affects multiple workflows, especially import. A dedicated page is useful for diagnosis, but users need early warning before starting work.

**Decision**: Implement both a global compact status indicator and a dedicated service status page. Redis down disables import; worker down warns but does not block; PostgreSQL down warns about persistence.

**Consequences**: Users get immediate visibility without leaving the workflow, and developers still have a detailed diagnostics page. The UI depends on stable service `name` values from the backend.

## Out of Scope

- Starting or stopping services from the UI.
- Historical uptime charts.
- Notifications outside the current page.
- Backend schema changes.
- Authentication or role-based visibility.

## Technical Notes

- Docs: `doc/SYSTEM_STATUS_API.md`
- Backend schema: `app/schemas/system.py`
- Backend route: `app/api/routes/system.py`
- Current frontend entry: `frontend/src/App.tsx`
- Current navigation: `frontend/src/features/Sidebar.tsx`
- API layer: `frontend/src/lib/api.ts`
- Types: `frontend/src/lib/types.ts`
