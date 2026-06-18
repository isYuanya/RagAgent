# brainstorm: LangGraph 智能组稿改造

## Goal

把当前“智能组稿助手”从手写顺序编排服务，改造成 LangGraph 驱动的状态机工作流，让后续的人工确认、断点恢复、失败重试、状态检查和未来多分支 Agent 能力更自然。

## What I already know

- 用户希望把当前 agent 实现方式改为 LangGraph。
- 当前实现不是 LangGraph，也不是 LangChain Agent；它是 `app/services/smart_composition.py` 里的确定性后端 workflow。
- 当前 LLM 调用仍通过 `app/core/llm.py`，底层用了 `langchain_openai.ChatOpenAI`。
- `pyproject.toml` 已经声明 `langgraph>=0.2.60`。
- 当前虚拟环境实际 LangGraph 版本是 `1.2.5`。
- 当前智能组稿 API 已经存在：
  - `GET /api/assistant/options`
  - `POST /api/assistant/brief-prefill`
  - `POST /api/assistant/runs`
  - `GET /api/assistant/runs`
  - `GET /api/assistant/runs/{run_id}`
- 当前持久化表是 `smart_composition_runs`，保存业务视角的 run、timeline、result、draft/version ids。
- 当前 auto 模式已经跑通：组稿、候选选择、初稿版本、诊断、改写选择、终稿版本。
- 当前 guided 模式只做到生成候选后 `waiting_for_user`，还没有完整确认端点。

## Research References

- LangGraph overview: https://docs.langchain.com/oss/python/langgraph/overview
  - LangGraph 是低层 orchestration runtime，核心能力包括 durable execution、human-in-the-loop、persistence。
- LangGraph persistence: https://docs.langchain.com/oss/python/langgraph/persistence
  - checkpointer 适合 thread-scoped graph state，store 适合跨 thread 长期数据。
- LangGraph interrupts: https://docs.langchain.com/oss/python/langgraph/interrupts
  - `interrupt()` 可暂停 graph，依赖 checkpointer 和 `thread_id` 恢复，适合 guided confirmation。
- LangGraph checkpointers: https://docs.langchain.com/oss/python/langgraph/checkpointers
  - checkpointers 支持 HITL、fault tolerance、time travel；需要 `thread_id`。

## Assumptions (temporary)

- MVP 不应改变前端主 API 形状太多；`/api/assistant/runs` 仍是前端入口。
- LangGraph 应先替换 workflow orchestration 层，不重写已有业务服务：
  - composition generation 仍复用 `app.services.compositions`
  - diagnosis 仍复用 `app.services.diagnostics`
  - draft/version 保存仍复用 `app.services.drafts`
  - workflow business history 仍写 `smart_composition_runs`
- LangGraph checkpoint 是“执行态持久化”，`smart_composition_runs` 是“产品态/业务态持久化”，两者职责不同。

## Open Questions

- 无阻塞问题。需求已收敛，可进入实现。

## Requirements (evolving)

- 使用 LangGraph `StateGraph` 表达智能组稿流程。
- 保留当前 API 兼容性，避免前端大改。
- 保留当前业务持久化表和返回结构。
- 用 LangGraph state 承载每个节点的中间产物。
- 节点失败时能标记失败步骤并保存业务 run 状态。

## Acceptance Criteria (evolving)

- [ ] `POST /api/assistant/runs` auto 模式仍能完成并返回 finished run。
- [ ] 自动流程仍保存 initial/final draft version。
- [ ] 现有智能组稿测试继续通过。
- [ ] 核心流程由 LangGraph graph 执行，而不是 `_finish_auto_run` 手写顺序调用。
- [ ] LangGraph state 与 `smart_composition_runs` 业务响应一致。

## Definition of Done

- Tests added/updated.
- `python -m pytest tests` passes.
- `python -m ruff check app tests alembic` passes.
- `npm run build` passes if frontend contract changes.
- Docs/spec updated for LangGraph workflow contract.
- Commit message uses Chinese.

## Out of Scope (temporary)

- LangSmith deployment / Agent Server。
- 多 agent 协作、工具自动规划、反思循环。
- 替换所有 LLM 调用为 LangChain Runnable graph。
- 发布/外部分发。

## Technical Notes

- Likely impacted backend files:
  - `app/services/smart_composition.py`
  - new graph module such as `app/workflows/smart_composition_graph.py`
  - maybe schemas if adding graph state fields
  - tests under `tests/test_smart_composition_api.py`
- LangGraph docs indicate:
  - `StateGraph` is the appropriate low-level workflow abstraction.
  - `interrupt()` is useful for guided mode, but requires durable checkpointing and `thread_id`.
  - checkpointer and business persistence should not be conflated.

## Feasible Approaches

### Approach A: Graph core only, keep API synchronous for MVP

- Replace auto workflow internals with `StateGraph`.
- Keep current `smart_composition_runs` persistence and response shape.
- Use in-memory checkpointer for tests/local graph execution, or no checkpointer for auto mode initially.
- Guided remains current behavior or is minimally represented as a graph stop state.

Pros:
- Lowest risk.
- Validates LangGraph integration without redesigning API.
- Existing tests mostly remain stable.

Cons:
- Does not fully use LangGraph HITL interrupt benefits yet.
- Guided mode still incomplete.

### Approach B: Graph core + LangGraph interrupt for guided mode

- Build `StateGraph` with nodes for retrieval, generation, selection, draft save, diagnosis, rewrite save.
- Add `interrupt()` at guided checkpoints.
- Use `thread_id = run_id`.
- Add/adjust endpoints to resume graph with user decisions.
- Persist both LangGraph checkpoint and `smart_composition_runs`.

Pros:
- Matches the reason to use LangGraph: human-in-the-loop and resume.
- Guided mode becomes structurally correct.

Cons:
- More moving pieces: checkpointer choice, resume API, idempotency of side effects.
- Need careful handling so draft/version creation does not duplicate after resume/replay.

### Approach C: Full LangGraph-first runtime

- Move workflow persistence primarily into LangGraph checkpointer.
- Treat `smart_composition_runs` as a projection/read model.
- Potentially add streaming events from graph to frontend later.

Pros:
- Best long-term architecture for complex agent runtime.

Cons:
- Too large for current MVP.
- More migration risk; current business table is already useful and frontend depends on it.

## Recommended Direction

Recommend Approach B if we want this change to be meaningful, not just a cosmetic StateGraph wrapper. But implement it in slices:

1. Extract a graph module and run auto mode through LangGraph while keeping current API/tests.
2. Add guided interrupts/resume endpoints after graph state is stable.
3. Add durable checkpointer strategy if the first guided slice needs true resume across process restart.

## Confirmed Decisions

### Scope

- Use Approach B: Graph core plus guided interrupt/resume.
- Auto mode should run through LangGraph while keeping current API behavior.
- Guided mode should gain backend resume endpoints for material confirmation, composition confirmation, and rewrite confirmation.

### Guided Pause Mechanism

- Guided confirmation points use real LangGraph `interrupt()`, not database status simulation.
- `run_id` is the LangGraph `thread_id`.
- Confirm endpoints resume the interrupted graph with LangGraph `Command(resume=...)`.
- Interrupt payloads must be JSON-serializable and directly useful to the frontend.
- Side effects before an interrupt must be avoided or idempotent, consistent with LangGraph interrupt rules.

### Checkpointer Strategy

- MVP uses LangGraph in-memory checkpointer first.
- Guided interrupt/resume works while the backend process is alive.
- `smart_composition_runs` remains the durable business history.
- Durable PostgreSQL/SQLite LangGraph checkpointing is explicitly deferred to a later task.
- The graph module should keep checkpointer creation isolated so it can be swapped later.

### Confirmation Payloads

- MVP uses selection-only confirmations, not inline editing.
- `confirm-materials` accepts selected/kept `material_ids`.
- `confirm-composition` accepts `candidate_id`.
- `confirm-rewrite` accepts `rewrite_candidate_id`.
- Editing selected candidate text or rewrite text is out of scope for this workflow MVP; users can edit in the draft workspace after generation.

## Requirements Update

- Add LangGraph `StateGraph` for the smart composition assistant.
- Use `run_id` as the LangGraph `thread_id` so the workflow can resume.
- Add backend resume endpoints for guided checkpoints:
  - `POST /api/assistant/runs/{run_id}/confirm-materials`
  - `POST /api/assistant/runs/{run_id}/confirm-composition`
  - `POST /api/assistant/runs/{run_id}/confirm-rewrite`
- Use LangGraph `interrupt()` at the guided confirmation points.
- Resume graph execution with `Command(resume=...)` from confirm endpoints.
- Use `InMemorySaver` or equivalent in-memory checkpointer for this MVP.
- Preserve the existing `smart_composition_runs` business persistence and frontend response shape.
- Make side-effect nodes idempotent enough to avoid duplicate drafts or versions after resume/retry.
- Confirm endpoints should use selection-only request bodies.

## Acceptance Criteria Update

- [ ] Auto mode executes through LangGraph and still returns `finished`.
- [ ] Guided mode pauses for material confirmation.
- [ ] Guided mode can resume after material confirmation.
- [ ] Guided mode pauses for composition confirmation and can create an initial draft after confirmation.
- [ ] Guided mode pauses for rewrite confirmation and can save the final draft after confirmation.
- [ ] Resume endpoints return the updated `SmartCompositionRunDetail`.
- [ ] Repeated resume calls should not create duplicate drafts or versions.
- [ ] Backend restart losing an interrupted guided execution is accepted in MVP and documented.
- [ ] Confirm endpoints accept selection-only payloads.
- [ ] Confirm endpoints reject missing/unknown selected ids with clear 404/422 behavior.

## Final MVP Summary

**Goal**: Rebuild the smart composition assistant workflow on LangGraph while preserving current API compatibility and adding real guided human-in-the-loop resume behavior.

**Technical Approach**:

- Add a LangGraph `StateGraph` for smart composition.
- Keep existing business services as graph node implementations.
- Use `run_id` as LangGraph `thread_id`.
- Use in-memory LangGraph checkpointer for MVP.
- Use `interrupt()` for guided checkpoints.
- Resume interrupted graph with `Command(resume=...)`.
- Keep `smart_composition_runs` as the durable product history/read model.
- Keep current frontend response shape and add selection-only confirm endpoints.

**Implementation Plan**:

1. Create graph state and graph builder module.
2. Move current auto orchestration into graph nodes.
3. Update `create_run` to invoke graph for auto and guided.
4. Add confirm request schemas and routes.
5. Implement guided resume endpoints.
6. Add/update tests for auto, guided pause, material confirm, composition confirm, rewrite confirm, duplicate prevention basics.
7. Update API docs/specs.
