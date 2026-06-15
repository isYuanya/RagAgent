# Directory Structure

> How frontend code is organized under `frontend/src/`.

---

## Layout

```
frontend/src/
├── main.tsx              # thin entry: ReactDOM.createRoot + <App/> + <Toaster/>
├── App.tsx               # top-level state + layout; view switching (no router)
├── styles.css            # Tailwind directives + green theme CSS variables
├── lib/
│   ├── types.ts          # all shared `export type` definitions (snake_case)
│   ├── api.ts            # all backend fetch functions (apiBase + helpers)
│   └── utils.ts          # cn(), formatters (formatMetrics/formatFollowers), phaseLabel, splitLines
├── components/ui/        # shadcn primitives ONLY (button, input, dialog, select, ...)
└── features/             # app-specific feature blocks
    ├── <Block>.tsx       # workbench blocks (AssetList, ReviewPanel, Sidebar, ...)
    ├── shared/           # cross-feature reusable pieces (EmptyState, ConfirmDialog)
    └── knowledge/        # one feature area = one subfolder (KnowledgeView + panels + dialogs)
```

---

## Where things go

| Putting in... | Goes to |
|---|---|
| A generic shadcn primitive (no app logic) | `components/ui/` |
| A piece reused across 2+ feature areas | `features/shared/` |
| A self-contained feature with several panels/dialogs | `features/<area>/` subfolder |
| A shared TS type | `lib/types.ts` (never inline-duplicate across files) |
| A backend call | `lib/api.ts` (never `fetch()` directly in a component) |
| A formatter / class helper | `lib/utils.ts` |

---

## Conventions

- **One feature area = one subfolder** under `features/` (e.g. `knowledge/`). The
  area's container component (e.g. `KnowledgeView.tsx`) owns shared data and
  renders its panels.
- **`components/ui/` is for shadcn primitives only** — no business logic, no API
  calls, no app types. App-specific composites live in `features/`.
- **Promote, don't duplicate**: if a presentational helper (empty state, skeleton
  row, confirm dialog) is needed in a second place, move it to `features/shared/`
  and have the first place import it too. Example: `EmptyState` was extracted from
  `AssetList.tsx` into `features/shared/EmptyState.tsx` and both consumers import it.

---

## Imports

- Always use the `@/` alias for cross-directory imports: `@/components/ui/button`,
  `@/lib/api`. Relative imports are fine within the same folder (`./StatusBadge`).
- `@/` resolves in **both** `tsconfig.json` (`paths`) and `vite.config.ts`
  (`resolve.alias`) — keep them in sync if changed.
