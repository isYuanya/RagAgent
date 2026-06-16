import * as React from "react";
import { toast } from "sonner";
import {
  Ban,
  BookOpenCheck,
  FileText,
  Loader2,
  Pencil,
  Plus,
  Tags,
  Trash2
} from "lucide-react";
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
  createBlock,
  createCase,
  createTag,
  createTemplate,
  deleteBlock,
  deleteCase,
  deleteTag,
  deleteTemplate,
  fetchBlocks,
  fetchCases,
  fetchTags,
  fetchTemplates,
  updateBlock,
  updateCase,
  updateTag,
  updateTemplate
} from "@/lib/api";
import { cn, splitLines } from "@/lib/utils";
import type {
  BlockSeverity,
  BlockType,
  KnowledgeBlock,
  KnowledgeCase,
  KnowledgeTag,
  KnowledgeTemplate,
  SourceReference,
  TagCategory
} from "@/lib/types";
import { ConfirmDialog } from "@/features/shared/ConfirmDialog";
import { EmptyState } from "@/features/shared/EmptyState";

type ManualKind = "templates" | "tags" | "cases" | "blocks";
type ManualItem = KnowledgeTemplate | KnowledgeTag | KnowledgeCase | KnowledgeBlock;

const SOURCE_NONE = "__none__";

const TAG_LABELS: Record<TagCategory, string> = {
  industry: "行业",
  emotion: "情绪",
  purpose: "目的",
  audience: "人群",
  hook_type: "钩子",
  custom: "自定义"
};

const BLOCK_TYPE_LABELS: Record<BlockType, string> = {
  sensitive_word: "敏感词",
  violation: "违规表达",
  do_not_copy: "不要复刻",
  custom: "自定义"
};

const SEVERITY_LABELS: Record<BlockSeverity, string> = {
  low: "低",
  medium: "中",
  high: "高"
};

const KIND_META: Record<
  ManualKind,
  {
    title: string;
    addLabel: string;
    emptyTitle: string;
    emptyHint: string;
    detailTitle: string;
    icon: React.ReactNode;
    fetchItems: () => Promise<ManualItem[]>;
    deleteItem: (id: string) => Promise<void>;
  }
> = {
  templates: {
    title: "模板库",
    addLabel: "新建模板",
    emptyTitle: "还没有模板",
    emptyHint: "沉淀可复用句式、结构框架和适用场景。",
    detailTitle: "模板详情",
    icon: <FileText className="size-8" />,
    fetchItems: fetchTemplates,
    deleteItem: deleteTemplate
  },
  tags: {
    title: "标签库",
    addLabel: "新建标签",
    emptyTitle: "还没有标签",
    emptyHint: "维护行业、情绪、目的、人群和钩子类型等分类标签。",
    detailTitle: "标签详情",
    icon: <Tags className="size-8" />,
    fetchItems: fetchTags,
    deleteItem: deleteTag
  },
  cases: {
    title: "案例库",
    addLabel: "新建案例",
    emptyTitle: "还没有案例",
    emptyHint: "记录高表现文案案例以及值得复用的原因。",
    detailTitle: "案例详情",
    icon: <BookOpenCheck className="size-8" />,
    fetchItems: fetchCases,
    deleteItem: deleteCase
  },
  blocks: {
    title: "禁用库",
    addLabel: "新建禁用项",
    emptyTitle: "还没有禁用项",
    emptyHint: "维护敏感词、违规表达和明确不要复刻的内容。",
    detailTitle: "禁用项详情",
    icon: <Ban className="size-8" />,
    fetchItems: fetchBlocks,
    deleteItem: deleteBlock
  }
};

export function ManualKnowledgePanel({ kind }: { kind: ManualKind }) {
  const meta = KIND_META[kind];
  const [items, setItems] = React.useState<ManualItem[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [selectedId, setSelectedId] = React.useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = React.useState(false);
  const [editing, setEditing] = React.useState<ManualItem | null>(null);
  const [deleting, setDeleting] = React.useState<ManualItem | null>(null);
  const [deleteBusy, setDeleteBusy] = React.useState(false);

  const selected = items.find((item) => item.id === selectedId) ?? null;

  const load = React.useCallback(async () => {
    setLoading(true);
    try {
      const data = await meta.fetchItems();
      setItems(data);
      setSelectedId((current) => current ?? data[0]?.id ?? null);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "加载失败");
    } finally {
      setLoading(false);
    }
  }, [meta]);

  React.useEffect(() => {
    void load();
  }, [load]);

  function openCreate() {
    setEditing(null);
    setDialogOpen(true);
  }

  function openEdit(item: ManualItem) {
    setEditing(item);
    setDialogOpen(true);
  }

  async function handleDelete() {
    if (!deleting) return;
    setDeleteBusy(true);
    try {
      await meta.deleteItem(deleting.id);
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
          <div className="text-sm font-semibold">
            {meta.title}（{items.length}）
          </div>
          <Button size="sm" onClick={openCreate}>
            <Plus />
            {meta.addLabel}
          </Button>
        </div>

        <div className="min-h-0 flex-1 space-y-2 overflow-y-auto pr-1">
          {loading ? (
            Array.from({ length: 5 }).map((_, index) => (
              <Skeleton key={index} className="h-16 w-full rounded-lg" />
            ))
          ) : items.length === 0 ? (
            <EmptyState
              icon={meta.icon}
              title={meta.emptyTitle}
              hint={meta.emptyHint}
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
                    {getTitle(kind, item)}
                  </span>
                  {getBadge(kind, item)}
                </div>
                <div className="mt-1 line-clamp-1 text-xs text-muted-foreground">
                  {getSummary(kind, item)}
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
                <div className="text-base font-semibold">{meta.detailTitle}</div>
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
            <ManualItemDetail kind={kind} item={selected} />
          </div>
        ) : (
          <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
            选择一条记录查看详情。
          </div>
        )}
      </Card>

      <ManualItemDialog
        kind={kind}
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        item={editing}
        onSaved={load}
      />
      <ConfirmDialog
        open={deleting !== null}
        onOpenChange={(open) => !open && setDeleting(null)}
        title={`删除${meta.title}记录`}
        description="删除后该记录不再显示。"
        busy={deleteBusy}
        onConfirm={handleDelete}
      />
    </div>
  );
}

function getTitle(kind: ManualKind, item: ManualItem): string {
  if (kind === "templates") return (item as KnowledgeTemplate).title;
  if (kind === "tags") return (item as KnowledgeTag).name;
  if (kind === "cases") return (item as KnowledgeCase).title;
  return (item as KnowledgeBlock).content;
}

function getSummary(kind: ManualKind, item: ManualItem): string {
  if (kind === "templates") return (item as KnowledgeTemplate).content;
  if (kind === "tags") return (item as KnowledgeTag).description ?? "暂无描述";
  if (kind === "cases") return (item as KnowledgeCase).reason;
  return (item as KnowledgeBlock).reason ?? "暂无原因";
}

function getBadge(kind: ManualKind, item: ManualItem) {
  if (kind === "tags") {
    return (
      <Badge variant="muted">
        {TAG_LABELS[(item as KnowledgeTag).category]}
      </Badge>
    );
  }
  if (kind === "blocks") {
    const block = item as KnowledgeBlock;
    return (
      <Badge variant={block.severity === "high" ? "destructive" : "muted"}>
        {SEVERITY_LABELS[block.severity]}
      </Badge>
    );
  }
  return null;
}

function ManualItemDetail({
  kind,
  item
}: {
  kind: ManualKind;
  item: ManualItem;
}) {
  return (
    <div className="min-h-0 flex-1 space-y-5 overflow-y-auto p-5">
      {kind === "templates" ? (
        <TemplateDetail item={item as KnowledgeTemplate} />
      ) : kind === "tags" ? (
        <TagDetail item={item as KnowledgeTag} />
      ) : kind === "cases" ? (
        <CaseDetail item={item as KnowledgeCase} />
      ) : (
        <BlockDetail item={item as KnowledgeBlock} />
      )}
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

function TemplateDetail({ item }: { item: KnowledgeTemplate }) {
  return (
    <>
      <DetailBlock label="模板内容">{item.content}</DetailBlock>
      <DetailList label="结构框架" items={item.structure} />
      <DetailList label="适用场景" items={item.suitable_scenarios} />
    </>
  );
}

function TagDetail({ item }: { item: KnowledgeTag }) {
  return (
    <>
      <DetailBlock label="分类">{TAG_LABELS[item.category]}</DetailBlock>
      <DetailBlock label="描述">{item.description || "暂无描述"}</DetailBlock>
    </>
  );
}

function CaseDetail({ item }: { item: KnowledgeCase }) {
  return (
    <>
      <DetailBlock label="高表现原因">{item.reason}</DetailBlock>
      <DetailBlock label="表现摘要">
        {item.performance_summary || "暂无表现摘要"}
      </DetailBlock>
    </>
  );
}

function BlockDetail({ item }: { item: KnowledgeBlock }) {
  return (
    <>
      <DetailBlock label="类型">{BLOCK_TYPE_LABELS[item.block_type]}</DetailBlock>
      <DetailBlock label="风险级别">{SEVERITY_LABELS[item.severity]}</DetailBlock>
      <DetailBlock label="原因">{item.reason || "暂无原因"}</DetailBlock>
    </>
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
  return (
    <DetailBlock label="来源引用">
      {source.source_type === "raw_copy" ? "原始文案" : "拆解记录"} ·{" "}
      {source.source_id}
    </DetailBlock>
  );
}

function ManualItemDialog({
  kind,
  open,
  onOpenChange,
  item,
  onSaved
}: {
  kind: ManualKind;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  item: ManualItem | null;
  onSaved: () => void;
}) {
  const isEdit = item !== null;
  const meta = KIND_META[kind];
  const [busy, setBusy] = React.useState(false);
  const [title, setTitle] = React.useState("");
  const [content, setContent] = React.useState("");
  const [secondary, setSecondary] = React.useState("");
  const [structure, setStructure] = React.useState("");
  const [scenarios, setScenarios] = React.useState("");
  const [tagCategory, setTagCategory] = React.useState<TagCategory>("custom");
  const [blockType, setBlockType] = React.useState<BlockType>("custom");
  const [severity, setSeverity] = React.useState<BlockSeverity>("medium");
  const [sourceType, setSourceType] = React.useState<SourceReference["source_type"] | typeof SOURCE_NONE>(
    SOURCE_NONE
  );
  const [sourceId, setSourceId] = React.useState("");

  React.useEffect(() => {
    if (!open) return;
    setBusy(false);
    setSourceType(item?.source?.source_type ?? SOURCE_NONE);
    setSourceId(item?.source?.source_id ?? "");
    if (kind === "templates") {
      const value = item as KnowledgeTemplate | null;
      setTitle(value?.title ?? "");
      setContent(value?.content ?? "");
      setStructure((value?.structure ?? []).join("\n"));
      setScenarios((value?.suitable_scenarios ?? []).join("\n"));
      setSecondary("");
    } else if (kind === "tags") {
      const value = item as KnowledgeTag | null;
      setTitle(value?.name ?? "");
      setContent(value?.description ?? "");
      setTagCategory(value?.category ?? "custom");
      setSecondary("");
    } else if (kind === "cases") {
      const value = item as KnowledgeCase | null;
      setTitle(value?.title ?? "");
      setContent(value?.reason ?? "");
      setSecondary(value?.performance_summary ?? "");
    } else {
      const value = item as KnowledgeBlock | null;
      setTitle(value?.content ?? "");
      setContent(value?.reason ?? "");
      setBlockType(value?.block_type ?? "custom");
      setSeverity(value?.severity ?? "medium");
      setSecondary("");
    }
  }, [open, kind, item]);

  async function handleSubmit() {
    const source = buildSource(sourceType, sourceId);
    setBusy(true);
    try {
      if (kind === "templates") {
        if (!title.trim() || !content.trim()) {
          toast.error("标题和内容不能为空");
          return;
        }
        const body = {
          title: title.trim(),
          content: content.trim(),
          structure: splitLines(structure),
          suitable_scenarios: splitLines(scenarios),
          source,
          metadata: {}
        };
        if (isEdit) await updateTemplate(item.id, body);
        else await createTemplate(body);
      } else if (kind === "tags") {
        if (!title.trim()) {
          toast.error("标签名称不能为空");
          return;
        }
        const body = {
          name: title.trim(),
          category: tagCategory,
          description: content.trim() || null,
          source,
          metadata: {}
        };
        if (isEdit) await updateTag(item.id, body);
        else await createTag(body);
      } else if (kind === "cases") {
        if (!title.trim() || !content.trim()) {
          toast.error("标题和原因不能为空");
          return;
        }
        const body = {
          title: title.trim(),
          reason: content.trim(),
          performance_summary: secondary.trim() || null,
          source,
          metadata: {}
        };
        if (isEdit) await updateCase(item.id, body);
        else await createCase(body);
      } else {
        if (!title.trim()) {
          toast.error("禁用内容不能为空");
          return;
        }
        const body = {
          content: title.trim(),
          block_type: blockType,
          reason: content.trim() || null,
          severity,
          source,
          metadata: {}
        };
        if (isEdit) await updateBlock(item.id, body);
        else await createBlock(body);
      }
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
          <DialogTitle>
            {isEdit ? `编辑${meta.title}记录` : meta.addLabel}
          </DialogTitle>
        </DialogHeader>

        <div className="max-h-[68vh] space-y-4 overflow-y-auto py-2 pr-1">
          <PrimaryFields
            kind={kind}
            title={title}
            content={content}
            secondary={secondary}
            structure={structure}
            scenarios={scenarios}
            tagCategory={tagCategory}
            blockType={blockType}
            severity={severity}
            onTitleChange={setTitle}
            onContentChange={setContent}
            onSecondaryChange={setSecondary}
            onStructureChange={setStructure}
            onScenariosChange={setScenarios}
            onTagCategoryChange={setTagCategory}
            onBlockTypeChange={setBlockType}
            onSeverityChange={setSeverity}
          />

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
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={busy}
          >
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

function PrimaryFields({
  kind,
  title,
  content,
  secondary,
  structure,
  scenarios,
  tagCategory,
  blockType,
  severity,
  onTitleChange,
  onContentChange,
  onSecondaryChange,
  onStructureChange,
  onScenariosChange,
  onTagCategoryChange,
  onBlockTypeChange,
  onSeverityChange
}: {
  kind: ManualKind;
  title: string;
  content: string;
  secondary: string;
  structure: string;
  scenarios: string;
  tagCategory: TagCategory;
  blockType: BlockType;
  severity: BlockSeverity;
  onTitleChange: (value: string) => void;
  onContentChange: (value: string) => void;
  onSecondaryChange: (value: string) => void;
  onStructureChange: (value: string) => void;
  onScenariosChange: (value: string) => void;
  onTagCategoryChange: (value: TagCategory) => void;
  onBlockTypeChange: (value: BlockType) => void;
  onSeverityChange: (value: BlockSeverity) => void;
}) {
  if (kind === "templates") {
    return (
      <>
        <TextField id="template-title" label="标题" value={title} onChange={onTitleChange} />
        <TextAreaField id="template-content" label="模板内容" value={content} onChange={onContentChange} />
        <TextAreaField id="template-structure" label="结构框架" value={structure} onChange={onStructureChange} placeholder="每行一条" />
        <TextAreaField id="template-scenarios" label="适用场景" value={scenarios} onChange={onScenariosChange} placeholder="每行一条" />
      </>
    );
  }
  if (kind === "tags") {
    return (
      <>
        <TextField id="tag-name" label="标签名称" value={title} onChange={onTitleChange} />
        <div className="space-y-1.5">
          <Label>分类</Label>
          <Select
            value={tagCategory}
            onValueChange={(value) => onTagCategoryChange(value as TagCategory)}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {Object.entries(TAG_LABELS).map(([value, label]) => (
                <SelectItem key={value} value={value}>
                  {label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <TextAreaField id="tag-description" label="描述" value={content} onChange={onContentChange} />
      </>
    );
  }
  if (kind === "cases") {
    return (
      <>
        <TextField id="case-title" label="标题" value={title} onChange={onTitleChange} />
        <TextAreaField id="case-reason" label="高表现原因" value={content} onChange={onContentChange} />
        <TextAreaField id="case-performance" label="表现摘要" value={secondary} onChange={onSecondaryChange} />
      </>
    );
  }
  return (
    <>
      <TextAreaField id="block-content" label="禁用内容" value={title} onChange={onTitleChange} />
      <div className="grid gap-3 sm:grid-cols-2">
        <div className="space-y-1.5">
          <Label>类型</Label>
          <Select
            value={blockType}
            onValueChange={(value) => onBlockTypeChange(value as BlockType)}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {Object.entries(BLOCK_TYPE_LABELS).map(([value, label]) => (
                <SelectItem key={value} value={value}>
                  {label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1.5">
          <Label>风险级别</Label>
          <Select
            value={severity}
            onValueChange={(value) => onSeverityChange(value as BlockSeverity)}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {Object.entries(SEVERITY_LABELS).map(([value, label]) => (
                <SelectItem key={value} value={value}>
                  {label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>
      <TextAreaField id="block-reason" label="原因" value={content} onChange={onContentChange} />
    </>
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
