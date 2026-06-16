import * as React from "react";
import { toast } from "sonner";
import { FileSearch, Loader2, Pencil, Plus, Trash2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import {
  createFragment,
  deleteFragment,
  fetchFragments,
  updateFragment
} from "@/lib/api";
import { cn } from "@/lib/utils";
import type {
  FragmentFilters,
  FragmentQuality,
  FragmentRiskLevel,
  KnowledgeFragment,
  KnowledgeFragmentCreate
} from "@/lib/types";
import { ConfirmDialog } from "@/features/shared/ConfirmDialog";
import { EmptyState } from "@/features/shared/EmptyState";

const QUALITY_LABELS: Record<FragmentQuality, string> = {
  unknown: "未知",
  low: "低",
  medium: "中",
  high: "高"
};

const RISK_LABELS: Record<FragmentRiskLevel, string> = {
  low: "低",
  medium: "中",
  high: "高"
};

const EMPTY_FILTERS: Required<FragmentFilters> = {
  source_copy_id: "",
  fragment_role: "",
  position: "",
  industry: ""
};

export function FragmentsPanel() {
  const [items, setItems] = React.useState<KnowledgeFragment[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [filters, setFilters] =
    React.useState<Required<FragmentFilters>>(EMPTY_FILTERS);
  const [draftFilters, setDraftFilters] =
    React.useState<Required<FragmentFilters>>(EMPTY_FILTERS);
  const [selectedId, setSelectedId] = React.useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = React.useState(false);
  const [editing, setEditing] = React.useState<KnowledgeFragment | null>(null);
  const [deleting, setDeleting] = React.useState<KnowledgeFragment | null>(null);
  const [deleteBusy, setDeleteBusy] = React.useState(false);

  const selected = items.find((item) => item.id === selectedId) ?? null;

  const load = React.useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchFragments(compactFilters(filters));
      setItems(data);
      setSelectedId((current) => current ?? data[0]?.id ?? null);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "加载片段库失败");
    } finally {
      setLoading(false);
    }
  }, [filters]);

  React.useEffect(() => {
    void load();
  }, [load]);

  function openCreate() {
    setEditing(null);
    setDialogOpen(true);
  }

  function openEdit(item: KnowledgeFragment) {
    setEditing(item);
    setDialogOpen(true);
  }

  function applyFilters() {
    setFilters(draftFilters);
    setSelectedId(null);
  }

  function clearFilters() {
    setDraftFilters(EMPTY_FILTERS);
    setFilters(EMPTY_FILTERS);
    setSelectedId(null);
  }

  async function handleDelete() {
    if (!deleting) return;
    setDeleteBusy(true);
    try {
      await deleteFragment(deleting.id);
      toast.success("片段已删除");
      setItems((current) => current.filter((item) => item.id !== deleting.id));
      if (selectedId === deleting.id) setSelectedId(null);
      setDeleting(null);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "删除片段失败");
    } finally {
      setDeleteBusy(false);
    }
  }

  return (
    <div className="grid min-h-0 grid-cols-1 gap-4 lg:grid-cols-[minmax(320px,420px)_1fr]">
      <Card className="flex min-h-0 flex-col overflow-hidden p-4">
        <div className="mb-3 flex items-center justify-between gap-3">
          <div className="text-sm font-semibold">片段库（{items.length}）</div>
          <Button size="sm" onClick={openCreate}>
            <Plus />
            新建片段
          </Button>
        </div>

        <div className="mb-3 space-y-2 rounded-lg border border-border bg-muted/20 p-3">
          <FilterInput
            label="原文 ID"
            value={draftFilters.source_copy_id}
            onChange={(value) =>
              setDraftFilters((current) => ({
                ...current,
                source_copy_id: value
              }))
            }
          />
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
            <FilterInput
              label="角色"
              value={draftFilters.fragment_role}
              onChange={(value) =>
                setDraftFilters((current) => ({
                  ...current,
                  fragment_role: value
                }))
              }
            />
            <FilterInput
              label="位置"
              value={draftFilters.position}
              onChange={(value) =>
                setDraftFilters((current) => ({ ...current, position: value }))
              }
            />
            <FilterInput
              label="行业"
              value={draftFilters.industry}
              onChange={(value) =>
                setDraftFilters((current) => ({ ...current, industry: value }))
              }
            />
          </div>
          <div className="flex justify-end gap-2">
            <Button size="sm" variant="outline" onClick={clearFilters}>
              清空
            </Button>
            <Button size="sm" onClick={applyFilters}>
              筛选
            </Button>
          </div>
        </div>

        <div className="min-h-0 flex-1 space-y-2 overflow-y-auto pr-1">
          {loading ? (
            Array.from({ length: 5 }).map((_, index) => (
              <Skeleton key={index} className="h-16 w-full rounded-lg" />
            ))
          ) : items.length === 0 ? (
            <EmptyState
              icon={<FileSearch className="size-8" />}
              title="还没有片段"
              hint="手动拆分原文后，可把片段、上下文和弱标签沉淀到这里。"
            />
          ) : (
            items.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => setSelectedId(item.id)}
                className={cn(
                  "w-full rounded-lg border bg-card p-3 text-left transition-colors hover:border-primary/40 hover:bg-accent/40",
                  item.id === selectedId &&
                    "border-primary bg-accent/60 ring-1 ring-primary/20"
                )}
              >
                <div className="flex items-start justify-between gap-2">
                  <span className="line-clamp-1 text-sm font-medium">
                    {item.fragment_text}
                  </span>
                  <Badge variant={item.risk_level === "high" ? "destructive" : "muted"}>
                    {RISK_LABELS[item.risk_level]}
                  </Badge>
                </div>
                <div className="mt-1 line-clamp-1 text-xs text-muted-foreground">
                  {item.fragment_role} · {item.position} · 顺序{" "}
                  {item.sequence_order}
                </div>
              </button>
            ))
          )}
        </div>
      </Card>

      <Card className="flex min-h-0 flex-col overflow-hidden p-0">
        {selected ? (
          <FragmentDetail
            fragment={selected}
            onEdit={() => openEdit(selected)}
            onDelete={() => setDeleting(selected)}
          />
        ) : (
          <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
            选择一条片段查看详情。
          </div>
        )}
      </Card>

      <FragmentDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        fragment={editing}
        onSaved={load}
      />
      <ConfirmDialog
        open={deleting !== null}
        onOpenChange={(open) => !open && setDeleting(null)}
        title="删除片段"
        description="删除后该片段不再显示。"
        busy={deleteBusy}
        onConfirm={handleDelete}
      />
    </div>
  );
}

function FilterInput({
  label,
  value,
  onChange
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <div className="space-y-1">
      <Label className="text-xs">{label}</Label>
      <Input
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="h-8 text-xs"
      />
    </div>
  );
}

function FragmentDetail({
  fragment,
  onEdit,
  onDelete
}: {
  fragment: KnowledgeFragment;
  onEdit: () => void;
  onDelete: () => void;
}) {
  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between gap-3 border-b border-border px-5 py-4">
        <div className="min-w-0">
          <div className="text-base font-semibold">片段详情</div>
          <div className="mt-0.5 truncate text-xs text-muted-foreground">
            {fragment.id}
          </div>
        </div>
        <div className="flex shrink-0 gap-1">
          <Button size="icon" variant="ghost" onClick={onEdit} aria-label="编辑">
            <Pencil />
          </Button>
          <Button size="icon" variant="ghost" onClick={onDelete} aria-label="删除">
            <Trash2 />
          </Button>
        </div>
      </div>

      <div className="min-h-0 flex-1 space-y-5 overflow-y-auto p-5">
        <DetailBlock label="片段正文">{fragment.fragment_text}</DetailBlock>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <DetailBlock label="片段角色">{fragment.fragment_role}</DetailBlock>
          <DetailBlock label="位置">{fragment.position}</DetailBlock>
          <DetailBlock label="顺序">{fragment.sequence_order}</DetailBlock>
          <DetailBlock label="行业">{fragment.industry || "未标行业"}</DetailBlock>
          <DetailBlock label="来源质量">
            {QUALITY_LABELS[fragment.source_quality]}
          </DetailBlock>
          <DetailBlock label="风险等级">
            {RISK_LABELS[fragment.risk_level]}
          </DetailBlock>
        </div>
        <DetailBlock label="来源原文 ID">{fragment.source_copy_id}</DetailBlock>
        <DetailBlock label="来源拆解 ID">
          {fragment.analysis_id || "未关联拆解记录"}
        </DetailBlock>
        <DetailBlock label="上一个片段">
          {fragment.previous_fragment || "暂无"}
        </DetailBlock>
        <DetailBlock label="下一个片段">
          {fragment.next_fragment || "暂无"}
        </DetailBlock>
        <DetailBlock label="前置上下文">
          {fragment.before_context || "暂无"}
        </DetailBlock>
        <DetailBlock label="后置上下文">
          {fragment.after_context || "暂无"}
        </DetailBlock>
      </div>
    </div>
  );
}

function DetailBlock({
  label,
  children
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <section>
      <h3 className="mb-2 text-xs font-medium text-muted-foreground">{label}</h3>
      <div className="rounded-lg border border-border bg-muted/30 p-3 text-sm leading-6">
        {children}
      </div>
    </section>
  );
}

function FragmentDialog({
  open,
  onOpenChange,
  fragment,
  onSaved
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  fragment: KnowledgeFragment | null;
  onSaved: () => void;
}) {
  const isEdit = fragment !== null;
  const [busy, setBusy] = React.useState(false);
  const [draft, setDraft] = React.useState<KnowledgeFragmentCreate>(
    emptyFragmentDraft()
  );

  React.useEffect(() => {
    if (!open) return;
    setBusy(false);
    setDraft(fragment ? fragmentToDraft(fragment) : emptyFragmentDraft());
  }, [open, fragment]);

  function update<K extends keyof KnowledgeFragmentCreate>(
    key: K,
    value: KnowledgeFragmentCreate[K]
  ) {
    setDraft((current) => ({ ...current, [key]: value }));
  }

  async function handleSubmit() {
    if (!draft.source_copy_id.trim()) {
      toast.error("来源原文 ID 不能为空");
      return;
    }
    if (!draft.fragment_text.trim()) {
      toast.error("片段正文不能为空");
      return;
    }
    if (!draft.fragment_role.trim() || !draft.position.trim()) {
      toast.error("片段角色和位置不能为空");
      return;
    }

    setBusy(true);
    try {
      const body = normalizeFragmentDraft(draft);
      if (isEdit) await updateFragment(fragment.id, body);
      else await createFragment(body);
      toast.success(isEdit ? "片段已保存" : "片段已创建");
      onOpenChange(false);
      onSaved();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "保存片段失败");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl">
        <DialogHeader>
          <DialogTitle>{isEdit ? "编辑片段" : "新建片段"}</DialogTitle>
        </DialogHeader>

        <div className="max-h-[70vh] space-y-4 overflow-y-auto py-2 pr-1">
          <div className="grid gap-3 sm:grid-cols-2">
            <TextField
              id="fragment-source-copy"
              label="来源原文 ID"
              value={draft.source_copy_id}
              onChange={(value) => update("source_copy_id", value)}
            />
            <TextField
              id="fragment-analysis"
              label="来源拆解 ID"
              value={draft.analysis_id ?? ""}
              onChange={(value) => update("analysis_id", value)}
            />
            <NumberField
              id="fragment-order"
              label="顺序"
              value={draft.sequence_order}
              onChange={(value) => update("sequence_order", value)}
            />
            <TextField
              id="fragment-role"
              label="片段角色"
              value={draft.fragment_role}
              onChange={(value) => update("fragment_role", value)}
              placeholder="hook / pain_point / proof / cta"
            />
            <TextField
              id="fragment-position"
              label="位置"
              value={draft.position}
              onChange={(value) => update("position", value)}
              placeholder="opening / middle / ending"
            />
            <TextField
              id="fragment-industry"
              label="行业"
              value={draft.industry ?? ""}
              onChange={(value) => update("industry", value)}
            />
          </div>

          <TextareaField
            id="fragment-text"
            label="片段正文"
            value={draft.fragment_text}
            onChange={(value) => update("fragment_text", value)}
            minHeight="min-h-[110px]"
          />

          <div className="grid gap-3 sm:grid-cols-2">
            <EnumSelect
              label="来源质量"
              value={draft.source_quality}
              labels={QUALITY_LABELS}
              onChange={(value) => update("source_quality", value)}
            />
            <EnumSelect
              label="风险等级"
              value={draft.risk_level}
              labels={RISK_LABELS}
              onChange={(value) => update("risk_level", value)}
            />
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <TextareaField
              id="fragment-prev"
              label="上一个片段"
              value={draft.previous_fragment ?? ""}
              onChange={(value) => update("previous_fragment", value)}
            />
            <TextareaField
              id="fragment-next"
              label="下一个片段"
              value={draft.next_fragment ?? ""}
              onChange={(value) => update("next_fragment", value)}
            />
            <TextareaField
              id="fragment-before"
              label="前置上下文"
              value={draft.before_context ?? ""}
              onChange={(value) => update("before_context", value)}
            />
            <TextareaField
              id="fragment-after"
              label="后置上下文"
              value={draft.after_context ?? ""}
              onChange={(value) => update("after_context", value)}
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={busy}>
            取消
          </Button>
          <Button onClick={handleSubmit} disabled={busy}>
            {busy ? <Loader2 className="animate-spin" /> : null}
            {isEdit ? "保存" : "创建"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function TextField({
  id,
  label,
  value,
  onChange,
  placeholder
}: {
  id: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}) {
  return (
    <div className="space-y-1.5">
      <Label htmlFor={id}>{label}</Label>
      <Input
        id={id}
        value={value}
        placeholder={placeholder}
        onChange={(event) => onChange(event.target.value)}
      />
    </div>
  );
}

function NumberField({
  id,
  label,
  value,
  onChange
}: {
  id: string;
  label: string;
  value: number;
  onChange: (value: number) => void;
}) {
  return (
    <div className="space-y-1.5">
      <Label htmlFor={id}>{label}</Label>
      <Input
        id={id}
        type="number"
        min="0"
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
      />
    </div>
  );
}

function TextareaField({
  id,
  label,
  value,
  onChange,
  minHeight = "min-h-[84px]"
}: {
  id: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  minHeight?: string;
}) {
  return (
    <div className="space-y-1.5">
      <Label htmlFor={id}>{label}</Label>
      <Textarea
        id={id}
        value={value}
        className={minHeight}
        onChange={(event) => onChange(event.target.value)}
      />
    </div>
  );
}

function EnumSelect<T extends string>({
  label,
  value,
  labels,
  onChange
}: {
  label: string;
  value: T;
  labels: Record<T, string>;
  onChange: (value: T) => void;
}) {
  return (
    <div className="space-y-1.5">
      <Label>{label}</Label>
      <Select value={value} onValueChange={(next) => onChange(next as T)}>
        <SelectTrigger>
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {Object.entries(labels).map(([key, text]) => (
            <SelectItem key={key} value={key}>
              {text as string}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}

function compactFilters(filters: Required<FragmentFilters>): FragmentFilters {
  return {
    source_copy_id: filters.source_copy_id.trim() || undefined,
    fragment_role: filters.fragment_role.trim() || undefined,
    position: filters.position.trim() || undefined,
    industry: filters.industry.trim() || undefined
  };
}

function emptyFragmentDraft(): KnowledgeFragmentCreate {
  return {
    source_copy_id: "",
    analysis_id: null,
    sequence_order: 0,
    previous_fragment: null,
    next_fragment: null,
    before_context: null,
    after_context: null,
    fragment_text: "",
    fragment_role: "",
    position: "",
    industry: null,
    source_quality: "unknown",
    risk_level: "low",
    metadata: {}
  };
}

function fragmentToDraft(fragment: KnowledgeFragment): KnowledgeFragmentCreate {
  return {
    source_copy_id: fragment.source_copy_id,
    analysis_id: fragment.analysis_id ?? null,
    sequence_order: fragment.sequence_order,
    previous_fragment: fragment.previous_fragment ?? null,
    next_fragment: fragment.next_fragment ?? null,
    before_context: fragment.before_context ?? null,
    after_context: fragment.after_context ?? null,
    fragment_text: fragment.fragment_text,
    fragment_role: fragment.fragment_role,
    position: fragment.position,
    industry: fragment.industry ?? null,
    source_quality: fragment.source_quality,
    risk_level: fragment.risk_level,
    metadata: fragment.metadata
  };
}

function normalizeFragmentDraft(
  draft: KnowledgeFragmentCreate
): KnowledgeFragmentCreate {
  return {
    ...draft,
    source_copy_id: draft.source_copy_id.trim(),
    analysis_id: draft.analysis_id?.trim() || null,
    previous_fragment: draft.previous_fragment?.trim() || null,
    next_fragment: draft.next_fragment?.trim() || null,
    before_context: draft.before_context?.trim() || null,
    after_context: draft.after_context?.trim() || null,
    fragment_text: draft.fragment_text.trim(),
    fragment_role: draft.fragment_role.trim(),
    position: draft.position.trim(),
    industry: draft.industry?.trim() || null,
    sequence_order: Math.max(0, Number(draft.sequence_order) || 0),
    metadata: draft.metadata ?? {}
  };
}
