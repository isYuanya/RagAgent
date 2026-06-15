# 重写前端页面 UI（Tailwind + shadcn/ui）

## Goal

当前前端是纯手写 CSS 的单文件 React 应用（`frontend/src/main.tsx` + `styles.css`），视觉偏旧、配色撞色（青绿 + 黄）、信息层次一般。目标是在**不改变后端契约和现有功能**的前提下，用 Tailwind CSS + shadcn/ui 重写界面，做到现代简洁（中性灰 + 单一主色），并优化布局与信息架构。

## What I already know

- 技术栈：React 19 + Vite 6 + TypeScript（strict），图标用 `lucide-react`。
- 前端仅两个核心文件：`frontend/src/main.tsx`（420 行单文件 App）、`frontend/src/styles.css`（400 行手写 CSS）。
- API 通过 `apiBase`（`VITE_API_BASE_URL ?? "http://127.0.0.1:8002"`）直连后端，**不走 vite proxy**（proxy 配的是 :8000，实际未用）。
- 现有功能（全部需保留）：
  1. CSV 上传 → `POST /api/copy/import` → 轮询 `GET /api/tasks/{id}` 展示进度（阶段/模型/成功失败数/百分比进度条）。
  2. 行级错误展示。
  3. 资产列表 `GET /api/copy/assets?page=1&page_size=100`（主题/作者/平台/行业/状态徽章）。
  4. 详情 + 校正表单：主题、目标用户、核心痛点、开头钩子、情绪按钮、内容结构、表达技巧、适用场景、可复用模板、置信度、审核状态。
  5. 保存 `PATCH /api/copy/assets/{id}/review`。
- 数据类型（`Analysis` / `CopyAsset` / `TaskProgress` / `TaskResponse`）已在 main.tsx 定义，重写时复用。

## Decisions (locked)

- **UI 方案**：Tailwind CSS + shadcn/ui。
- **视觉风格**：现代简洁，中性灰 (zinc) 打底 + **绿色主色**（primary 用 emerald/green 系，作为点缀，不大面积铺色）。
- **暗色模式**：不做，**仅亮色**。
- **布局**：优化布局 + 美化（不只是换皮）。
- **代码组织**：拆分多文件——`src/components/`（shadcn 原子组件）+ `src/features/`（AssetList / ReviewPanel / ImportProgress / CsvUpload 等区块）+ `src/lib/`（types、api、utils）+ 精简的 `App.tsx`。

## Assumptions (temporary)

- 后端 API 契约完全不变，纯前端改造。
- 保持单页应用，不引入路由库（侧边栏导航当前是装饰性的）。
- 复用现有数据类型定义与 fetch 逻辑，仅重构 UI 层与组件拆分。

## Open Questions

（已全部收敛）

## Requirements (final)

- 引入 Tailwind + shadcn/ui 工具链（tailwind.config、postcss、CSS 变量主题、`cn` 工具、`components.json`），主色绿色、仅亮色。
- 用 shadcn 组件重建：按钮、输入框、文本域、下拉选择、徽章、卡片、进度条、Toast、骨架屏等。
- 重做布局与信息架构：保留侧边栏（品牌 + 静态信息，**去掉死链接假导航**），主区为「列表 + 详情校正」两栏。
- **列表筛选栏**：列表顶部加筛选（平台 / 行业 / 审核状态），**前端本地筛选**已加载的资产（不改后端、不加分页接口）。
- **体验细节**：
  - 空状态插画/提示（无资产时）。
  - 加载骨架屏（首次加载资产列表时）。
  - 保存成功/失败、导入完成/失败用 **Toast** 提示（替代现有 inline message）。
- 功能与 API 调用零回归。

## Acceptance Criteria (final)

- [ ] `npm run build`（tsc -b && vite build）通过。
- [ ] 所有现有功能可用：CSV 导入、进度轮询、行级错误、列表、详情校正、保存审核。
- [ ] 视觉为现代简洁绿色主色，无旧的青绿+黄撞色。
- [ ] 列表筛选栏可按平台/行业/状态本地过滤。
- [ ] 空状态、骨架屏、Toast 正常工作。
- [ ] 窄屏响应式不破版。

## Definition of Done

- 前端构建通过（tsc -b && vite build）。
- 无功能回归，API 调用与数据流不变。
- 代码组织清晰（组件合理拆分）。
- 旧的 `styles.css` 中无用样式清理。

## Out of Scope

- 后端任何改动。
- 新增功能（筛选、分页 UI、路由、多页面）—— 除非明确加入。
- 真正的暗色模式（除非确认需要）。

## Technical Notes

- vite proxy 与 apiBase 不一致是既有现象，本任务不修复（保持现状）。
- React 19 + shadcn/ui 需确认兼容性（shadcn 基于 Radix，React 19 已支持）。
