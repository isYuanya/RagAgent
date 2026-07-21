# API Layer

> Contract for `lib/api.ts` — the single place that talks to the backend.

---

## Scope / Trigger

Any new backend call. Components must **never** call `fetch()` directly; add a
typed function to `lib/api.ts` instead.

---

## Base & types

```ts
export const apiBase =
  import.meta.env.VITE_API_BASE_URL ?? "";
```

Default calls are same-origin `/api/...` requests. In local development, Vite
proxies `/api` to the FastAPI backend (`http://127.0.0.1:8002`). Set
`VITE_API_BASE_URL` only when the frontend must call an absolute backend URL
directly.

- All response/request shapes are `export type` in `lib/types.ts`, **snake_case**
  (mirrors backend; no camelCase conversion layer).
- List responses use the generic `ListResponse<T> = { items: T[]; total; page; page_size }`.

---

## Function conventions

- One exported `async` function per endpoint; bare value params (not an options bag),
  except where a small object reads better (e.g. `updateRawCopy(id, { collection_ids })`).
- Return `Promise<ConcreteType>`. Legacy list fetchers may return `.items`, but
  views that display totals, pagination, or bulk operations must use explicit
  `fetch*Page` wrappers that return the full `ListResponse<T>` envelope.
- Chinese error messages (surfaced via `toast`).

---

## Error handling (two shapes)

**Read (GET)** — throw a generic Chinese message on non-ok:

```ts
export async function fetchCollections(): Promise<KnowledgeCollection[]> {
  const response = await fetch(`${apiBase}/api/knowledge/collections?page=1&page_size=100`);
  if (!response.ok) throw new Error("加载集合失败");
  const payload = (await response.json()) as ListResponse<KnowledgeCollection>;
  return payload.items;
}
```

**Write (POST/PATCH)** — `parseJson` (swallows JSON errors) then prefer backend `detail`:

```ts
const payload = await parseJson(response);
if (!response.ok) throw new Error((payload?.detail as string) ?? "保存失败");
```

**Delete (204)** — only check `ok`; never parse a body on success:

```ts
async function deleteResource(url: string, fallback: string): Promise<void> {
  const response = await fetch(url, { method: "DELETE" });
  if (!response.ok) {
    const payload = await parseJson(response);
    throw new Error((payload?.detail as string) ?? fallback);
  }
}
```

Shared helpers `parseJson`, `writeJson`, `deleteResource` already exist — reuse them.

**Exception**: `fetchTask` returns `null` on 404 (polling), instead of throwing.

## Async task endpoints

Some backend actions create a `TaskResponse` and finish later, then expose their
typed result through `GET /api/tasks/{task_id}`. Frontend code should keep the
endpoint-specific request/accept functions in `lib/api.ts`, reuse `fetchTask`
for polling, and parse `task.result` in the feature component before rendering.

Keyword crawler progress uses the same `TaskResponse.progress.percent` field as
the visible progress bar. The frontend must not rescale crawler percentages by
phase. If the backend says `current_message = "已滚动 8/20 次..."` and
`percent = 40`, the bar and number both show `40%`; processing-video progress
follows the same visible ratio rule.

## Scenario: Frontend API Base and Dev Proxy

### 1. Scope / Trigger

- Trigger: any change to `frontend/src/lib/api.ts`, `frontend/vite.config.ts`,
  API deployment wiring, or local backend port assumptions.

### 2. Signatures

```ts
export const apiBase = import.meta.env.VITE_API_BASE_URL ?? "";
```

Vite dev proxy:

```ts
server: {
  proxy: {
    "/api": "http://127.0.0.1:8002"
  }
}
```

### 3. Contracts

- Default API calls are same-origin `/api/...`.
- Local dev routes `/api/...` through the Vite proxy to FastAPI on `8002`.
- `VITE_API_BASE_URL` is optional and only needed when the frontend must call an
  absolute backend origin directly.
- API wrapper functions must keep endpoint paths as `${apiBase}/api/...`.

### 4. Validation & Error Matrix

| Condition | Expected behavior |
|---|---|
| Backend running on `8002` and Vite running on `5173` | `GET http://localhost:5173/api/drafts` returns 200 |
| `VITE_API_BASE_URL` is unset | Browser requests `/api/...` on the frontend origin |
| `VITE_API_BASE_URL` is set | Browser requests `${VITE_API_BASE_URL}/api/...` |
| Vite proxy points to the wrong port | Workbench may show browser-level `Failed to fetch` or proxy errors |

### 5. Good/Base/Bad Cases

- Good: draft workbench calls `fetchDrafts()`, which requests `/api/drafts` in
  dev and lets Vite proxy it to `8002`.
- Base: production-like deployments set `VITE_API_BASE_URL` when no same-origin
  reverse proxy exists.
- Bad: hardcode `http://127.0.0.1:8002` inside feature components or individual
  API functions.

### 6. Tests Required

- `npm run build` must pass.
- With backend running, `Invoke-WebRequest http://localhost:5173/api/drafts
  -UseBasicParsing` must return 200.

### 7. Wrong vs Correct

#### Wrong

```ts
await fetch("http://127.0.0.1:8002/api/drafts");
```

#### Correct

```ts
await fetch(`${apiBase}/api/drafts`);
```

Current task-backed contracts:

| Feature | Create endpoint | Result consumer | Follow-up endpoint |
|---|---|---|---|
| Copy import | `POST /api/copy/import` | import progress panel | refresh assets |
| Draft next sentence | `POST /api/recommendations/next-sentence` | draft recommendation panel | `POST /api/recommendations/accepted` |

### Knowledge list totals and bulk actions

Knowledge views that need true totals must call typed API wrappers instead of
deriving counts from loaded rows:

```ts
fetchKnowledgeStats(): Promise<KnowledgeStatsResponse>
fetchCollectionsPage(page, pageSize): Promise<ListResponse<KnowledgeCollection>>
fetchRawCopiesPage(collectionId, page, pageSize): Promise<ListResponse<RawCopySummary>>
fetchAnalysesPage(page, pageSize): Promise<ListResponse<AnalysisSummary>>
fetchTemplatesPage(page, pageSize): Promise<ListResponse<KnowledgeTemplate>>
fetchFragmentsPage(filters, page, pageSize): Promise<ListResponse<KnowledgeFragment>>
previewBulkDeleteRawCopies(body): Promise<BulkOperationResponse>
bulkDeleteRawCopies(body): Promise<BulkOperationResponse>
previewBulkDeleteFragments(body): Promise<BulkOperationResponse>
bulkDeleteFragments(body): Promise<BulkOperationResponse>
```

Bulk delete UI must preview `matched_count` first, show a destructive
confirmation, then call the confirmed endpoint and refresh both the current list
and `fetchKnowledgeStats()`.

Fragment bulk delete UI must require at least one active filter before enabling
"select all filtered results" or "delete filtered results"; never let an empty
filter payload represent "delete the whole fragment library".

### Draft next-sentence recommendation

Request type mirrors backend snake_case fields:

```ts
type NextSentenceRecommendationRequest = {
  draft_id: string;
  candidate_count?: number; // 1..5
  cursor_item_id?: string | null;
  q?: string | null;
  metadata?: Record<string, unknown>;
};
```

The create function returns `TaskResponse`, not the final candidate list:

```ts
createNextSentenceRecommendation(body): Promise<TaskResponse>
```

When `TaskResponse.status === "finished"`, parse `task.result` as
`NextSentenceRecommendationResult`. The accept endpoint returns the updated
`DraftDetail`, and the UI must replace local draft state with `response.draft`.

Validation and error behavior:

| Condition | Backend | Frontend handling |
|---|---|---|
| `candidate_count` outside 1..5 | 422 | backend `detail` -> toast |
| draft missing | 404 | backend `detail` -> toast |
| recommendation task still running when accepting | 404 | backend `detail` -> toast |
| accepted successfully | 200 | replace draft with returned `draft` |

---

## Validation & Error Matrix (backend-driven)

| Condition | Backend | Frontend handling |
|---|---|---|
| Invalid/missing field | 422 (Pydantic) | `detail` → `toast.error` |
| Resource not found | 404 | `detail` → `toast.error` (except `fetchTask` → `null`) |
| Soft delete success | 204 (no body) | resolve void; remove row from local state |
| Repeated delete after a row was already removed | 404 | the owning view treats it as already deleted, removes the local row, and avoids surfacing raw backend English |
| LLM config/parse failure (copy) | 502 / 503 | `detail` → `toast.error` |

---

## Wrong vs Correct

**Wrong** — fetch inside a component, no typed contract:
```tsx
const r = await fetch("http://127.0.0.1:8002/api/knowledge/collections");
const data = await r.json(); // untyped, no error handling, hardcoded base
```

**Correct** — call the typed api function:
```tsx
import { fetchCollections } from "@/lib/api";
try { setCollections(await fetchCollections()); }
catch (e) { toast.error(e instanceof Error ? e.message : "加载集合失败"); }
```

---

## Tests Required

No frontend unit-test framework currently. The bar is:
- `npm run build` (`tsc -b && vite build`) passes — confirms types match contracts.
- Manual: screenshot the view against a running backend (`:8002`), confirm Network
  hits `/api/...` and CORS is OK. When backend is absent/stale, the view must
  degrade to the empty state, not crash.

---

## Scenario: Smart Composition Assistant API Layer

### 1. Scope / Trigger

- Trigger: frontend work that touches the smart composition assistant view or `/api/assistant/*` calls.
- All calls must go through `frontend/src/lib/api.ts`; all response/request shapes live in `frontend/src/lib/types.ts`.

### 2. Signatures

```ts
fetchSmartCompositionOptions(): Promise<SmartCompositionOptions>
prefillSmartCompositionBrief(text: string): Promise<SmartCompositionBriefPrefillResponse>
createSmartCompositionRun(body: SmartCompositionRunCreate): Promise<SmartCompositionRunDetail>
fetchSmartCompositionRuns(): Promise<SmartCompositionRunSummary[]>
fetchSmartCompositionRun(id: string): Promise<SmartCompositionRunDetail>
confirmSmartCompositionMaterials(runId, body): Promise<SmartCompositionRunDetail>
confirmSmartCompositionCandidate(runId, body): Promise<SmartCompositionRunDetail>
confirmSmartCompositionRewrite(runId, body): Promise<SmartCompositionRunDetail>
```

### 3. Contracts

- The view should default to `mode: "auto"` because the product direction is one-click completion.
- `mode: "guided"` is valid but currently stops at `waiting_for_user`; do not show that as an error.
- Progress UI must use `run.timeline`; do not infer progress from draft ids.
- Guided UI decides which confirmation panel to render from `run.metadata.pending_interrupt.type`.
- Confirmation payloads are selection-only; do not send edited candidate or rewrite text in MVP.
- Final preview should use `run.result.draft.current_text`.
- Model display can use `timeline[].model`, `result.composition.model`, and `result.diagnosis.model`.
- Selection explanation should render `result.composition_selection` and `result.rewrite_selection`.

### 4. Validation & Error Matrix

| Condition | Backend | Frontend handling |
|---|---|---|
| Invalid brief | 422 | backend detail -> toast |
| LLM prefill parse failure | 422 | backend detail -> toast |
| Missing workflow run | 404 | backend detail -> toast |
| Guided waiting state | 200 `waiting_for_user` | show waiting/confirm state, not error |
| Confirm called at wrong checkpoint | 409 | backend detail -> toast |
| Unknown selected id | 422 | backend detail -> toast |
| Auto finished | 200 `finished` | show final draft preview and version ids if needed |

### 5. Good/Base/Bad Cases

- Good: user fills selection-first form, clicks one button, sees completed timeline and final text.
- Good: guided user confirms materials, then candidate, then rewrite through typed API functions.
- Good: user opens a recent workflow run from history and sees the same persisted state.
- Base: no history exists; show empty state.
- Bad: component fetches `/api/assistant/*` directly instead of calling `lib/api.ts`.
- Bad: component hardcodes backend base URL.

### 6. Tests Required

- `npm run build` must pass.
- When backend tests are run, `tests/test_smart_composition_api.py` must pass.

### 7. Wrong vs Correct

#### Wrong

```tsx
await fetch("http://127.0.0.1:8002/api/assistant/runs", { method: "POST" });
```

#### Correct

```tsx
const run = await createSmartCompositionRun({ mode, brief });
setSelectedRun(run);
```

## Scenario: Draft Approval API Layer

### 1. Scope / Trigger

- Trigger: frontend work that touches draft approval from the draft workbench.
- All draft approval calls must go through `frontend/src/lib/api.ts`.

### 2. Signatures

```ts
approveDraft(id: string): Promise<DraftApprovalResponse>
```

Response shape:

```ts
type DraftApprovalResponse = {
  draft: DraftDetail;
  raw_copy: CopyAsset;
  fragment_extraction: FragmentExtractionResult;
};
```

### 3. Contracts

- UI copy says `审批通过`, while the backend draft status remains `ready`.
- The draft workbench must replace local draft state with `response.draft` after approval.
- The button should be disabled for archived drafts, already-ready drafts, empty current text, and in-flight approval.
- The success toast may summarize `fragment_extraction.status` and `fragment_count`.

### 4. Validation & Error Matrix

| Condition | Backend | Frontend handling |
|---|---|---|
| Missing draft | 404 | backend detail -> toast |
| Empty draft text | 409 | backend detail -> toast |
| Approval success | 200 | refresh detail/list from returned draft |
| Existing fragments | 200 `fragment_extraction.status = skipped` | show success without duplicate warning |

### 5. Tests Required

- `npm run build` must pass.
- Backend `tests/test_drafts_api.py` must cover the endpoint behavior.

## Scenario: Draft Video JSON Export API Layer

### 1. Scope / Trigger

- Trigger: frontend work that touches video-processing JSON generation from the draft workbench.
- All draft video export calls must go through `frontend/src/lib/api.ts`.

### 2. Signatures

```ts
createDraftVideoExport(id: string): Promise<TaskResponse>
fetchDraftVideoExports(id: string): Promise<DraftVideoExportRecord[]>
```

Backend endpoints:

```text
POST /api/drafts/{draft_id}/video-exports
GET  /api/drafts/{draft_id}/video-exports?page=1&page_size=20
GET  /api/tasks/{task_id}
```

### 3. Contracts

- Generation is asynchronous and uses the shared task polling contract.
- The UI must show task progress, model, success, and failure state from `TaskResponse.progress`.
- `TaskResponse.result` is a `DraftVideoExportRecord` when finished.
- `DraftVideoExportRecord.result` is the strict downstream video-processing JSON.
- Copy/download actions must serialize only `DraftVideoExportRecord.result`, not wrapper fields like `id`, `draft_id`, `model`, or timestamps.
- The workbench may show record metadata for human traceability.
- `hashtags` values are plain topic strings without `#`; the workbench may display them comma-separated for readability, but copied/downloaded JSON keeps the `hashtags: string[]` array.

### 4. Validation & Error Matrix

| Condition | Backend | Frontend handling |
|---|---|---|
| Missing draft | 404 | backend detail -> toast |
| Empty draft text | task `failed` | show task error toast |
| LLM invalid JSON | task `failed` | show task error toast; history remains unchanged |
| Generation success | task `finished` | refresh history and select the new record |
| History load failure | non-ok response | toast and show empty history area |

### 5. Good/Base/Bad Cases

- Good: user clicks generate, sees progress/model, then copies a six-field JSON payload.
- Good: hashtag display reads like `贷款, 征信空白`, while the copied JSON remains `["贷款", "征信空白"]`.
- Good: existing history loads when switching back to a draft.
- Base: no history exists; show an empty state without blocking draft editing.
- Bad: component directly calls `fetch("/api/drafts/.../video-exports")`.
- Bad: copy/download includes wrapper metadata and breaks the later video processing pipeline.

### 6. Tests Required

- `npm run build` must pass.
- Backend `tests/test_drafts_api.py` must cover task success, history persistence, and invalid LLM JSON.

### 7. Wrong vs Correct

#### Wrong

```tsx
await navigator.clipboard.writeText(JSON.stringify(record));
```

#### Correct

```tsx
await navigator.clipboard.writeText(JSON.stringify(record.result, null, 2));
```

The API wrapper is for the workbench; `record.result` is the strict video-processing payload.
