# Phase 6 文案诊断、原创改写与合规评审

## Goal

Build backend support for diagnosing user-written or AI-generated copy, identifying quality, originality, and compliance risks, and returning actionable rewrite suggestions.

This phase should extend the existing async task pattern used by Phase 4 recommendations and Phase 5 auto-composition. Frontend remains user-owned, so backend must provide stable API contracts and integration documentation.

## Current Product Context

- Phase 1 established copy import, metadata extraction, structured analysis, review, and persistence.
- Phase 2 established fragment-level assets and knowledge-base retrieval.
- Phase 3 established draft persistence and draft item editing.
- Phase 4 established async next-sentence recommendation tasks.
- Phase 5 PRD defines async auto-composition and accepting generated candidates into drafts.
- Phase 6 in `doc/PRD.md` is defined as quality diagnosis, originality rewrite, and compliance review for user copy or generated copy.

## Product Requirements

### Input Scope

Backend should support both main Phase 6 entry points:

- Diagnose arbitrary pasted text.
- Diagnose an existing draft by `draft_id`.

At least one input source is required. For `draft_id`, backend reads the draft's current text and available draft context. For pasted text, backend uses only request-provided context.

Optional context fields should align with existing copy/draft generation context where possible:

- `platform`
- `audience`
- `purpose`
- `style`
- `industry`
- `constraints`

### Diagnosis Dimensions

The output should cover the PRD-defined dimensions:

- Opening attractiveness.
- Target audience clarity.
- Pain point specificity.
- Context coherence.
- Emotional resonance.
- Spoken-language naturalness.
- Conversion action.
- Originality risk.
- Compliance risk.

Diagnosis should avoid absolute numeric scoring. Use level labels instead:

- `weak`
- `fair`
- `strong`
- `risk`
- `high_risk`

### Sentence-Level Feedback

The response should point to specific sentences or spans that need attention.

Each issue should include:

- Original sentence or span.
- Dimension or risk category.
- Level.
- Why it should be changed.
- Concrete editing suggestion.
- Replacement text.

### Rewrite Output

The response should include rewrite candidates:

- A conservative rewrite that preserves the original intent.
- A stronger conversion-oriented rewrite.
- Optional compliance-safe rewrite when risks are detected.

Each rewrite candidate should explain what changed and why.

### Compliance And Originality

Compliance checks should combine:

- Existing local blocked-term or risk rule checks.
- LLM-based risk interpretation.
- Optional references to the disabled/block library if the current schema supports it.

Originality risk should be expressed as editorial risk, not as a legal verdict. The response should indicate whether content appears overly close to generic high-performing copy patterns or source-like phrasing when references are available.

### Persistence

MVP decision:

- Diagnosis task results are transient and are returned through the existing task result contract.
- The backend does not add a diagnosis-history table in Phase 6.
- Accepted rewrites are the durable boundary. When a diagnosis is linked to a `draft_id`, accepting a rewrite should save the accepted text through the draft workflow.
- Diagnosing arbitrary pasted text does not create a draft unless a later explicit endpoint is added.

### Async Task Behavior

Long-running diagnosis should use the existing task contract:

- `POST /api/diagnostics/copy` returns `TaskResponse`.
- Frontend polls `GET /api/tasks/{task_id}`.
- Task progress includes phase, model, percent, and current message.

Suggested phases:

- `queued`
- `preparing_context`
- `checking_rules`
- `calling_llm`
- `building_rewrites`
- `finished`
- `failed`

## API Draft

### `POST /api/diagnostics/copy`

Starts a diagnosis task.

Request fields:

- `text`: optional string.
- `draft_id`: optional string.
- `platform`: optional string.
- `audience`: optional string.
- `purpose`: optional string.
- `style`: optional string.
- `industry`: optional string.
- `constraints`: optional list of strings.
- `rewrite_modes`: optional list of strings.

Validation:

- At least one of `text` or `draft_id` is required.
- If both are provided, `text` takes precedence unless we decide otherwise.

Response:

- Standard `TaskResponse`.

### Task Result Shape

The completed task result should include:

- `source`: input source metadata.
- `summary`: overall diagnosis summary.
- `overall_level`: one level label.
- `dimensions`: list of dimension findings.
- `sentence_issues`: list of sentence-level findings.
- `rewrite_candidates`: list of rewrite candidates.
- `risk_warnings`: list of risk warnings.
- `model`: LLM model used.

### Optional Follow-Up Endpoint

If persistence is included:

- `POST /api/diagnostics/accepted-rewrite`
- Accepts `task_id`, `candidate_id`, and optionally `draft_id`.
- If `draft_id` exists, creates a new draft version or updates current draft depending on the chosen workflow.

## Frontend Integration Notes

Frontend should treat diagnosis as an async job:

1. Submit diagnosis request.
2. Poll the task endpoint.
3. Render `progress.phase`, `progress.percent`, `progress.model`, and `progress.current_message`.
4. On completion, read `result.dimensions`, `result.sentence_issues`, `result.rewrite_candidates`, and `result.risk_warnings`.
5. If accepted rewrite persistence is implemented, call the accepted-rewrite endpoint rather than mutating a draft locally.

## Acceptance Criteria

- [x] `POST /api/diagnostics/copy` creates an async diagnosis task and returns `TaskResponse`.
- [x] Diagnosis input accepts either pasted `text` or `draft_id`.
- [x] Task progress exposes phase, percent, current message, and model.
- [x] Completed task result includes overall level, dimension findings, sentence-level issues, rewrite candidates, risk warnings, and model.
- [x] Output avoids absolute numeric scoring and uses stable level labels.
- [x] Rule-based compliance warnings are included alongside LLM diagnosis.
- [x] `POST /api/diagnostics/accepted-rewrite` can apply an accepted rewrite to a draft when a `draft_id` is present.
- [x] Backend tests cover pasted text diagnosis, draft diagnosis, validation failure, and accepted rewrite persistence behavior.
- [x] Frontend integration documentation is added under `doc/`.
- [x] Frontend exposes diagnosis as a separate left-nav view after drafting, with task polling, progress/model display, findings, rewrite candidates, and accepted rewrite persistence.

## Decision

**Context**: Phase 6 needs to help users improve drafts without turning every diagnostic run into permanent data that must be managed, filtered, deleted, and migrated.

**Decision**: Use transient async diagnosis task results for MVP. Persist only user-accepted rewrites through the draft workflow.

**Consequences**:

- The feature stays aligned with Phase 4 and Phase 5 async task behavior.
- Frontend can show diagnosis immediately through task polling.
- The database schema stays smaller for MVP.
- Historical diagnosis analytics remain out of scope until there is a real review workflow for them.

## Open Questions

1. Should Phase 6 be allowed to use source fragments/templates as references for originality risk in MVP, or only diagnose the submitted text itself?
