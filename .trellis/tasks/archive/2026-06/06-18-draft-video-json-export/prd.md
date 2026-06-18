# 草稿转视频处理 JSON

## Goal

在草稿工作台中，把已组好的草稿文案转换成后续视频处理可直接消费的严格 JSON。输出字段固定为 `title`、`title_break`、`description`、`script`、`tts_script`、`hashtags`，用于视频标题字幕、发布描述、字幕正文、TTS 配音和话题标签。

## What I Already Know

* 用户要求输出必须严格为 JSON，字段如下：
  * `title`: 2-16 字视频标题
  * `title_break`: 适合顶部标题字幕的自然换行版本
  * `description`: 10-100 字发布描述
  * `script`: 字幕正文，不含拼音标注，按自然段换行
  * `tts_script`: 配音正文，可少量使用多音字拼音标注
  * `hashtags`: 最多 5 个话题标签
* 功能入口来自草稿工作台的草稿正文。
* 现有草稿 API 位于 `/api/drafts/*`，草稿正文使用 `DraftDetail.current_text`。
* 现有前端约定：所有后端调用必须通过 `frontend/src/lib/api.ts`，类型放在 `frontend/src/lib/types.ts`。
* 现有项目已有 LLM 结构化输出、任务进度、诊断和草稿审批入库等模式，可复用这些约定。

## Requirements

* 后端提供一个草稿级转换接口，从 `draft_id` 读取当前草稿正文并生成视频处理 JSON。
* 转换结果需要落库，形成可回看的历史记录。
* 转换使用异步任务模式：前端创建任务后轮询进度，任务完成后返回历史记录 ID 和生成 JSON。
* 任务状态需要覆盖排队中、调用 LLM、校验结果、保存历史、失败/完成等阶段。
* 每次转换记录至少关联原草稿、保存生成的六字段 JSON、使用模型、创建时间和状态/错误信息。
* API 响应可以包含历史记录 ID、草稿 ID、模型、状态和时间等元信息。
* 前端复制或下载给视频处理流程使用的 JSON 必须只包含 `title`、`title_break`、`description`、`script`、`tts_script`、`hashtags` 六个业务字段。
* 接口返回严格结构化对象，而不是返回未解析的字符串。
* 后端 prompt 明确要求 LLM 只输出 JSON，并且服务层必须解析/校验后再返回。
* `script` 不允许拼音标注，按自然段换行。
* `tts_script` 允许少量多音字拼音标注。
* `hashtags` 最多 5 个。
* 前端从草稿工作台触发转换，并展示转换状态、模型信息和生成结果。

## Open Questions

* None.

## Acceptance Criteria

* [ ] 空草稿转换返回明确错误。
* [ ] LLM 返回多余文本或非法 JSON 时，后端返回可理解错误或进行一次受控修复重试。
* [ ] 成功响应字段包含约定 JSON 字段、历史记录 ID、草稿 ID、模型元信息和创建时间。
* [ ] 前端复制/下载的 JSON 只包含六个业务字段，不包含历史记录 ID、模型或状态。
* [ ] 转换历史重启后仍可查询。
* [ ] 任务进度可被前端轮询，并能显示当前阶段、模型信息和失败原因。
* [ ] 字段长度约束被后端校验。
* [ ] 前端不直接调用 `fetch`，只通过 `lib/api.ts`。
* [ ] 后端测试覆盖成功、空草稿、非法 LLM JSON、字段越界和历史查询场景。

## Definition of Done

* Tests added/updated.
* `python -m ruff check app tests alembic` passes.
* `python -m pytest tests` passes.
* `npm run build` passes if frontend is changed.
* Specs updated if a new public API contract is added.

## Out of Scope

* 直接调用视频剪辑、TTS 或字幕渲染服务。
* 多草稿批量转换。
* 复杂视频分镜、镜头脚本、时间轴生成。
* 把转换结果自动发布到外部平台。

## Decision Log

### 持久化策略

**Decision**: 采用“生成并落库为历史记录”。

**Reason**: 用户希望后续视频处理流程可追溯、可复用，不只是一次性复制结果。

**Consequence**: 需要新增数据库表、模型、迁移、查询接口和前端历史展示；实现范围比即时生成更大，但后续扩展更稳。

### 执行模式

**Decision**: 采用“异步任务 + 进度条”。

**Reason**: 用户希望看到 LLM 调用状态、使用模型和进度；该项目已有导入任务和任务轮询模式，复用后体验更一致。

**Consequence**: 需要新增任务入口、worker 执行函数、任务进度事件和历史记录落库；前端通过任务 ID 轮询结果。

### JSON 契约

**Decision**: API 响应允许携带元信息，但复制/下载给视频处理流程的 JSON 只包含六个业务字段。

**Reason**: 前端需要历史记录 ID、模型和状态来管理生成过程；后续视频处理流程需要干净、稳定、可直接消费的 JSON。

**Consequence**: 后端响应结构应采用包装对象，例如 `record_id`、`draft_id`、`model`、`created_at`、`result`；前端复制/下载时只取 `result`。

## Technical Notes

* Likely backend files: `app/api/routes/drafts.py`, `app/schemas/draft.py`, `app/services/drafts.py`, `app/core/llm.py`, `app/prompts/*`, `app/models/*`, `alembic/versions/*`.
* Likely frontend files: `frontend/src/lib/api.ts`, `frontend/src/lib/types.ts`, `frontend/src/features/drafts/DraftWorkbenchView.tsx`.
* Relevant specs: `.trellis/spec/backend/knowledge-api.md`, `.trellis/spec/frontend/api-layer.md`.
* Existing unrelated dirty files must be left untouched: `doc/RESTART_SERVICES.md`, `.idea/ai_debugger.xml`.
