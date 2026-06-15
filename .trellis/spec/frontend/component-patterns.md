# Component Patterns

> How feature components are structured and wired.

---

## State-up / props-down

Feature components are **presentational and controlled**. State is lifted to a
container (`App.tsx` or a feature container like `KnowledgeView.tsx`) and passed
down via props; children raise events through callbacks. Children only hold
*local UI* state (a form draft, a filter, a dialog open flag).

```tsx
// container owns data + actions
<AssetList
  assets={assets}
  loading={listLoading}
  selectedId={selectedId}
  onSelect={setSelectedId}
/>
<ReviewPanel asset={selected} saving={saving} onSave={handleSave} />
```

**Why**: keeps data flow one-directional and makes panels reusable across views.

---

## View switching (no router)

There is no routing library. Top-level navigation is a `view` state in `App.tsx`,
driven by a controlled `Sidebar`:

```tsx
const [view, setView] = React.useState<AppView>("workbench");
<Sidebar view={view} onChangeView={setView} assetCount={assets.length} />
{view === "knowledge" ? <KnowledgeView /> : (/* workbench main */)}
```

- `AppView` type is exported from `features/Sidebar.tsx`.
- Sub-navigation inside a feature (e.g. the three knowledge libraries) uses a
  local `useState` + a segmented control built from existing `Button`/buttons —
  **do not** add a tabs dependency for this.

**Gotcha**: when adding a new top-level view, keep the existing view's JSX/state
untouched and add a sibling branch — don't refactor the working view into the
new one (avoids regressions).

---

## Feature container owns shared data

A feature area's container loads data shared by its panels once and passes it
down. Example: `KnowledgeView` loads `collections` and shares it with all three
panels; CRUD success calls back to reload.

```tsx
const [collections, setCollections] = React.useState<KnowledgeCollection[]>([]);
const loadCollections = React.useCallback(async () => { ... }, []);
// passed to CollectionsPanel(onChanged), RawCopiesPanel(collections), ...
```

---

## Dialogs (CRUD)

CRUD uses the shadcn `Dialog` (`components/ui/dialog.tsx`, Radix-based).

- **Create/Edit share one dialog**: pass the entity (or `null` for create). Seed
  the form in a `useEffect` keyed on `open`. See `CollectionDialog.tsx`.
- **Destructive actions use the shared `ConfirmDialog`** (`features/shared/`) —
  do not hand-roll confirm modals per feature.
- Forms are plain `useState` + controlled `Input`/`Textarea` — **no form library**.
  Validate inline, surface failures with `toast.error`.

```tsx
<ConfirmDialog
  open={deleting !== null}
  onOpenChange={(o) => !o && setDeleting(null)}
  title="删除集合"
  description={`确定删除「${deleting?.name}」？`}
  busy={deleteBusy}
  onConfirm={handleDelete}
/>
```

---

## Read-only vs editable views

When the same data needs both an editable and a read-only presentation, build a
**separate read-only component** rather than adding a `readOnly` flag to the
editable one.

- `ReviewPanel` stays the editable workbench form (don't touch it).
- `features/knowledge/AnalysisView.tsx` is the read-only renderer of an `Analysis`
  (+ optional asset context), reused by `RawCopyDetail` and `AnalysesPanel`.

**Why**: protects the editable workbench from regressions when read-only screens evolve.

---

## Feedback & loading

- All user-facing success/failure goes through `sonner` `toast` (mounted once in
  `main.tsx`). Don't render inline status banners for transient results.
- Loading uses `Skeleton`; empty uses shared `EmptyState`. Errors are caught and
  toasted; lists fall back to the empty state (so a failed/absent backend degrades
  gracefully instead of crashing).
