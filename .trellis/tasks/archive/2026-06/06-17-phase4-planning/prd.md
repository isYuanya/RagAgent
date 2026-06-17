# brainstorm: phase 4 planning

## Goal

Define Phase 4 for RagAgent: an AI next-sentence recommendation capability that reads the current draft context, retrieves useful fragment/material references, and returns several original candidate sentences with insertion guidance, reasoning, tone notes, and originality/risk warnings.

## What I Already Know

- Phase 1 established copy import, LLM analysis, review, persistence, collections, and service diagnostics.
- Phase 2 established fragment-level material extraction, fragment persistence, structured filtering, keyword search, knowledge library synchronization, and auto extraction for approved imports.
- Phase 3 established backend draft persistence, ordered draft items, editable draft text, and manual version snapshots.
- `doc/PRD.md` defines Phase 4 as AI next-sentence recommendation.
- Phase 4 should read current draft context, infer what function the next sentence should perform, retrieve similar context/follow-up fragments, generate 3-5 candidate sentences, and return recommendation reasons, insertion position, tone explanation, and originality risk warnings.
- Existing `/api/generate` is a stub-like full-copy generation endpoint and should not be overloaded as the Phase 4 next-sentence contract.
- Existing `CopyKnowledgeRetriever` is currently stubbed; Phase 4 may need a real structured fragment retrieval path before vector retrieval is introduced.
- The user currently owns frontend work; backend should provide stable APIs and frontend-facing docs.

## Assumptions (temporary)

- Phase 4 MVP should be backend-first.
- Phase 4 should use a dedicated API namespace rather than changing Phase 3 draft APIs.
- Phase 4 should work with current PostgreSQL-backed fragment filters/keyword search before introducing Milvus or reranking.
- Phase 4 should produce original suggestions, not directly copy fragment text into candidate sentences.
- Recommendation requests should include LLM status/model information, consistent with the product principle that long-running or LLM tasks are visible.

## Open Questions

- None for Phase 4 MVP.

## Requirements (evolving)

- Read current draft content and ordered draft items.
- Support recommending next sentence candidates for a draft.
- Retrieve relevant reference fragments from the fragment library.
- Generate multiple original candidate sentences.
- Return structured reasons, suggested insertion position, tone notes, and risk/originality warnings.
- Use an asynchronous task endpoint for recommendation generation.
- Return `task_id`, model, progress phase, and final structured recommendation result through the existing task polling pattern.
- Do not persist every recommendation attempt.
- Persist only accepted recommendation records.
- Accepted recommendation records should preserve the recommendation candidate, source draft, inserted draft item, and model metadata for later analysis.
- Provide a backend accept endpoint that inserts the selected candidate into the draft and persists the accepted recommendation in one operation.
- Accepting a recommendation creates a new draft item using the selected candidate sentence as `edited_text`.
- Use the current draft metadata and text to retrieve reference fragments from PostgreSQL-backed structured filters and keyword search.
- Let the LLM infer the recommended next-sentence function, such as transition, pain point, proof, solution, or CTA.
- Do not introduce Milvus/vector retrieval in the Phase 4 MVP.
- Generate 3 candidates by default.
- Allow `candidate_count` in the recommendation request, constrained to 1-5.
- Each recommendation candidate includes `candidate_id`, `text`, `function`, `reason`, `tone`, `suggested_order_index`, `risk_warnings`, and `reference_fragment_ids`.
- Recommendation task result includes the overall inferred next-sentence function and reference fragments used.
- Recommendation task result should include reference fragment summaries so frontend does not need a separate candidate detail endpoint.
- Do not add a separate preview/explain endpoint in Phase 4 MVP.
- Recommendation candidates may contain 1-2 sentences.
- Candidate text should still be short enough to insert as one draft item.
- Keep automatic full-copy drafting out of Phase 4.

## Acceptance Criteria (evolving)

- [x] Backend exposes a stable next-sentence recommendation API.
- [x] Recommendation request returns a task response.
- [x] Task polling exposes model/status/progress visibility.
- [x] Recommendation response includes `candidate_count` candidates, defaulting to 3 and constrained to 1-5.
- [x] Each candidate includes sentence text, reason, tone note, suggested insertion position, and risk warnings.
- [x] Each candidate exposes stable `candidate_id` for acceptance.
- [x] Recommendation result includes reference fragment summaries suitable for frontend display.
- [x] Phase 4 MVP does not require a separate candidate detail endpoint.
- [x] Candidate text is constrained to 1-2 sentences.
- [x] Recommendations use draft context and retrieved fragment references.
- [x] Recommendation result includes the inferred next-sentence function.
- [x] Phase 4 MVP does not require Milvus or vector retrieval.
- [x] Unaccepted recommendation candidates are not persisted as durable records.
- [x] Accepted recommendations are persisted with source draft, candidate content, inserted draft item, and model metadata.
- [x] Accepting a recommendation inserts the selected candidate into the draft.
- [x] Accepting a recommendation and recording the accepted recommendation are handled together by the backend.
- [x] Tests cover draft-backed recommendation flow.
- [x] Frontend integration docs are updated.

## Confirmed Implementation Plan

1. Add recommendation schemas, accepted recommendation model, and migration.
2. Add recommendation service: read draft, retrieve fragments, build prompt, parse validated LLM JSON.
3. Add async recommendation task entrypoint: `POST /api/recommendations/next-sentence`.
4. Add accept endpoint: insert selected candidate into draft and save accepted recommendation.
5. Update frontend docs and Trellis backend spec.
6. Add API tests with fake LLM coverage for recommendation task result and acceptance insertion.

## Definition of Done

- Tests added/updated for Phase 4 backend flows.
- Static checks pass.
- Frontend API docs updated.
- Trellis backend spec updated if new contracts are added.
- Changes committed separately from unrelated dirty worktree files.

## Out of Scope (temporary)

- Fully automatic drafting.
- Publishing workflow.
- Multi-user collaboration and permissions.
- Milvus/vector retrieval unless explicitly chosen for Phase 4 MVP.
- Reranker unless explicitly chosen for Phase 4 MVP.
- Persisting accepted recommendation analytics unless explicitly chosen for Phase 4 MVP.

## Technical Notes

- Existing draft APIs are documented in `doc/DRAFT_API.md`.
- Existing draft service is `app/services/drafts.py`.
- Existing fragment APIs are under `/api/knowledge/fragments`.
- Existing full-generation route is `app/api/routes/generate.py` and uses `app/workflows/copy_generation.py`.
- Existing LLM abstraction is `app/core/llm.py`.
- Existing task status schema is `app/schemas/task.py`.
- Existing in-memory task helpers are in `app/workers/tasks.py`.
- Existing retriever stub is `app/rag/retriever.py`.

## Initial Feasible Approaches

### Approach A: Synchronous next-sentence endpoint

- API example: `POST /api/recommendations/next-sentence`.
- Request contains `draft_id`, optional cursor/item context, optional filters, and desired candidate count.
- Response immediately returns recommendations and model metadata.
- Pros: simplest frontend integration, easiest MVP, fewer queue/worker moving parts.
- Cons: LLM latency blocks the request; less consistent with long-task principle if calls become slow.

### Approach B: Asynchronous recommendation task

- API example: `POST /api/recommendations/next-sentence` returns `TaskResponse`.
- Frontend polls `/api/tasks/{task_id}` for progress and result.
- Pros: consistent with import task pattern and visible LLM progress.
- Cons: more moving parts; for short 3-5 sentence suggestions it may feel heavy.
- Decision: selected for Phase 4 MVP.

### Approach C: Hybrid

- API supports sync by default and async mode when requested or when input is large.
- Pros: flexible future path.
- Cons: larger contract surface and more edge cases for frontend.

## Decision (ADR-lite)

### Recommendation Execution Mode

**Context**: Phase 4 recommendations call the LLM and should expose model/status visibility. Existing import flows already use task polling for long-running LLM work.

**Decision**: Phase 4 next-sentence recommendation uses an asynchronous task endpoint. The create endpoint returns `TaskResponse`, and frontend polls `/api/tasks/{task_id}` for progress and final recommendations.

**Consequences**: The frontend gets a consistent LLM task interaction model and can show loading/model/error states. The backend has slightly more queue/task plumbing than a synchronous endpoint, but the pattern will also support Phase 5 and Phase 6.

### Recommendation Persistence

**Context**: Full recommendation history would help future analytics, but it would add storage and cleanup complexity before the recommendation quality has been validated.

**Decision**: Phase 4 does not persist every generated recommendation. It persists only accepted recommendations, linked to the source draft and inserted draft item.

**Consequences**: The MVP keeps durable data meaningful and avoids filling the database with throwaway candidates. Later phases can analyze accepted suggestions without needing a full interaction log.

### Recommendation Acceptance

**Context**: Accepted recommendations should be traceable to the exact draft item inserted into the user's draft. If frontend performs insertion and backend records acceptance separately, partial failure can create broken analytics.

**Decision**: Phase 4 provides a backend accept endpoint. It receives the selected recommendation candidate, inserts it into the target draft as a new draft item, and persists the accepted recommendation record in one operation.

**Consequences**: The backend owns acceptance consistency. Frontend integration is simpler: call one accept endpoint, then refresh the returned draft detail. The accept endpoint must validate draft existence, candidate identity, and insertion order.

### Reference Retrieval Strategy

**Context**: Phase 4 needs useful material references, but the current retriever is a stub and vector retrieval would require embedding and Milvus synchronization work.

**Decision**: Phase 4 MVP uses PostgreSQL-backed structured fragment retrieval and keyword search. The backend builds a query from draft metadata and current text, retrieves a limited set of fragments, and asks the LLM to infer the next-sentence function while generating candidates.

**Consequences**: The MVP stays grounded in existing persisted fragment data and avoids premature vector complexity. Recommendation quality depends on available fragment tags and keyword matches, so the response should expose reference fragments used for transparency.

### Candidate Count and Shape

**Context**: The frontend needs a predictable set of choices, while later UX may allow users to request more or fewer suggestions.

**Decision**: Phase 4 defaults to 3 candidates and allows `candidate_count` from 1 to 5. Each candidate has a stable `candidate_id`, text, inferred function, reason, tone, suggested order index, risk warnings, and reference fragment ids.

**Consequences**: The default UI stays compact, but the backend contract can support richer controls later. Stable candidate ids let the accept endpoint validate which candidate was chosen.

### Candidate Explanation and Source Display

**Context**: The frontend should be able to show why a candidate is recommended and which fragments influenced it, without displaying raw ids or making extra calls for every candidate.

**Decision**: Phase 4 does not add a separate candidate detail endpoint. The recommendation task result includes enough explanation and reference fragment summaries for direct display.

**Consequences**: The MVP keeps frontend flow simple and avoids persistence for unaccepted candidate details. Response payloads are larger, but candidate counts are small enough for this to be acceptable.

### Candidate Length

**Context**: Some recommendation moments need more than a single sentence to complete a transition, proof point, or CTA, but Phase 4 should not become full automatic drafting.

**Decision**: Phase 4 candidates may contain 1-2 sentences and are inserted as one draft item when accepted.

**Consequences**: Suggestions can be more natural than a strict one-sentence limit, while still staying small enough for manual review and insertion. Longer paragraphs remain out of scope.
