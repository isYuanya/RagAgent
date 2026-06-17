# brainstorm: phase 3 planning

## Goal

Define Phase 3 for RagAgent: a manual drafting workspace where users can select reusable fragments from the material library, compose a new draft, edit and reorder content, and save draft versions without introducing AI next-sentence recommendation or automatic drafting yet.

## What I Already Know

- Phase 1 established copy import, LLM analysis, review, persistence, collections, and local service diagnostics.
- Phase 2 established fragment-level material extraction, fragment persistence, structured filtering, keyword search, knowledge library synchronization, and auto extraction for approved imports.
- `doc/PRD.md` defines Phase 3 as a manual drafting workspace.
- Phase 3 includes material list, draft editing area, adding fragments, deleting fragments, drag ordering, manual editing, draft save, and version save.
- Phase 3 excludes automatic drafting, AI next-sentence recommendation, real-time vector database writes, and multi-user collaboration.
- The user currently owns frontend work; backend should provide stable APIs and docs for frontend integration.

## Assumptions

- Phase 3 should be backend-first in this session, with enough frontend-facing documentation for the user to build the UI.
- Drafts should persist in PostgreSQL, with in-memory fallback in tests/local degraded mode following current knowledge service patterns.
- Draft composition should reference source fragments but also allow edited text so users can transform material instead of copying it verbatim.
- Draft versioning should be explicit and simple for the MVP.

## Open Questions

- Confirm Phase 3 MVP scope before implementation.

## Requirements (Evolving)

- Create and persist drafts.
- Add selected fragment materials into a draft.
- Preserve source fragment traceability.
- Allow manual edits after adding fragments.
- Allow item ordering inside a draft.
- Save draft versions.
- Keep AI recommendation and automatic drafting out of Phase 3 MVP.
- Use a mixed draft model: backend stores ordered editable blocks with source references, and frontend can render a full-text preview by joining block text.
- Each draft item should keep `edited_text` as the user-controlled content and preserve `original_fragment_text` for traceability.
- Draft detail responses should include `current_text`, assembled from ordered `edited_text` blocks, so frontend can display the full draft without reconstructing it independently.
- Draft versioning is manual only in the MVP. Updating a draft or its blocks does not automatically create a version; the frontend calls a dedicated save-version endpoint when the user chooses to preserve a snapshot.
- Draft creation starts with an empty draft. Users add fragments after the draft exists.
- Creating a draft directly from multiple selected fragments is out of scope for Phase 3 MVP.
- Draft statuses are `draft`, `ready`, and `archived`.
- `draft` is the default status.
- `ready` means the user considers the draft assembled enough for later AI diagnosis, recommendation, or rewrite flows.
- `archived` hides the draft from the normal active list without deleting its versions.
- Draft item editing supports `edited_text`, `role`, and `position`.
- Draft item notes are out of scope for Phase 3 MVP.
- Manual draft versions snapshot `current_text` and the ordered draft items at the time of saving.
- Draft metadata is not fully snapshotted in Phase 3 MVP versions.
- Draft deletion is archive semantics: set status to `archived`.
- Draft item deletion is hard delete from the current draft.
- Saved version item snapshots are immutable and not affected by later draft item deletion.

## Acceptance Criteria (Evolving)

- [x] Backend exposes draft CRUD APIs.
- [x] Backend exposes APIs to add, edit, reorder, and remove draft items.
- [x] Drafts can be created without initial fragments.
- [x] Draft list can filter by `status`.
- [x] Draft status can be updated to `draft`, `ready`, or `archived`.
- [x] Draft item updates can change `edited_text`, `role`, and `position`.
- [x] Draft items preserve source fragment ID and source copy provenance where available.
- [x] Drafts can save versions and list/retrieve version history.
- [x] Draft updates do not create versions unless the save-version endpoint is called.
- [x] Version detail can return the saved `current_text` and ordered item snapshot.
- [x] Draft detail returns both ordered blocks and assembled `current_text`.
- [x] Deleting a draft sets status to `archived`.
- [x] Deleting a draft item removes it from current draft detail and recomputes `current_text`.
- [x] Existing version snapshots remain readable after draft item deletion.
- [x] API docs explain request/response shapes for frontend integration.
- [x] Tests cover create/edit/reorder/version flows.

## Definition of Done

- Tests added/updated for draft workspace backend flows.
- Static checks pass.
- Frontend integration docs updated.
- Trellis backend spec updated.
- Changes committed separately from unrelated dirty worktree files.

## Out of Scope

- AI next-sentence recommendation.
- Fully automatic drafting.
- Multi-user collaboration and permissions.
- Real-time embedding/vector writes from draft edits.
- Publishing workflow.
- One-request draft creation from selected fragments.
- Draft item notes.
- Hard-deleting drafts and their version history.

## Technical Notes

- Current PRD references:
  - `doc/PRD.md` section `7.3 Phase 3: 手动组稿工作台`.
  - `doc/PRD.md` section `8.8 草稿与组稿`.
  - `doc/PRD.md` data object `9.8 Draft`.
- Likely backend areas:
  - `app/models/*` for draft persistence models.
  - `app/schemas/*` for frontend-facing contracts.
  - `app/services/*` for draft business logic.
  - `app/api/routes/*` for draft endpoints.
  - `alembic/versions/*` for database migration.
  - `doc/FRONTEND_INTEGRATION.md` and `doc/SCHEMAS.md` for frontend handoff.

## Decision (ADR-lite)

### Draft Composition Shape

**Context**: Phase 3 needs source traceability for fragments while still giving the user an ergonomic full-draft editing experience.

**Decision**: Use a mixed model. The backend stores an ordered list of editable draft blocks/items. Each block may reference a source fragment and source copy, stores the original fragment text, and stores the user-edited text. Draft detail responses also include an assembled `current_text` generated from ordered block text.

**Consequences**: Frontend can render both a block editor and a full-text preview. Backend keeps provenance and ordering stable. The MVP does not need to support arbitrary rich-text spans inside one large text field.

### Version Save Mode

**Context**: Drafts need version history, but Phase 3 should avoid noisy automatic snapshots and keep user intent clear.

**Decision**: Use manual version saving. The backend exposes an explicit save-version endpoint that snapshots the draft metadata, assembled text, and ordered items at that moment.

**Consequences**: Version history stays meaningful and small. Users must intentionally save versions. Automatic checkpointing can be added later if editing loss becomes a real problem.

### Draft Creation Flow

**Context**: Drafts could be created as empty containers or directly from selected fragments. The MVP should keep the workflow predictable and the API easy to reason about.

**Decision**: Phase 3 starts with empty draft creation. Fragments are added after the draft exists through item APIs.

**Consequences**: Frontend has a simple lifecycle: create draft, then add/edit/reorder items. Bulk create-from-selection can be added later as a convenience endpoint without changing the underlying draft/item model.

### Draft Statuses

**Context**: Phase 3 needs enough status to separate active work from assembled drafts, while avoiding a publishing workflow.

**Decision**: Use `draft`, `ready`, and `archived`. New drafts start as `draft`. Users can mark a draft as `ready` when it is assembled enough for later AI workflows. Users can archive drafts to hide them from active work.

**Consequences**: Phase 4/5/6 can treat `ready` drafts as stronger inputs. Phase 3 avoids premature `published` semantics.

### Draft Item Editable Fields

**Context**: Draft blocks need enough editability to support manual composition without turning Phase 3 into a full rich-text editor.

**Decision**: Draft item updates support `edited_text`, `role`, and `position`. Notes are excluded from the MVP.

**Consequences**: Frontend can let users adjust copy text and functional labels. The backend contract remains small. Notes can be added later as an optional field if review workflow needs them.

### Version Snapshot Contents

**Context**: Manual versions should be useful for comparing or restoring draft content without overbuilding a full audit system.

**Decision**: A draft version stores the assembled `current_text` and ordered draft item snapshots at the time the user saves the version.

**Consequences**: Version detail can reconstruct the saved draft body and item order/source state. Draft metadata changes such as title or goal are not fully versioned in the MVP.

### Delete Semantics

**Context**: Phase 3 needs to protect draft/version history while keeping item editing simple.

**Decision**: Draft delete archives the draft by setting `status = archived`. Draft item delete hard-deletes the item from the current draft. Saved version item snapshots are immutable and remain readable.

**Consequences**: Users can hide old drafts without losing version history. Current draft editing remains straightforward. Restoring a deleted draft item from a previous version is out of scope for the MVP.

## Proposed Backend API

```text
GET    /api/drafts?page=1&page_size=20&status=draft
POST   /api/drafts
GET    /api/drafts/{draft_id}
PATCH  /api/drafts/{draft_id}
DELETE /api/drafts/{draft_id}

POST   /api/drafts/{draft_id}/items
PATCH  /api/drafts/{draft_id}/items/{item_id}
DELETE /api/drafts/{draft_id}/items/{item_id}
PATCH  /api/drafts/{draft_id}/items/reorder

POST   /api/drafts/{draft_id}/versions
GET    /api/drafts/{draft_id}/versions
GET    /api/drafts/{draft_id}/versions/{version_id}
```

## Implementation Plan

1. Add draft models, schemas, migration, and service layer with in-memory fallback for tests.
2. Add draft CRUD and item add/edit/delete/reorder APIs.
3. Add manual version save/list/detail APIs.
4. Update frontend integration docs and backend specs.
5. Add API tests for create, add fragment, edit, reorder, delete item, archive draft, and version snapshot.
