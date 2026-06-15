# 知识库前端功能实现计划

## Context

后端新增了统一知识库命名空间 `/api/knowledge`（见 `doc/FRONTEND_INTEGRATION.md` 第 7 节、`doc/SCHEMAS.md` 第 7 节），提供集合 + 6 类库的完整 CRUD。当前前端只有「文案资产审核工作台」单页，没有任何知识库 UI。文档明确建议「新页面优先接入知识库 API」。

本次实现**核心三库**：集合（collections）、原始文案库（raw-copies）、结构化拆解库（analyses），采用**侧边栏本地视图切换**（不引 react-router，用 App 顶层 state）。目标是让用户能管理集合、浏览 CSV 导入沉淀的原始文案与拆解结果、并归类到集合。

## 决策（已与用户确认）

- 范围：核心三库（集合 / 原始文案库 / 拆解库），其余 4 类库（模板/标签/案例/禁用）本期不做。
- 页面接入：侧边栏本地视图切换，不引路由。
- 三库内切换：**顶部 segmented 按钮**（复用现有 Button，不加 tabs 依赖）。
- 集合：完整 CRUD（增删改）。
- 原始文案库：浏览 + 改所属集合 + 删除，**手工新建暂缓**。
- 拆解库：**只读浏览 + 删除**。
- 改集合 UI：可 toggle 的 Badge 网格（多选）。
- 默认：首页 `page_size=100`（同现有 `fetchAssets`，分页器后做）；metrics 只读展示；不暴露 metadata UI。

## 后端契约要点（base `http://127.0.0.1:8002`，前缀 `/api`）

- **collections**：`GET/POST /api/knowledge/collections`（仅分页），`GET/PATCH/DELETE /{id}`，DELETE→204。Create：`name`(必填) / `description?` / `metadata={}`。
- **raw-copies**：`GET /api/knowledge/raw-copies?page&page_size&collection_id`（**只有 collection_id 筛选**），`POST/GET/PATCH/DELETE`。Response 继承 copy asset 全字段 + `collection_ids: string[]` + `collections: KnowledgeCollection[]`。
- **analyses**：`GET /api/knowledge/analyses?page&page_size`（仅分页），`POST/GET/PATCH/DELETE`。Response：`id` / `raw_copy_id` / `auto_analysis?` / `reviewed_analysis?` / `status`。
- 关联：`raw_copy.id == copy_asset.id`；CSV 导入产物自动出现在 raw-copies 与（已分析的）analyses 中。
- 错误：404 / 422；写操作错误体含 `detail`。CORS 已放行 localhost/127 任意端口。

## 新增依赖

- `@radix-ui/react-dialog` —— CRUD 对话框。其余复用现有依赖。

## 实现步骤

### 步骤 0 — 依赖与 dialog 组件
- `npm i @radix-ui/react-dialog`。
- 新增 `frontend/src/components/ui/dialog.tsx`（shadcn 标准封装，复用现有 `cn`）。

### 步骤 1 — types 与 api
- 编辑 `frontend/src/lib/types.ts`，追加（沿用 `export type` + snake_case + `?: T|null`）：
  - `KnowledgeCollection` / `KnowledgeCollectionCreate`
  - `RawCopySummary = CopyAsset & { collection_ids: string[]; collections: KnowledgeCollection[] }`
  - `AnalysisSummary = { id; raw_copy_id; auto_analysis?: Analysis|null; reviewed_analysis?: Analysis|null; status: string }`
  - 通用 `ListResponse<T> = { items: T[]; total; page; page_size }`
  - 复用现有 `Analysis` / `CopyAsset` / `emptyAnalysis`。
- 编辑 `frontend/src/lib/api.ts`，追加（沿用现有两套写法：GET 抛中文错误；写操作 `parseJson` + `detail`；DELETE 仅判 `ok`）：
  - collections：`fetchCollections / createCollection / updateCollection / deleteCollection`
  - raw-copies：`fetchRawCopies({collectionId?}) / updateRawCopy / deleteRawCopy`
  - analyses：`fetchAnalyses / deleteAnalysis`

### 步骤 2 — 视图切换骨架
- 编辑 `frontend/src/features/Sidebar.tsx`：`SidebarItem` 由装饰 `<div>` 改受控 `<button onClick>`；新增 `view` + `onChangeView` props；导航改为「审核工作台 / 知识库」两项，`active` 由 `view===value` 决定；保留底部统计卡。
- 编辑 `frontend/src/App.tsx`：加 `view: "workbench" | "knowledge"` state；现有工作台 JSX/state/逻辑**原样保留**，外层条件渲染 `view==="workbench" ? 现有 main : <KnowledgeView/>`。
- 新增 `frontend/src/features/knowledge/KnowledgeView.tsx`：容器，持 `kbTab` + segmented control；进入时加载一次 `collections`（三库共享，CRUD 后刷新），下传子 Panel。

### 步骤 3 — 集合库（完整 CRUD）
- 新增 `features/knowledge/CollectionsPanel.tsx`：Card 列表（name/description/编辑/删除）+ 空态。
- 新增 `features/knowledge/CollectionDialog.tsx`：create/edit 共用（传入 collection 即编辑），复用 dialog + Input/Textarea/Label/Button。
- 新增 `features/knowledge/ConfirmDialog.tsx`：destructive 删除确认，三库共用。
- 成功后 `toast.success` + 刷新 collections。

### 步骤 4 — 只读 AnalysisView 抽取
- 新增 `features/knowledge/AnalysisView.tsx`：把 `ReviewPanel` 的展示部分（原文卡片 + 字段网格）抽成**只读**组件（props：`analysis` + 可选 `asset`）。
- **不改 `ReviewPanel`**（保持其为可编辑工作台，避免回归），供 RawCopyDetail 与 AnalysesPanel 复用。

### 步骤 5 — 原始文案库（浏览 + 改集合 + 删除）
- 新增 `features/knowledge/RawCopiesPanel.tsx`：顶部集合筛选（复用 `Select` + `__all__` 哨兵），按 `collectionId` 服务端筛选；左列复用 AssetRow 视觉，右列详情。
- 新增 `features/knowledge/RawCopyDetail.tsx`：只读详情，渲染 `reviewed_analysis ?? auto_analysis`（用 AnalysisView），展示所属集合 Badge。
- 改集合：对话框 + 可 toggle 的 Badge 网格 → `updateRawCopy(id, { collection_ids })`。
- 删除 → ConfirmDialog。

### 步骤 6 — 拆解库（只读 + 删除）
- 新增 `features/knowledge/AnalysesPanel.tsx`：列表行展示 `raw_copy_id` 截断 + `StatusBadge`（复用 `StatusBadge`/`STATUS_LABELS`）；详情用 AnalysisView；删除 → ConfirmDialog。

### 步骤 7 — 收尾
- 错误统一 `toast.error(err.message)`；loading 用 Skeleton；空态用共享 EmptyState（可复用 AssetList 内现有空态思路，必要时抽到 `features/shared`）。
- `npm run build` 通过。

## 组件树

```
App (view state)
├─ Sidebar(view, onChangeView)
└─ workbench ? 现有 main (CsvUpload/AssetList/ReviewPanel)
   : KnowledgeView (kbTab + collections)
      ├─ Segmented control: 集合 | 原始文案 | 拆解
      ├─ CollectionsPanel → CollectionDialog / ConfirmDialog
      ├─ RawCopiesPanel → RawCopyDetail→AnalysisView / EditCollectionsDialog / ConfirmDialog
      └─ AnalysesPanel → AnalysisView / ConfirmDialog
新增共享 ui: dialog.tsx
复用 ui: button/input/textarea/label/select/badge/card/skeleton
```

## 验证

1. 后端跑在 `127.0.0.1:8002`；前端 `cd frontend && npm i && npm run build`（`tsc -b && vite build`）必须通过。
2. 启 `npm run preview`，用 Edge headless 截图确认渲染（同上次重写验证方式）。
3. 点测：
   - 侧栏切到知识库 → 三 tab 可切、列表能载。
   - 集合：新建（空 name → 422 → toast）/ 编辑 / 删除（204 行消失）。
   - 先 CSV 导入产生数据 → raw-copies 出现产物；按集合筛选；看只读详情；改集合后 Badge 更新；删除。
   - analyses 出现已分析产物；只读详情；删除；核对 `analysis.raw_copy_id` 能对回 raw-copy。
   - 网络面板确认命中 `/api/knowledge/...`，CORS 正常。

## 风险与不做项

- 风险：`AssetRow`/空态先**复制**到知识库再视情况抽取，降低对现有工作台的回归风险；`AnalysisView` 抽取需确保 ReviewPanel 行为不变。
- 不做（本期外）：react-router、分页器、raw-copy 手工新建、metrics 编辑器、metadata UI、移动端导航、模板/标签/案例/禁用 4 类库。

## Trellis 流程说明

本前端任务应作为**独立新任务**走 Trellis 流程（现有 active task `copy-persistence-knowledge-bases` 是另一个 codex 会话的后端持久化任务，与此前端任务不同）。批准本计划后：创建任务 → 走 brainstorm 固化 prd（本计划即可作为 prd 基础）→ curate jsonl → `task.py start` → 实现 → trellis-check → 提交。
