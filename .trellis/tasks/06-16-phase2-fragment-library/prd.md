# brainstorm: phase 2 fragment library

## Goal

Define Phase 2 for RagAgent: turn approved copy assets into reusable, searchable fragments with provenance and context, without jumping ahead to full semantic retrieval, next-sentence recommendation, or draft assembly.

## What I Already Know

- Phase 1 has established copy import, LLM analysis, review status, raw copy persistence, structured analysis persistence, collections, and basic knowledge library endpoints.
- Phase 2 in `doc/PRD.md` is scoped as fragment-level material library plus basic retrieval.
- The intended fragment library stores source copy ID, source analysis ID, sequence order, previous/next fragment, before/after context, fragment text, fragment role, position, industry, source quality, and risk level.
- Existing backend already has a `/api/knowledge/fragments` CRUD surface and persistence model, but Phase 2 still needs product decisions about how fragments are created, reviewed, and searched.
- Current user preference: discuss first; no implementation yet.

## Assumptions

- Phase 2 should begin from approved copy assets only, not unreviewed imports.
- Fragment extraction should be LLM-assisted, with low-confidence or ambiguous fragments requiring human review later.
- The first MVP should stay backend-first because the user currently owns frontend work.

## Open Questions

- Confirm whether this Phase 2 MVP scope is complete enough to move into implementation planning.

## Requirements (Evolving)

- Persist fragment-level materials with source traceability.
- Preserve enough context around each fragment to make later retrieval and reuse safe.
- Support basic structured filtering before introducing vector search.
- Use automatic LLM fragment extraction first, then allow human correction of the generated fragments.
- Treat low-confidence or ambiguous fragment results as needing human correction rather than blocking extraction.
- Trigger fragment extraction automatically when a copy asset is reviewed as `approved`.
- Give generated fragments their own review status using confidence-based routing: high-confidence fragments become usable, low-confidence fragments require human correction.
- Generate function-level fragments, not sentence-level fragments, for the MVP. A fragment may contain one to three sentences when they serve the same copywriting function.
- Support practical structured filtering plus keyword search for fragments.
- Fragment retrieval filters include `fragment_role`, `position`, `industry`, `status`, `platform`, `purpose`, `audience`, and `risk_level`.
- Fragment retrieval includes `q` keyword search using PostgreSQL text matching first; semantic vector retrieval is out of scope.

## Implemented Slice

- Added fragment fields for confidence, status, source platform, source purpose, and source audience.
- Added practical filters and keyword search to `GET /api/knowledge/fragments`.
- Added automatic function-level fragment extraction when a copy asset is reviewed as `approved`.
- Added idempotency by source copy ID so repeated approval does not duplicate fragments.
- Added confidence-based routing using `FRAGMENT_AUTO_APPROVE_MIN_CONFIDENCE`.
- Added frontend-facing schema documentation for new fragment fields and filters.

## Acceptance Criteria (Evolving)

- [ ] Approved copy can produce fragment records linked to the source copy and analysis.
- [ ] Reviewing a copy asset as `approved` starts fragment extraction automatically.
- [ ] Fragment records include text, role, position, sequence, and context window.
- [ ] Fragment records represent function-level spans such as hook, pain point, explanation, proof, solution, transition, and CTA.
- [ ] Fragment list can be filtered by at least source copy, role, position, and industry.
- [ ] Fragment list supports filters for role, position, industry, status, platform, purpose, audience, and risk level.
- [ ] Fragment list supports keyword search through `q`.
- [ ] Generated fragments can be corrected after extraction.
- [ ] Generated fragments expose confidence and review status.
- [ ] High-confidence generated fragments are immediately searchable, while low-confidence fragments require review/correction before use.
- [ ] Phase 2 scope explicitly excludes next-sentence recommendation and draft assembly.

## Decision (ADR-lite)

### Fragment Creation Mode

**Context**: Fragment records need to be created quickly enough to build a useful library, but LLM segmentation quality will vary by copy type.

**Decision**: Phase 2 will use automatic LLM fragment extraction plus human correction.

**Consequences**: The backend must preserve generated fragment records in a reviewable/editable shape. Human review is not a separate phase blocker; it is the correction path for low-confidence or imperfect fragments.

### Fragment Extraction Trigger

**Context**: Fragment extraction can be triggered manually, automatically on approval, or batched later.

**Decision**: Phase 2 MVP triggers fragment extraction automatically when a copy asset is reviewed as `approved`.

**Consequences**: The review path becomes the ingestion boundary for fragment generation. The backend needs idempotency so approving the same asset again does not create duplicate fragments, and errors must be visible without breaking the copy approval itself.

### Fragment Review Routing

**Context**: Generated fragments can vary in quality even when the source copy is approved.

**Decision**: Fragments have their own review status and are routed by confidence. High-confidence fragments become usable immediately; low-confidence fragments are marked for human correction.

**Consequences**: Fragment extraction output must include per-fragment confidence. Fragment APIs need status filtering and update support so frontend can show both usable fragments and fragments that need correction.

### Fragment Granularity

**Context**: Sentence-level fragments are flexible but often too small to reuse safely without context. Full paragraphs can be too broad for retrieval and composition.

**Decision**: Phase 2 uses function-level fragments. Each fragment captures one copywriting function, such as hook, pain point, explanation, proof, solution, transition, or CTA. A fragment may contain one to three sentences if they work together.

**Consequences**: Fragment extraction prompts should optimize for reusable functional spans and preserve adjacent context. Sentence-level child fragments are out of scope for Phase 2 and can be introduced later for next-sentence recommendation.

### Fragment Retrieval Scope

**Context**: Phase 2 needs fragments to be practically usable before vector retrieval and next-sentence recommendation exist.

**Decision**: Phase 2 MVP supports practical structured filtering plus keyword search. Filters include role, position, industry, status, platform, purpose, audience, and risk level. Keyword search uses a simple `q` parameter backed by PostgreSQL text matching.

**Consequences**: Fragment records should either store denormalized source metadata or query through source copy metadata so frontend can filter fragments by platform, purpose, and audience. Milvus/vector retrieval and reranking remain out of scope.

## Out of Scope

- Full semantic vector retrieval.
- AI next-sentence recommendation.
- Manual draft assembly workspace.
- Multi-user workflow.

## Technical Notes

- Relevant spec: `.trellis/spec/backend/knowledge-api.md`
- Relevant service: `app/services/knowledge.py`
- Relevant model: `app/models/knowledge.py`
- Relevant schema: `app/schemas/knowledge.py`
- Relevant tests: `tests/test_knowledge_api.py`
