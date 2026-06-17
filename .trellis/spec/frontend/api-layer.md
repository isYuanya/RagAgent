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
  import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8002";
```

- All response/request shapes are `export type` in `lib/types.ts`, **snake_case**
  (mirrors backend; no camelCase conversion layer).
- List responses use the generic `ListResponse<T> = { items: T[]; total; page; page_size }`.

---

## Function conventions

- One exported `async` function per endpoint; bare value params (not an options bag),
  except where a small object reads better (e.g. `updateRawCopy(id, { collection_ids })`).
- Return `Promise<ConcreteType>`; list fetchers return `.items` (callers rarely need the envelope).
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

Current task-backed contracts:

| Feature | Create endpoint | Result consumer | Follow-up endpoint |
|---|---|---|---|
| Copy import | `POST /api/copy/import` | import progress panel | refresh assets |
| Draft next sentence | `POST /api/recommendations/next-sentence` | draft recommendation panel | `POST /api/recommendations/accepted` |

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
```

### 3. Contracts

- The view should default to `mode: "auto"` because the product direction is one-click completion.
- `mode: "guided"` is valid but currently stops at `waiting_for_user`; do not show that as an error.
- Progress UI must use `run.timeline`; do not infer progress from draft ids.
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
| Auto finished | 200 `finished` | show final draft preview and version ids if needed |

### 5. Good/Base/Bad Cases

- Good: user fills selection-first form, clicks one button, sees completed timeline and final text.
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
