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

---

## Validation & Error Matrix (backend-driven)

| Condition | Backend | Frontend handling |
|---|---|---|
| Invalid/missing field | 422 (Pydantic) | `detail` → `toast.error` |
| Resource not found | 404 | `detail` → `toast.error` (except `fetchTask` → `null`) |
| Soft delete success | 204 (no body) | resolve void; remove row from local state |
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
