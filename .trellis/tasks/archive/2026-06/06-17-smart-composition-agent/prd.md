# brainstorm: 智能组稿助手

## Goal

Build an "智能组稿助手" workflow that automates the current copywriting pipeline: collect a user brief, retrieve reusable knowledge, generate draft candidates, assemble a draft, diagnose/rewrite it, and surface checkpoints for user approval.

## What I already know

- The user wants an agent workflow feature named "智能组稿助手".
- The existing system already has these building blocks:
  - Knowledge libraries: raw copies, analyses, fragments, templates, collections.
  - Draft workspace: persistent drafts and draft items.
  - Phase 4 next-sentence recommendations.
  - Phase 5 auto composition: generates three 5-part candidates and can accept one into a draft.
  - Phase 6 diagnosis/rewrite: diagnoses draft/text and can accept rewrite into a draft version.
- Current automation opportunity is orchestration, not rebuilding every capability from scratch.

## Assumptions (temporary)

- The first MVP should automate the path from a brief to a diagnosed draft.
- The user should still approve important transitions, especially candidate selection and final rewrite acceptance.
- The workflow should expose progress/model/status like existing async tasks.

## Open Questions

- Should the MVP be a fully automatic one-click flow or a guided step-by-step assistant?

## Requirements (evolving)

- Provide a named agent workflow: "智能组稿助手".
- Reuse existing backend services where possible rather than duplicating auto-composition and diagnosis logic.
- Persist outputs as normal draft records so existing draft workspace and diagnosis screens remain usable.

## Acceptance Criteria (evolving)

- [ ] User can start the assistant from a brief.
- [ ] Assistant can produce draft candidates using existing knowledge fragments.
- [ ] User can approve one candidate into a persistent draft.
- [ ] Assistant can trigger diagnosis/rewrite on the draft.
- [ ] Workflow progress is visible to frontend.

## Definition of Done

- Tests added/updated for workflow orchestration.
- Lint / typecheck / build checks pass.
- API/frontend integration docs updated if endpoints or flow contracts change.
- Workflow failure states are visible and recoverable.

## Out of Scope (temporary)

- Autonomous publishing.
- Multi-user permissions.
- Long-term agent memory beyond persisted drafts/tasks.

## Technical Notes

- Existing docs inspected:
  - `doc/COMPOSITION_API.md`
  - `doc/DIAGNOSTIC_API.md`
  - `doc/RECOMMENDATION_API.md`
  - `doc/DRAFT_API.md`
- Likely implementation surface:
  - Backend orchestration endpoint/service for the assistant workflow.
  - Frontend workflow view or panel.
  - Existing async `TaskResponse` polling contract.

## Confirmed Decisions

### Automation Mode

- The assistant has two workflow modes:
  - `auto`: default mode. The user starts once from a brief, then the assistant runs through composition, candidate selection, draft creation, diagnosis, rewrite selection, and final draft update.
  - `guided`: optional mode. The user can pause at key checkpoints and manually confirm candidate selection and rewrite acceptance.
- The primary product promise is one-click automation, with guided mode as an override for users who want control.

### Acceptance Criteria Update

- [ ] User can choose `auto` or `guided`; `auto` is the default.
- [ ] In auto mode, assistant can select one composition candidate and persist it as a draft without requiring another click.
- [ ] In guided mode, user can review and approve the selected composition candidate before draft creation.
- [ ] In auto mode, assistant can select and apply one rewrite candidate into a saved draft version.
- [ ] In guided mode, user can review and approve the rewrite candidate before it is applied.
- [ ] Workflow progress is visible throughout the run.

### ADR-lite

**Context**: The assistant can either be a fully automated agent or a controlled workflow. A fully automatic flow better matches the agent product promise, but the product is still early and generated copy quality needs review options.

**Decision**: Make `auto` the default mode and expose `guided` as an optional mode.

**Consequences**:

- Backend orchestration must support checkpoint state even if auto mode does not stop at every checkpoint.
- Auto mode needs deterministic selection policies for composition candidates and rewrite candidates.
- Guided mode can reuse the same workflow states, but leaves selected actions pending until the user confirms.

## Open Question Update

- What default candidate-selection and rewrite-selection policy should one-click mode use?

## Confirmed Decisions - Selection Policy

- Auto mode uses a hybrid selection policy:
  - First pass: deterministic rule scoring filters/ranks candidates by structure completeness, brief match, available references, risk warnings, and compliance signals.
  - Second pass: LLM judge chooses from the top-ranked candidates and returns a short selection reason.
- The same pattern applies to rewrite candidates when diagnosis returns multiple rewrites.
- The workflow must persist the selected candidate id, selection method, score signals, judge model, and selection reason in workflow metadata.

## Acceptance Criteria Update - Selection

- [ ] Auto mode selects composition candidates via rule scoring plus LLM judge.
- [ ] Auto mode selects rewrite candidates via rule scoring plus LLM judge when multiple candidates exist.
- [ ] Selection reasons are visible to the frontend and stored in workflow result metadata.
- [ ] If LLM judging fails, the workflow falls back to the top rule-scored candidate and records the fallback reason.

## Confirmed Decisions - Output Versions

- Auto mode keeps both intermediate and final outputs:
  - `initial_draft`: the accepted composition candidate before diagnosis/rewrite.
  - `final_draft`: the diagnosis-rewritten version after auto rewrite selection.
- Both versions should be persisted as normal draft version snapshots.
- The active draft after workflow completion should contain the final rewritten text.
- Workflow metadata should reference both version ids so the frontend can show "initial draft vs final draft" later.

## Acceptance Criteria Update - Output Versions

- [ ] Auto workflow saves an initial draft version immediately after composition candidate acceptance.
- [ ] Auto workflow saves a final draft version after diagnosis rewrite acceptance.
- [ ] Workflow result includes `draft_id`, `initial_version_id`, and `final_version_id`.
- [ ] User can continue editing the final draft in the existing draft workspace.

## Confirmed Decisions - Brief Input UX

- The assistant brief should be selection-first, not blank-text-first.
- Users choose from structured options for most fields:
  - knowledge collection / reference scope
  - product or topic category when available
  - target audience
  - publishing platform
  - conversion purpose
  - tone/style
  - constraints/compliance preferences
- Free-form input is a fallback:
  - "other" option for a field.
  - optional extra notes / selling points.
  - optional custom constraints.
- Collection selection is included in MVP so the assistant can restrict retrieval to a relevant knowledge scope instead of searching all content.
- Option lists should be populated from existing backend data where possible:
  - collections from `GET /api/knowledge/collections`.
  - platforms/purposes/audiences/styles can start from configured presets and later be derived from tag library / historical copy metadata.

## Acceptance Criteria Update - Brief Input UX

- [ ] Frontend brief form presents structured choices before free-form fields.
- [ ] User can select one or more knowledge collections as the retrieval scope.
- [ ] Every required brief field has either a selected preset value or an explicit "other" free-form fallback.
- [ ] Backend accepts both preset values and free-form fallback values in the same workflow request shape.

## Confirmed Decisions - Brief Input Pattern

- MVP uses a hybrid brief input pattern:
  - Main surface: one-page selection form for structured choices.
  - Optional accelerator: user can enter one natural-language sentence, and the assistant pre-selects likely form options.
  - User can review and manually adjust all pre-selected options before starting the workflow.
- The one-sentence prefill should never start generation automatically. It only fills the form.
- Prefill should return confidence/notes so frontend can mark uncertain selections if useful.

## Acceptance Criteria Update - Brief Prefill

- [ ] User can type one sentence and ask the assistant to prefill the brief form.
- [ ] Prefill maps text into the same structured fields used by the manual form.
- [ ] User can edit prefilled values before starting auto/guided workflow.
- [ ] If prefill fails, the user can still fill the selection form manually.

## Confirmed Decisions - Progress UX

- MVP shows a step timeline, not only a simple percentage bar.
- Timeline steps:
  1. brief parsing / option prefill
  2. knowledge retrieval
  3. composition candidate generation
  4. composition candidate selection
  5. initial draft version save
  6. initial draft diagnosis
  7. rewrite candidate selection
  8. final draft version save
- Step statuses:
  - `pending`
  - `running`
  - `completed`
  - `failed`
  - `waiting_for_user`
- Each step can expose:
  - status
  - percent contribution or ordering
  - model when an LLM was used
  - short message
  - short reason / selection explanation when applicable
- Detailed logs are out of MVP, but the workflow result should keep enough metadata to debug candidate/rewrite selection.

## Acceptance Criteria Update - Progress UX

- [ ] Frontend can render a step timeline with current state.
- [ ] Backend task progress includes structured step states, not only `percent` and `current_message`.
- [ ] Guided mode can mark checkpoint steps as `waiting_for_user`.
- [ ] Failed steps expose a user-readable message and preserve prior completed step metadata.

## Confirmed Decisions - Failure Handling

- MVP uses fail-stop behavior:
  - If a workflow step fails, the workflow stops at that step.
  - Completed artifacts before the failed step are preserved.
  - The failed step is marked `failed` in the timeline with a user-readable message.
  - The user can retry from the failed step instead of starting over.
- No silent downgrade to a lower-quality final draft in MVP.
- If initial composition succeeds but diagnosis fails, the initial draft and its version remain usable.
- If final rewrite save fails, the initial draft remains usable and the workflow can retry finalization.

## Acceptance Criteria Update - Failure Handling

- [ ] Failed workflow stops at the failed step.
- [ ] Completed draft/version artifacts are not deleted when a later step fails.
- [ ] User can retry from the failed step.
- [ ] Frontend displays failed step message and available retry action.

## Confirmed Decisions - Guided Checkpoints

- Guided mode pauses at three checkpoints:
  1. Knowledge material confirmation after retrieval.
  2. Composition candidate confirmation after candidate generation and recommendation.
  3. Rewrite candidate confirmation after diagnosis and rewrite generation.
- At each checkpoint, backend marks the relevant timeline step as `waiting_for_user`.
- User can accept the system-recommended selection or override it.
- Auto mode does not pause at these checkpoints, but still records retrieved materials, selected candidate, selected rewrite, and selection reasons for later inspection.

## Acceptance Criteria Update - Guided Checkpoints

- [ ] Guided mode can pause after knowledge retrieval and wait for material confirmation.
- [ ] Guided mode can pause after composition candidate recommendation and wait for candidate confirmation.
- [ ] Guided mode can pause after rewrite recommendation and wait for rewrite confirmation.
- [ ] User confirmations resume the workflow from the paused step.
- [ ] Auto mode records the same checkpoint metadata without pausing.

## Confirmed Decisions - Material Confirmation Scope

- Guided material confirmation supports lightweight controls:
  - User can deselect retrieved materials they do not want to use.
  - User can change selected collections and trigger retrieval again.
  - User cannot manually search and add arbitrary materials in MVP.
- Auto mode uses the retrieved material set directly, but records the material ids and retrieval reason.
- Manual search/add can be a future enhancement if guided mode needs more editorial control.

## Acceptance Criteria Update - Material Confirmation

- [ ] Guided mode can show retrieved material summaries for confirmation.
- [ ] User can deselect retrieved materials before continuing.
- [ ] User can change collection scope and rerun material retrieval.
- [ ] Manual material search/add is not required in MVP.

## Confirmed Decisions - Workflow History

- MVP includes lightweight workflow history.
- Each workflow run should persist:
  - workflow id
  - brief input and selected options
  - mode: `auto` or `guided`
  - status
  - timeline steps
  - selected collection ids
  - retrieved/confirmed material ids
  - selected composition candidate id and reason
  - selected rewrite candidate id and reason
  - `draft_id`
  - `initial_version_id`
  - `final_version_id`
  - created/updated timestamps
- Frontend can show recent workflow runs and reopen a run to inspect progress/result.
- Full model-call audit logs are out of MVP.

## Acceptance Criteria Update - Workflow History

- [ ] Backend persists lightweight workflow run records.
- [ ] Frontend can list recent workflow runs.
- [ ] User can reopen a workflow run and see brief, mode, status, timeline, draft links, and version ids.
- [ ] Workflow history does not need full prompt/response audit logs in MVP.
