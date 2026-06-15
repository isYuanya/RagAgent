# Styling & UI Kit

> Tailwind theme, shadcn/ui usage, and styling conventions.

---

## Stack

- **Tailwind CSS v3** + **shadcn/ui** (Radix-based primitives).
- **Light theme only**, **green primary** (emerald/green). `darkMode: ["class"]`
  is configured but no dark theme is shipped — don't add dark variants ad hoc.
- `tailwindcss-animate` plugin enabled (used by dialog/select animations).

---

## Theme tokens

Colors are HSL CSS variables in `src/styles.css` (`:root`), referenced by
`tailwind.config.js` as `hsl(var(--token))`. Use **semantic classes**, not raw colors:

| Use | Class |
|---|---|
| Page / card surfaces | `bg-background`, `bg-card`, `bg-muted` |
| Primary action | `bg-primary text-primary-foreground` |
| Subtle accent (selected, hover) | `bg-accent text-accent-foreground` |
| Destructive | `text-destructive`, `variant="destructive"` |
| Borders | `border-border` |
| Secondary text | `text-muted-foreground` |

**Don't** hardcode hex colors or the old teal/yellow palette — the rewrite removed it.

---

## shadcn components

Live in `components/ui/`. Currently available: `button` (cva: variant
default/destructive/outline/secondary/ghost/link, size default/sm/lg/icon,
`asChild`), `input`, `textarea`, `label`, `select`, `badge` (variant
default/secondary/destructive/success/muted/outline), `card`, `progress`,
`skeleton`, `dialog`.

- Compose UIs from these primitives; don't restyle native elements by hand.
- Adding a new shadcn primitive: drop the standard shadcn file into
  `components/ui/`, reuse `cn` from `@/lib/utils`, and add its Radix dep to
  `package.json` (e.g. `@radix-ui/react-dialog`).

---

## `cn` helper

Merge classes with `cn` (clsx + tailwind-merge) from `@/lib/utils` — never string-concat
className conditionals manually.

```tsx
className={cn(
  "w-full rounded-lg border p-3",
  active && "border-primary bg-accent/60 ring-1 ring-primary/20"
)}
```

---

## Layout conventions

- App shell: `flex min-h-screen`; sidebar `hidden lg:flex` (desktop tool, no mobile nav).
- Two-pane list/detail: `grid lg:grid-cols-[minmax(320px,420px)_1fr]` with each pane a `Card`
  using `flex min-h-0 flex-col overflow-hidden` so inner lists scroll independently.
- Selected list row: green border + `bg-accent/60` + `ring-1 ring-primary/20`.

---

## Conventions recap

- Light-only, green primary, semantic tokens, `cn` for conditionals, `@/` alias imports.
- UI copy is Chinese; code identifiers and these docs are English.
