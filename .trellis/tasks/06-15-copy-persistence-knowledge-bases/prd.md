# 文案拆解持久化与多知识库

## Goal

让拆解后的文案资产真正进入后端持久化存储，并为后续多个知识库建立清晰的数据边界。目标不是一次性完成完整向量检索系统，而是先把“文案资产、拆解结果、审核结果、知识库归属”落到稳定的数据模型和 API 契约里，避免 worker/API 进程、Redis 缓存和内存状态之间的数据不一致。

## What I already know

* 用户现在只要求后端建设，前端由用户自行负责；后端需要同步写清前端对接文档。
* 现有文案导入会逐行调用 LLM，生成 `CopyAssetSummary`，并尝试写入 `copy_sources` 和 `copy_analyses`。
* 现有 `CopySource` 只有 `source_text`、`source_url`、`metadata_json`、`created_at`。
* 现有 `CopyAnalysis` 只有 `copy_source_id`、`result_json`、`confidence`、`created_at`。
* 现有审核结果和状态主要塞在 `CopySource.metadata_json` 中，不是明确的关系模型。
* 当前没有 Alembic 迁移文件，`alembic/versions/` 只有 `.gitkeep`。
* 当前资产读取顺序是 Postgres -> Redis -> 内存，Postgres 不可用时会退回 Redis/内存。
* 当前 RAG 模块仍是 stub：`app/rag/ingestion.py` 只做文档标准化，`app/rag/retriever.py` 只返回固定 stub context。
* 现有 PRD 已提到文案资产、作者、模板库、检索库和后续作者分析，但还没有“多个知识库”的明确模型。

## Assumptions (temporary)

* MVP 后端主存储应以 PostgreSQL 为准，Redis 只作为队列/缓存/本地兜底，不作为长期事实来源。
* “多个知识库”不是只有一个向量检索库，而是多个面向不同用途的数据资产库。
* 已明确的知识库类型：
  * 原始文案库：保存原文和来源。
  * 结构化拆解库：保存每条文案的分析结果。
  * 模板库：保存从文案中抽象出来的句式和框架。
  * 标签库：保存行业、情绪、目的、人群、钩子类型等标签体系。
  * 案例库：保存高表现案例及其表现原因。
  * 禁用库：保存敏感词、违规表达、不要复刻的内容。
* 本任务先处理结构化资产库和知识库归属；真正的 Milvus 向量索引和高级召回可以作为后续任务。
* API 变更应保持向后兼容，现有资产列表/详情接口继续可用，只新增可选字段或新增端点。

## Open Questions

* 删除采用软删除还是硬删除？

## Requirements (evolving)

* 拆解后的原文案、作者信息、指标、自动拆解结果、人工审核结果和审核状态必须持久化。
* 重启 API/worker 后，已导入资产仍能从后端查询到。
* 知识库需要成为后端一等概念，至少能创建、查询，并能关联文案资产。
* 原始文案库保存原始文案和来源信息，作为所有后续拆解、模板沉淀、检索和生成的上游事实来源。
* 结构化拆解库保存每条文案的 LLM 自动分析结果和人工审核结果。
* 模板库保存可复用句式、结构框架和适用场景。
* 标签库保存可复用的分类标签，包括行业、情绪、目的、人群、钩子类型。
* 案例库保存高表现文案案例及其高表现原因。
* 禁用库保存敏感词、违规表达和明确不要复刻的内容。
* 本轮 MVP 六个库都做最小可用，支持后端增删查改；模板库、标签库、案例库、禁用库主要人工维护，不做复杂自动抽取。
* 本轮不要求 LLM 自动抽象模板、自动打标签、自动识别高表现原因或自动生成禁用表达。
* 模板、标签、案例、禁用项都可以关联到原始文案或结构化拆解结果，保留来源追溯。
* 支持知识库集合层，一条原始文案可以同时属于多个集合，例如“美妆库”“高转化库”“某账号库”。
* 后端新增统一知识库 API 命名空间：
  * `/api/knowledge/raw-copies`
  * `/api/knowledge/analyses`
  * `/api/knowledge/templates`
  * `/api/knowledge/tags`
  * `/api/knowledge/cases`
  * `/api/knowledge/blocks`
  * `/api/knowledge/collections`
* 六类知识库都支持列表、创建、详情、更新、删除。
* 资产列表/详情应能暴露资产所属集合信息，供前端展示或筛选。
* 数据模型要为后续作者分析、模板抽取和 RAG 检索保留扩展空间。

## Acceptance Criteria (evolving)

* [ ] 数据库模型和迁移能表达文案资产、拆解结果、审核结果、知识库、资产-知识库关系。
* [ ] 数据库模型能区分原始文案库、结构化拆解库、模板库、标签库、案例库、禁用库。
* [ ] 六个库都有最小可用的后端读写能力。
* [ ] 模板库、标签库、案例库、禁用库支持人工维护。
* [ ] 模板、标签、案例、禁用项支持保存来源引用，能追溯到原始文案或拆解结果。
* [ ] 后端提供统一的 `/api/knowledge/*` API，六类库各自有明确端点。
* [ ] 六类知识库端点都支持列表、创建、详情、更新、删除。
* [ ] 支持知识库集合 CRUD，并支持原始文案与多个集合的多对多关系。
* [ ] 原始文案列表/详情支持返回和筛选所属集合。
* [ ] CSV 导入成功后，资产和拆解结果写入 PostgreSQL，服务重启后仍可查询。
* [ ] 后端提供知识库列表/创建/详情或最小必要 API。
* [ ] 后端支持把文案资产关联到知识库。
* [ ] 现有 `GET /api/copy/assets`、`GET /api/copy/assets/{id}` 行为保持兼容。
* [ ] 后端测试覆盖持久化和知识库关联。
* [ ] 前端对接文档更新新增字段、端点和流程。

## Definition of Done

* Tests added/updated for backend persistence and knowledge base behavior.
* `python -m pytest` passes.
* `python -m compileall app scripts tests` passes.
* Alembic migration is included if database tables/columns change.
* Frontend integration documentation is updated.
* Rollback risk is documented if schema changes are non-trivial.

## Out of Scope (explicit)

* 本任务不实现完整 Milvus 向量索引。
* 本任务不实现高级 RAG rerank、embedding 批处理和召回评估。
* 本任务不要求 LLM 自动生成模板、标签、高表现原因或禁用表达。
* 本任务不改前端页面。
* 本任务不做多用户权限、团队协作或 SaaS 租户隔离。
* 本任务不做完整作者画像分析，只保留作者分析所需的基础数据结构。

## Technical Notes

* Inspected `app/models/copy.py`: existing `CopySource` / `CopyAnalysis` can be extended or replaced with richer relational model.
* Inspected `app/services/copy_assets.py`: current persistence path exists but mixes DB, Redis, and memory fallback; review status is metadata JSON.
* Inspected `app/rag/ingestion.py` and `app/rag/retriever.py`: RAG is currently a stub, so multiple knowledge bases should first be modeled in structured storage.
* Inspected `alembic/versions/`: no actual migration exists yet.
* Relevant docs: `doc/PRD.md`, `doc/FRONTEND_INTEGRATION.md`, `doc/SCHEMAS.md`.

## Decision (ADR-lite)

**Context**: 用户需要多个知识库支撑后续生成、检索、评审和复用，而不是单一文案表或单一向量索引。

**Decision**: MVP 采用“六个库都做最小可用”的后端方案：原始文案库、结构化拆解库、模板库、标签库、案例库、禁用库都建立持久化模型和基础 API；其中原始文案库和结构化拆解库接入 CSV 导入/LLM 拆解闭环，其他库先以人工维护为主。

**Consequences**: 数据边界会比只做文案资产更清晰，前端可以逐步接入不同库；代价是数据库迁移和 API 面会增加。自动抽取能力延后，避免本轮 LLM 流程过重。

## Decision (ADR-lite): Source Traceability

**Context**: 后续模板复用、案例分析、禁用表达治理和 RAG 检索都需要知道知识项来自哪条文案或哪次拆解。

**Decision**: 模板、标签、案例、禁用项都支持关联到原始文案或结构化拆解结果。来源引用不是展示必填项，但后端模型和 API 需要支持保存和返回。

**Consequences**: 数据模型需要支持跨库来源引用；实现比完全独立的字典表复杂，但能保留资产血缘，方便后续解释、筛选和回溯。

## Decision (ADR-lite): API Namespace

**Context**: 六类知识库需要长期维护，且前端由用户独立开发，API 命名需要清晰稳定。

**Decision**: 使用统一 `/api/knowledge/*` 命名空间，并为六类库提供独立资源端点。现有 `/api/copy/assets` 保持兼容，后续可作为文案资产旧入口或转发到原始文案/拆解库。

**Consequences**: API 数量增加，但每类资源的 schema 和前端页面边界更清楚。未来接 RAG、筛选和权限时，也能按库类型扩展。

## Decision (ADR-lite): CRUD Scope

**Context**: 前端后续会独立开发各知识库管理页，需要稳定、完整的后端资源操作。

**Decision**: 六类知识库本轮都提供列表、创建、详情、更新、删除能力。删除实现可以由后端选择软删除或硬删除，但 API 对前端表现为删除成功后列表不再显示。

**Consequences**: 后端测试和文档量增加，但前端不会因为缺少更新/删除能力卡住。

## Decision (ADR-lite): Collections

**Context**: 同一条原始文案可能同时用于不同业务集合，例如按行业、账号、表现类型或项目归档。

**Decision**: 增加知识库集合层，一条原始文案可以属于多个集合。集合是跨六类库之上的组织维度，MVP 至少支持原始文案与集合的多对多关系，并在 API 中提供集合 CRUD。

**Consequences**: 数据模型需要增加集合表和关联表；好处是后续可以按项目、账号、行业和用途复用同一资产，不需要复制文案。
