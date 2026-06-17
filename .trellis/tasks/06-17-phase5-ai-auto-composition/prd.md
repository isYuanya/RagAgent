# Phase 5 AI 自动组稿

## Goal

Build Phase 5 end-to-end AI auto-composition. A user starts from the draft workspace, submits a structured creative brief, receives three complete candidate drafts, accepts one, and continues editing it as a normal `Draft`.

This phase should extend the existing Phase 3 draft workspace and Phase 4 async recommendation/task pattern instead of introducing an isolated generation flow.

## Requirements

### Product Flow

- Add an AI auto-composition entry in the draft workspace.
- User fills a structured brief:
  - `product`
  - `audience`
  - `platform`
  - `purpose`
  - `style`
  - `key_selling_points`
  - `constraints`
  - `target_length`
- Backend creates an async composition task.
- Frontend polls `GET /api/tasks/{task_id}` for progress.
- Task result returns three candidate drafts.
- User previews the candidates and accepts one.
- Backend creates a formal `Draft` only after acceptance.
- Frontend opens the accepted draft in the draft workspace.

### Backend API

- Add `POST /api/compositions/auto-draft`.
  - Returns the standard `TaskResponse`.
  - Uses the existing `recommendation` queue.
  - Uses task progress phases:
    - `queued`
    - `retrieving_fragments`
    - `generating_compositions`
    - `finished`
    - `failed`
- Add `POST /api/compositions/accepted`.
  - Accepts `task_id` and `candidate_id`.
  - Creates a `Draft`.
  - Creates five ordered `draft_items`.
  - Records the accepted composition.
  - Returns `DraftDetail` plus accepted composition metadata.

### Candidate Draft Contract

- The task result contains exactly three candidates.
- Each candidate contains five structured items:
  1. `hook`
  2. `pain_point`
  3. `solution`
  4. `proof`
  5. `cta`
- Suggested item positions:
  - `hook`: `opening`
  - `pain_point`: `body`
  - `solution`: `body`
  - `proof`: `body`
  - `cta`: `ending`
- Each item contains:
  - `role`
  - `position`
  - `text`
  - `quote_mode`: `direct | adapted | original`
  - `reference_fragment_ids`
  - `source_copy_id` when available
  - `reason`

### Reference Material

- Use only approved fragment records as reference material for MVP.
- Retrieve fragments with structured filters from the brief where possible:
  - `platform`
  - `purpose`
  - `audience`
  - relevant role/position
  - keyword query derived from `product` and `key_selling_points`
- Do not use template library, Milvus, vector retrieval, or reranker in MVP.
- If no matching fragments exist, continue generation from the brief alone.
- Fallback candidate items must have:
  - `reference_fragment_ids: []`
  - `quote_mode: original`
- Task result should include `fallback_reason: "no_matching_fragments"` when fallback is used.

### Quoting And Provenance

- Generated drafts may directly quote source fragments when appropriate.
- Direct or adapted use must be explicitly traceable.
- On accepted draft items:
  - Set `source_fragment_id` when one source fragment is the primary source.
  - Set `source_copy_id` when source information is available.
  - Store provenance in `metadata`:
    - `quote_mode`
    - `reference_fragment_ids`
    - `generation_task_id`
    - `generation_candidate_id`
    - `generation_reason`

### Accepted Composition Persistence

- Add accepted composition persistence aligned with Phase 4 `accepted_recommendations`.
- Record:
  - `id`
  - `task_id`
  - `candidate_id`
  - `draft_id`
  - `brief_json`
  - `candidate_title`
  - `model`
  - `reference_fragment_ids`
  - `metadata_json`
  - `created_at`
- Unaccepted candidates are not persisted in a dedicated table; they only live in task result data.

### Frontend

- Add the entry in `DraftWorkbenchView`.
- Provide a structured brief form.
- Create the auto-composition task.
- Poll task status.
- Show progress phase/model/current message.
- Render three candidate previews.
- Allow accepting one candidate.
- After acceptance, open/select the returned draft.

## Acceptance Criteria

- [x] `POST /api/compositions/auto-draft` returns a `TaskResponse`.
- [x] Composition task returns exactly three candidates.
- [x] Each candidate has five ordered items with fixed roles.
- [x] Matching approved fragments are included as references when available.
- [x] No matching fragments triggers fallback generation, not task failure.
- [x] `POST /api/compositions/accepted` creates a `Draft` and five draft items.
- [x] Accepted draft item metadata preserves quote/provenance fields.
- [x] Accepted composition is persisted.
- [x] Unaccepted candidates are not persisted as standalone records.
- [x] Frontend can create the task, poll, preview candidates, accept one, and open the draft.
- [x] Backend tests cover task result, fallback behavior, acceptance, and persistence.
- [x] Frontend build passes.

## Definition Of Done

- Backend route, schema, service, queue job, model/migration, and tests are implemented.
- Frontend API types/functions and draft workspace UI are implemented.
- `doc/` integration documentation is updated.
- `.trellis/spec/` backend/frontend contracts are updated if implementation establishes new conventions.
- `python -m ruff check app tests alembic` passes.
- `python -m pytest` or targeted backend regression passes.
- `npm run build` passes for frontend changes.

## Technical Approach

- Reuse the standard task contract and existing task polling UI pattern.
- Reuse the `recommendation` queue for composition tasks.
- Add a new API namespace: `/api/compositions`.
- Add `app/schemas/composition.py`, `app/services/compositions.py`, `app/services/composition_jobs.py`, and `app/api/routes/compositions.py`.
- Add `AcceptedComposition` model and Alembic migration.
- Reuse draft service functions to create the accepted `Draft` and items.
- Reuse fragment list/filter behavior from the knowledge service.
- Add frontend API contracts in `frontend/src/lib/types.ts` and `frontend/src/lib/api.ts`.
- Add the UI in the draft feature area rather than adding a top-level navigation page.

## Decision

**Context**: Phase 5 needs to turn generated content into editable, traceable writing assets rather than isolated text output.

**Decision**: Generate three transient candidate drafts, accept one into the existing Draft model, and preserve quote provenance on each accepted draft item.

**Consequences**:

- This keeps the draft workspace as the single editing surface.
- The system can support direct source quotation while preserving traceability.
- The MVP avoids candidate persistence complexity until analytics requires it.
- Frontend scope is larger because users need task creation, polling, preview, and acceptance in one flow.

## Out Of Scope

- Phase 6 diagnosis, rewrite, scoring, or compliance review.
- Automatic full-article multi-round optimization.
- Template library participation.
- Milvus/vector retrieval/reranking.
- Persisting unaccepted candidates as first-class records.
- Purpose-specific dynamic structure templates.

## Technical Notes

- Existing Phase 3 draft APIs are documented in `doc/DRAFT_API.md`.
- Existing Phase 4 async recommendation APIs are documented in `doc/RECOMMENDATION_API.md`.
- Phase 5 should follow Phase 4's pattern where unaccepted generated candidates are transient task results and acceptance performs the durable write.
- Existing frontend draft workspace is `frontend/src/features/drafts/DraftWorkbenchView.tsx`.
- Existing task polling type/function lives in `frontend/src/lib/api.ts`.
