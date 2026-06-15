# Frontend Development Guidelines

> Conventions for the RagAgent React frontend (`frontend/`).

---

## Overview

The frontend is a **single-page React 19 + Vite + TypeScript** app styled with
**Tailwind CSS v3 + shadcn/ui** (green primary, light-only). It talks to the
FastAPI backend directly via a thin `lib/api.ts` layer. There is **no router** —
top-level view switching is done with React state.

These docs describe how the code is actually organized and the contracts new
code must follow, so future AI/dev sessions match existing patterns instead of
inventing new ones.

---

## Guidelines Index

| Guide | Description | Status |
|-------|-------------|--------|
| [Directory Structure](./directory-structure.md) | Where components, features, lib, and ui live | Active |
| [Component Patterns](./component-patterns.md) | State-up / props-down, dialogs, shared pieces | Active |
| [API Layer](./api-layer.md) | `lib/api.ts` fetch contract, error handling, types | Active |
| [Styling & UI Kit](./styling-ui-kit.md) | Tailwind theme, shadcn components, `cn`, `@/` alias | Active |

---

## Quick Reference

- Path alias: `@/` → `frontend/src/` (configured in both `tsconfig.json` and `vite.config.ts`).
- API base: `import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8002"`.
- Toasts via `sonner` (`Toaster` mounted in `main.tsx`); icons via `lucide-react`.
- Build gate: `npm run build` (= `tsc -b && vite build`) must pass; project is `strict`.
- No ESLint / no frontend unit-test framework currently — `tsc` + manual screenshot is the verification bar.

---

**Language**: Documentation in English; UI copy in Chinese (matches product).
