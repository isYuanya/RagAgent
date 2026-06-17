import * as React from "react";
import { toast } from "sonner";
import { FileText, Loader2, Pencil, Plus, Trash2 } from "lucide-react";
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
  createTemplate,
  deleteTemplate,
  fetchTemplates,
  updateTemplate
} from "@/lib/api";
import { cn, splitLines } from "@/lib/utils";
import type {
  KnowledgeTemplate,
  SourceReference
} from "@/lib/types";
import { ConfirmDialog } from "@/features/shared/ConfirmDialog";
import { EmptyState } from "@/features/shared/EmptyState";

const SOURCE_NONE = "__none__";

export function ManualKnowledgePanel({ kind }: { kind: "templates" }) {
  void kind;
  const [items, setItems] = React.useState<KnowledgeTemplate[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [selectedId, setSelectedId] = React.useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = React.useState(false);
  const [editing, setEditing] = React.useState<KnowledgeTemplate | null>(null);
  const [deleting, setDeleting] = React.useState<KnowledgeTemplate | null>(null);
  const [deleteBusy, setDeleteBusy] = React.useState(false);

  const selected = items.find((item) => item.id === selectedId) ?? null;

  const load = React.useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchTemplates();
      setItems(data);
      setSelectedId((current) => current ?? data[0]?.id ?? null);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "加载失败");
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    void load();
  }, [load]);

  function openCreate() {
    setEditing(null);
    setDialogOpen(true);
  }

  function openEdit(item: KnowledgeTemplate) {
    setEditing(item);
    setDialogOpen(true);
  }

  async function handleDelete() {
    if (!deleting) return;
    setDeleteBusy(true);
    try {
      await deleteTemplate(deleting.id);
      toast.success("已删除");
      setItems((current) => current.filter((item) => item.id !== deleting.id));
      if (selectedId === deleting.id) setSelectedId(null);
      setDeleting(null);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "删除失败");
    } finally {
      setDeleteBusy(false);
    }
  }

  return (
    <div className="grid min-h-0 grid-cols-1 gap-4 lg:grid-cols-[minmax(300px,380px)_1fr]">
      <Card className="flex min-h-0 flex-col overflow-hidden p-4">
        <div className="mb-3 flex items-center justify-between gap-3">
          <div className="text-sm font-semibold">模板库（{items.length}）</div>
          <Button size="sm" onClick={openCreate}>
            <Plus />
            新建模板
          </Button>
        </div>

        <div className="min-h-0 flex-1 space-y-2 overflow-y-auto pr-1">
          {loading ? (
            Array.from({ length: 5 }).map((_, index) => (
              <Skeleton key={index} className="h-16 w-full rounded-lg" />
            ))
          ) : items.length === 0 ? (
            <EmptyState
              icon={<FileText className="size-8" />}
              title="还没有模板"
              hint="沉淀可复用句式、结构框架和适用场景。"
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
                <div className="line-clamp-1 text-sm font-medium">
                  {item.title}
                </div>
                <div className="mt-1 line-clamp-1 text-xs text-muted-foreground">
                  {item.content}
                </div>
              </button>
            ))
          )}
        </div>
      </Card>

      <Card className="flex min-h-0 flex-col overflow-hidden p-0">
        {selected ? (
          <div className="flex h-full flex-col">
            <div className="flex items-center justify-between gap-3 border-b border-border px-5 py-4">
              <div className="min-w-0">
                <div className="text-base font-semibold">模板详情</div>
                <div className="mt-0.5 truncate text-xs text-muted-foreground">
                  {selected.id}
                </div>
              </div>
              <div className="flex shrink-0 gap-1">
                <Button
                  size="icon"
                  variant="ghost"
                  onClick={() => openEdit(selected)}
                  aria-label="编辑"
                >
                  <Pencil />
                </Button>
                <Button
                  size="icon"
                  variant="ghost"
                  onClick={() => setDeleting(selected)}
                  aria-label="删除"
                >
                  <Trash2 />
                </Button>
              </div>
            </div>
            <TemplateDetail item={selected} />
          </div>
        ) : (
          <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
            选择一条记录查看详情。
          </div>
        )}
      </Card>

      <TemplateDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        item={editing}
        onSaved={load}
      />
      <ConfirmDialog
        open={deleting !== null}
        onOpenChange={(open) => !open && setDeleting(null)}
        title="删除模板库记录"
        description="删除后该记录不再显示。"
        busy={deleteBusy}
        onConfirm={handleDelete}
      />
    </div>
  );
}

function TemplateDetail({ item }: { item: KnowledgeTemplate }) {
  return (
    <div className="min-h-0 flex-1 space-y-5 overflow-y-auto p-5">
      <DetailBlock label="模板内容">{item.content}</DetailBlock>
      <DetailList label="结构框架" items={item.structure} />
      <DetailList label="适用场景" items={item.suitable_scenarios} />
      <SourceDetail source={item.source} />
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

function DetailList({ label, items }: { label: string; items: string[] }) {
  if (items.length === 0) {
    return <DetailBlock label={label}>暂无内容</DetailBlock>;
  }
  return (
    <section>
      <h3 className="mb-2 text-xs font-medium text-muted-foreground">{label}</h3>
      <div className="space-y-2">
        {items.map((item, index) => (
          <div
            key={`${item}-${index}`}
            className="rounded-lg border border-border bg-muted/30 px-3 py-2 text-sm"
          >
            {item}
          </div>
        ))}
      </div>
    </section>
  );
}

function SourceDetail({ source }: { source?: SourceReference | null }) {
  if (!source) return <DetailBlock label="来源引用">未关联来源</DetailBlock>;
  const sourceTypeLabel = source.source_type === "raw_copy" ? "原始文案" : "拆解记录";
  return (
    <DetailBlock label="来源引用">
      <div className="space-y-1">
        <div>
          {sourceTypeLabel} · {source.source_display ?? source.source_id}
        </div>
        {source.source_display ? (
          <div className="break-all text-xs text-muted-foreground">
            {source.source_id}
          </div>
        ) : null}
      </div>
    </DetailBlock>
  );
}

function TemplateDialog({
  open,
  onOpenChange,
  item,
  onSaved
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  item: KnowledgeTemplate | null;
  onSaved: () => void;
}) {
  const isEdit = item !== null;
  const [busy, setBusy] = React.useState(false);
  const [title, setTitle] = React.useState("");
  const [content, setContent] = React.useState("");
  const [structure, setStructure] = React.useState("");
  const [scenarios, setScenarios] = React.useState("");
  const [sourceType, setSourceType] = React.useState<
    SourceReference["source_type"] | typeof SOURCE_NONE
  >(SOURCE_NONE);
  const [sourceId, setSourceId] = React.useState("");

  React.useEffect(() => {
    if (!open) return;
    setBusy(false);
    setSourceType(item?.source?.source_type ?? SOURCE_NONE);
    setSourceId(item?.source?.source_id ?? "");
    setTitle(item?.title ?? "");
    setContent(item?.content ?? "");
    setStructure((item?.structure ?? []).join("\n"));
    setScenarios((item?.suitable_scenarios ?? []).join("\n"));
  }, [open, item]);

  async function handleSubmit() {
    if (!title.trim() || !content.trim()) {
      toast.error("标题和内容不能为空");
      return;
    }
    setBusy(true);
    try {
      const body = {
        title: title.trim(),
        content: content.trim(),
        structure: splitLines(structure),
        suitable_scenarios: splitLines(scenarios),
        source: buildSource(sourceType, sourceId),
        metadata: {}
      };
      if (isEdit) await updateTemplate(item.id, body);
      else await createTemplate(body);
      toast.success(isEdit ? "已保存" : "已创建");
      onOpenChange(false);
      onSaved();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "保存失败");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>{isEdit ? "编辑模板库记录" : "新建模板"}</DialogTitle>
        </DialogHeader>

        <div className="max-h-[68vh] space-y-4 overflow-y-auto py-2 pr-1">
          <TextField id="template-title" label="标题" value={title} onChange={setTitle} />
          <TextAreaField id="template-content" label="模板内容" value={content} onChange={setContent} />
          <TextAreaField id="template-structure" label="结构框架" value={structure} onChange={setStructure} placeholder="每行一条" />
          <TextAreaField id="template-scenarios" label="适用场景" value={scenarios} onChange={setScenarios} placeholder="每行一条" />

          <div className="grid gap-3 rounded-lg border border-border bg-muted/20 p-3 sm:grid-cols-[160px_1fr]">
            <div className="space-y-1.5">
              <Label>来源类型</Label>
              <Select
                value={sourceType}
                onValueChange={(value) =>
                  setSourceType(value as SourceReference["source_type"] | typeof SOURCE_NONE)
                }
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={SOURCE_NONE}>不关联</SelectItem>
                  <SelectItem value="raw_copy">原始文案</SelectItem>
                  <SelectItem value="analysis">拆解记录</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="source-id">来源 ID</Label>
              <Input
                id="source-id"
                value={sourceId}
                onChange={(event) => setSourceId(event.target.value)}
                placeholder="可选，填写 raw_copy_id 或 analysis_id"
                disabled={sourceType === SOURCE_NONE}
              />
            </div>
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
  onChange
}: {
  id: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <div className="space-y-1.5">
      <Label htmlFor={id}>{label}</Label>
      <Input
        id={id}
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
    </div>
  );
}

function TextAreaField({
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
      <Textarea
        id={id}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
      />
    </div>
  );
}

function buildSource(
  sourceType: SourceReference["source_type"] | typeof SOURCE_NONE,
  sourceId: string
): SourceReference | null {
  if (sourceType === SOURCE_NONE || !sourceId.trim()) return null;
  return { source_type: sourceType, source_id: sourceId.trim() };
}
