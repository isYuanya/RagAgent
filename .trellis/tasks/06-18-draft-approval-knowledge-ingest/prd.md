# 草稿审批入知识库

## Goal

在草稿工作台给草稿增加“审批通过”动作。草稿通过后，后端把当前草稿正文沉淀为可追溯的原始文案资产，并自动触发已有的文案片段拆解流程，让通过后的成稿进入知识库，后续可被片段库、推荐、组稿助手复用。

## What I already know

- 用户希望在草稿工作台中给文案增加“审批通过”按钮。
- 审批通过之后，也要进行拆解并进入知识库。
- 现有草稿状态是 `draft | ready | archived`。
- 现有片段拆解入口 `extract_fragments_for_asset_id(source_copy_id)` 依赖 `CopyAssetSummary.status == "approved"`。
- 现有导入后处理 `sync_imported_asset_to_knowledge(asset)` 会同步分析字段到模板库，并在资产已审核时自动触发片段拆解。
- 草稿正文由 `draft_items.edited_text` 按顺序拼接成 `current_text`。
- 片段库当前以 `source_copy_id` 作为一等来源字段，因此最小可靠方案是审批草稿时创建一个 `approved` 的 CopyAsset，再复用现有拆解链路。

## Assumptions

- 审批按钮主要出现在草稿工作台，不需要单独做一套复杂审核流。
- MVP 允许审批动作同步执行；如果 LLM 拆解失败，接口返回可见错误或结果信息，不静默吞掉。
- 草稿审批应具备幂等性：同一草稿重复点击不应重复创建多个原文案资产或重复拆片段。
- 草稿审批后的来源引用应能看出来自哪个草稿，而不是只有一串 UUID。

## Requirements

- 后端新增草稿审批接口，例如 `POST /api/drafts/{draft_id}/approve`。
- 审批接口读取草稿当前正文；正文为空时返回 `409` 或 `422`。
- 审批通过后，草稿状态复用现有 `ready`，表示“已审批通过，可进入知识库/后续流程”，并在 `metadata` 中记录知识库入库结果。
- 审批通过后创建或复用一个 CopyAsset：
  - `source_text = draft.current_text`
  - `status = approved`
  - `platform/audience/purpose` 继承草稿字段
  - `source_url` 可为空
  - metadata 需要保留 `source_type = draft`、`source_draft_id`、`source_draft_title`
- 审批通过后复用现有片段拆解流程入片段库。
- 审批动作应幂等：草稿已有关联的 `approved_copy_asset_id` 时，复用该资产并重试/跳过已有片段拆解。
- 前端草稿工作台新增“审批通过”按钮。
- 前端点击后刷新草稿详情，并提示拆解结果。

## Acceptance Criteria

- [ ] 草稿工作台能对非归档、有正文的草稿点击“审批通过”。
- [ ] 审批后草稿详情返回通过态和入库元数据。
- [ ] 审批后原始文案库能看到一条来自该草稿的原文案。
- [ ] 审批后片段库能看到基于该文案拆出来的片段。
- [ ] 重复审批同一草稿不会生成重复原文案资产。
- [ ] 空草稿审批失败，前端能显示错误。
- [ ] 后端测试覆盖成功审批、空正文、重复审批幂等。
- [ ] 前端构建通过。

## Open Questions

- 已确认：草稿审批通过后的状态复用现有 `ready`，不新增 `approved` 状态。

## Decision

### Reuse Draft `ready` Status

**Context**: 草稿已有 `draft | ready | archived` 三种状态。新增 `approved` 会带来 schema、筛选、列表、测试和历史数据语义的额外改动。

**Decision**: 审批通过动作将草稿状态设为 `ready`。产品文案显示为“审批通过”，内部状态仍使用 `ready`。

**Consequences**: 改动更小，兼容现有草稿列表和筛选；后续如果需要区分“可进入后续流程”和“已进入知识库”，用 `metadata.knowledge_ingest` 记录入库状态，而不是新增草稿状态。

## Technical Approach

推荐方案：草稿审批时创建/复用一个 approved CopyAsset，然后调用现有 `sync_imported_asset_to_knowledge(asset)` 或 `extract_fragments_for_asset_id(asset.id)`。

这样做的好处：
- 片段库仍然用现有 `source_copy_id` 模型，不新增平行来源模型。
- 原始文案库也能保存最终成稿和来源。
- 后续模板库、案例库、推荐检索可以复用现有 CopyAsset/Knowledge 体系。

需要注意：
- 当前 `create_copy_asset()` 会根据 `analysis.confidence` 决定初始状态，不能直接用于“审批即 approved”的路径，可能需要新增服务函数或可选参数。
- 审批草稿最好不要强制先做完整 CopyAnalysis，除非已有分析结果可复用；MVP 可先以 raw copy + fragment extraction 为主。
- 拆解失败时不应把草稿状态回滚到未通过，但应把错误记录在 metadata 或返回结果中，方便用户重试。

## Out of Scope

- 不做完整多级审核流、审核人、审核时间线。
- 不做权限系统。
- 不做数据库新表，除非现有 metadata 无法满足幂等追踪。
- 不重新设计片段来源模型。
- 不做异步任务化审批，除非现有同步 LLM 拆解明显影响接口稳定性。

## Definition of Done

- Tests added/updated.
- `python -m ruff check app tests alembic` passes.
- `python -m pytest tests` passes or scoped test failures are explained.
- `npm run build` passes for frontend changes.
- Docs/spec updated if API contract changes.
