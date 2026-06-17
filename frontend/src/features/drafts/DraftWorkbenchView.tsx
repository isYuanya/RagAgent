import * as React from "react";
import {
  Archive,
  ChevronDown,
  ChevronUp,
  FileClock,
  FilePlus2,
  Loader2,
  Plus,
  Save,
  Search,
  Sparkles,
  Trash2
} from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
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
import { ConfirmDialog } from "@/features/shared/ConfirmDialog";
import { EmptyState } from "@/features/shared/EmptyState";
import {
  acceptRecommendation,
  addDraftItem,
  archiveDraft,
  createDraft,
  createDraftVersion,
  createNextSentenceRecommendation,
  deleteDraftItem,
  fetchDraft,
  fetchDraftVersions,
  fetchDrafts,
  fetchFragments,
  fetchTask,
  reorderDraftItems,
  updateDraft,
  updateDraftItem
} from "@/lib/api";
import { cn } from "@/lib/utils";
import type {
  DraftDetail,
  DraftItem,
  DraftStatus,
  DraftSummary,
  DraftVersionSummary,
  FragmentFilters,
  KnowledgeFragment,
  NextSentenceRecommendationResult,
  RecommendationCandidate,
  ReferenceFragmentSummary,
  TaskResponse
} from "@/lib/types";

const STATUS_LABELS: Record<DraftStatus, string> = {
  draft: "编辑中",
  ready: "可进入后续",
  archived: "已归档"
};

const ROLE_OPTIONS = ["hook", "pain_point", "proof", "transition", "cta"];
const POSITION_OPTIONS = ["opening", "middle", "ending"];

type DraftForm = {
  title: string;
  goal: string;
  audience: string;
  platform: string;
  purpose: string;
  status: DraftStatus;
};

export function DraftWorkbenchView({
  headerAction
}: {
  headerAction?: React.ReactNode;
}) {
  const [statusFilter, setStatusFilter] =
    React.useState<DraftStatus | "all">("draft");
  const [drafts, setDrafts] = React.useState<DraftSummary[]>([]);
  const [draftsLoading, setDraftsLoading] = React.useState(true);
  const [selectedId, setSelectedId] = React.useState<string | null>(null);
  const [detail, setDetail] = React.useState<DraftDetail | null>(null);
  const [detailLoading, setDetailLoading] = React.useState(false);
  const [draftForm, setDraftForm] = React.useState<DraftForm>(emptyDraftForm());
  const [savingDraft, setSavingDraft] = React.useState(false);
  const [creatingDraft, setCreatingDraft] = React.useState(false);
  const [archiving, setArchiving] = React.useState<DraftSummary | null>(null);
  const [archiveBusy, setArchiveBusy] = React.useState(false);
  const [versions, setVersions] = React.useState<DraftVersionSummary[]>([]);
  const [versionLabel, setVersionLabel] = React.useState("");
  const [versionBusy, setVersionBusy] = React.useState(false);

  const loadDrafts = React.useCallback(
    async (preferredId?: string | null) => {
      setDraftsLoading(true);
      try {
        const items = await fetchDrafts(statusFilter);
        setDrafts(items);
        setSelectedId((current) => {
          if (preferredId !== undefined) return preferredId;
          if (current && items.some((item) => item.id === current)) return current;
          return items[0]?.id ?? null;
        });
      } catch (error) {
        toast.error(error instanceof Error ? error.message : "加载草稿失败");
      } finally {
        setDraftsLoading(false);
      }
    },
    [statusFilter]
  );

  React.useEffect(() => {
    void loadDrafts();
  }, [loadDrafts]);

  const loadDetail = React.useCallback(async (draftId: string) => {
    setDetailLoading(true);
    try {
      const item = await fetchDraft(draftId);
      setDetail(item);
      setDraftForm(draftToForm(item));
      setVersions(await fetchDraftVersions(draftId));
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "加载草稿详情失败");
      setDetail(null);
      setVersions([]);
    } finally {
      setDetailLoading(false);
    }
  }, []);

  React.useEffect(() => {
    if (!selectedId) {
      setDetail(null);
      setVersions([]);
      setDraftForm(emptyDraftForm());
      return;
    }
    void loadDetail(selectedId);
  }, [selectedId, loadDetail]);

  async function handleCreateDraft() {
    setCreatingDraft(true);
    try {
      const next = await createDraft({
        title: "未命名草稿",
        metadata: {}
      });
      toast.success("草稿已创建");
      await loadDrafts(next.id);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "创建草稿失败");
    } finally {
      setCreatingDraft(false);
    }
  }

  async function handleSaveDraft() {
    if (!detail) return;
    if (!draftForm.title.trim()) {
      toast.error("草稿标题不能为空");
      return;
    }
    setSavingDraft(true);
    try {
      const updated = await updateDraft(detail.id, {
        title: draftForm.title.trim(),
        goal: draftForm.goal.trim() || null,
        audience: draftForm.audience.trim() || null,
        platform: draftForm.platform.trim() || null,
        purpose: draftForm.purpose.trim() || null,
        status: draftForm.status,
        metadata: detail.metadata
      });
      applyDetail(updated);
      toast.success("草稿信息已保存");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "保存草稿失败");
    } finally {
      setSavingDraft(false);
    }
  }

  async function handleArchive() {
    if (!archiving) return;
    setArchiveBusy(true);
    try {
      await archiveDraft(archiving.id);
      toast.success("草稿已归档");
      setArchiving(null);
      await loadDrafts(selectedId === archiving.id ? null : selectedId);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "归档草稿失败");
    } finally {
      setArchiveBusy(false);
    }
  }

  async function handleDetailChange(updated: DraftDetail) {
    applyDetail(updated);
    setDraftForm(draftToForm(updated));
  }

  async function handleSaveVersion() {
    if (!detail) return;
    setVersionBusy(true);
    try {
      const version = await createDraftVersion(detail.id, versionLabel);
      setVersionLabel("");
      setVersions((current) => [
        {
          id: version.id,
          draft_id: version.draft_id,
          version_number: version.version_number,
          label: version.label,
          current_text: version.current_text,
          item_count: version.item_count,
          metadata: version.metadata
        },
        ...current
      ]);
      toast.success("版本快照已保存");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "保存版本失败");
    } finally {
      setVersionBusy(false);
    }
  }

  function applyDetail(updated: DraftDetail) {
    setDetail(updated);
    setDrafts((current) =>
      current.map((draft) => (draft.id === updated.id ? toSummary(updated) : draft))
    );
  }

  return (
    <main className="flex min-w-0 flex-1 flex-col">
      <header className="flex items-center justify-between gap-4 border-b border-border px-6 py-4">
        <div>
          <h1 className="text-lg font-semibold">草稿工作台</h1>
          <p className="text-sm text-muted-foreground">
            从片段库选择素材，组装、编辑、排序并保存草稿版本。
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {headerAction}
          <Button onClick={handleCreateDraft} disabled={creatingDraft}>
            {creatingDraft ? <Loader2 className="animate-spin" /> : <FilePlus2 />}
            新建草稿
          </Button>
        </div>
      </header>

      <div className="grid min-h-0 flex-1 grid-cols-1 gap-4 p-6 xl:grid-cols-[300px_minmax(420px,1fr)_360px]">
        <Card className="flex min-h-0 flex-col overflow-hidden p-4">
          <div className="mb-3 flex items-center justify-between gap-3">
            <div className="text-sm font-semibold">草稿列表</div>
            <Select
              value={statusFilter}
              onValueChange={(value) =>
                setStatusFilter(value as DraftStatus | "all")
              }
            >
              <SelectTrigger className="h-8 w-[118px] text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="draft">编辑中</SelectItem>
                <SelectItem value="ready">可进入后续</SelectItem>
                <SelectItem value="archived">已归档</SelectItem>
                <SelectItem value="all">全部</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <DraftList
            items={drafts}
            loading={draftsLoading}
            selectedId={selectedId}
            onSelect={setSelectedId}
            onArchive={setArchiving}
          />
        </Card>

        <Card className="flex min-h-0 flex-col overflow-hidden p-0">
          {detailLoading ? (
            <DraftEditorSkeleton />
          ) : detail ? (
            <DraftEditor
              draft={detail}
              form={draftForm}
              saving={savingDraft}
              onFormChange={setDraftForm}
              onSaveDraft={handleSaveDraft}
              onDetailChange={handleDetailChange}
            />
          ) : (
            <div className="flex h-full items-center justify-center p-6">
              <EmptyState
                icon={<FilePlus2 className="size-8" />}
                title="还没有选中草稿"
                hint="新建草稿后，可以从片段库添加素材，也可以手工写入段落。"
              />
            </div>
          )}
        </Card>

        <Card className="flex min-h-0 flex-col overflow-hidden p-0">
          {detail ? (
            <DraftSidePanel
              draft={detail}
              versions={versions}
              versionLabel={versionLabel}
              versionBusy={versionBusy}
              onVersionLabelChange={setVersionLabel}
              onSaveVersion={handleSaveVersion}
              onDetailChange={handleDetailChange}
            />
          ) : (
            <div className="flex h-full items-center justify-center p-6 text-sm text-muted-foreground">
              选择草稿后显示素材和版本。
            </div>
          )}
        </Card>
      </div>

      <ConfirmDialog
        open={archiving !== null}
        onOpenChange={(open) => !open && setArchiving(null)}
        title="归档草稿"
        description="归档后草稿默认不在编辑列表显示，但版本历史会保留。"
        confirmLabel="归档"
        busy={archiveBusy}
        onConfirm={handleArchive}
      />
    </main>
  );
}

function DraftList({
  items,
  loading,
  selectedId,
  onSelect,
  onArchive
}: {
  items: DraftSummary[];
  loading: boolean;
  selectedId: string | null;
  onSelect: (id: string) => void;
  onArchive: (draft: DraftSummary) => void;
}) {
  if (loading) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 6 }).map((_, index) => (
          <Skeleton key={index} className="h-20 w-full rounded-lg" />
        ))}
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <EmptyState
        icon={<FileClock className="size-8" />}
        title="暂无草稿"
        hint="新建草稿后会出现在这里。"
      />
    );
  }

  return (
    <div className="min-h-0 flex-1 space-y-2 overflow-y-auto pr-1">
      {items.map((item) => (
        <div
          key={item.id}
          className={cn(
            "rounded-lg border bg-card transition-colors hover:border-primary/40 hover:bg-accent/40",
            selectedId === item.id &&
              "border-primary bg-accent/60 ring-1 ring-primary/20"
          )}
        >
          <button
            type="button"
            className="w-full p-3 text-left"
            onClick={() => onSelect(item.id)}
          >
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <div className="truncate text-sm font-medium">{item.title}</div>
                <div className="mt-1 line-clamp-2 text-xs text-muted-foreground">
                  {item.goal || item.current_text || "暂无内容"}
                </div>
              </div>
              <Badge variant={item.status === "archived" ? "muted" : "outline"}>
                {STATUS_LABELS[item.status]}
              </Badge>
            </div>
            <div className="mt-2 flex flex-wrap gap-1 text-xs text-muted-foreground">
              <span>{item.item_count} 段</span>
              {item.platform ? <span>· {item.platform}</span> : null}
              {item.purpose ? <span>· {item.purpose}</span> : null}
            </div>
          </button>
          {item.status !== "archived" ? (
            <div className="border-t border-border px-2 py-1.5">
              <Button
                size="sm"
                variant="ghost"
                className="h-7 w-full justify-start text-xs text-muted-foreground"
                onClick={() => onArchive(item)}
              >
                <Archive />
                归档
              </Button>
            </div>
          ) : null}
        </div>
      ))}
    </div>
  );
}

function DraftEditor({
  draft,
  form,
  saving,
  onFormChange,
  onSaveDraft,
  onDetailChange
}: {
  draft: DraftDetail;
  form: DraftForm;
  saving: boolean;
  onFormChange: (form: DraftForm) => void;
  onSaveDraft: () => void;
  onDetailChange: (draft: DraftDetail) => void;
}) {
  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-border px-5 py-4">
        <div className="mb-4 flex items-center justify-between gap-3">
          <div className="min-w-0">
            <div className="text-base font-semibold">草稿编辑区</div>
            <div className="mt-0.5 truncate text-xs text-muted-foreground">
              {draft.id}
            </div>
          </div>
          <Button onClick={onSaveDraft} disabled={saving}>
            {saving ? <Loader2 className="animate-spin" /> : <Save />}
            保存信息
          </Button>
        </div>

        <div className="grid gap-3 md:grid-cols-2">
          <TextField
            label="标题"
            value={form.title}
            onChange={(title) => onFormChange({ ...form, title })}
          />
          <SelectField
            label="状态"
            value={form.status}
            options={STATUS_LABELS}
            onChange={(status) => onFormChange({ ...form, status })}
          />
          <TextField
            label="平台"
            value={form.platform}
            onChange={(platform) => onFormChange({ ...form, platform })}
          />
          <TextField
            label="目的"
            value={form.purpose}
            onChange={(purpose) => onFormChange({ ...form, purpose })}
          />
          <TextField
            label="人群"
            value={form.audience}
            onChange={(audience) => onFormChange({ ...form, audience })}
          />
          <TextField
            label="目标"
            value={form.goal}
            onChange={(goal) => onFormChange({ ...form, goal })}
          />
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto p-5">
        <div className="mb-3 flex items-center justify-between gap-3">
          <div className="text-sm font-semibold">段落编排（{draft.item_count}）</div>
          <ManualItemForm draft={draft} onDetailChange={onDetailChange} />
        </div>

        {draft.items.length === 0 ? (
          <EmptyState
            icon={<Plus className="size-8" />}
            title="草稿还没有段落"
            hint="从右侧片段库添加，或手工写入一段文案。"
          />
        ) : (
          <div className="space-y-3">
            {draft.items.map((item, index) => (
              <DraftItemCard
                key={item.id}
                draft={draft}
                item={item}
                index={index}
                onDetailChange={onDetailChange}
              />
            ))}
          </div>
        )}

        <section className="mt-5">
          <div className="mb-2 text-xs font-medium text-muted-foreground">
            全文预览
          </div>
          <div className="whitespace-pre-wrap rounded-lg border border-border bg-muted/30 p-4 text-sm leading-7">
            {draft.current_text || "暂无正文"}
          </div>
        </section>
      </div>
    </div>
  );
}

function ManualItemForm({
  draft,
  onDetailChange
}: {
  draft: DraftDetail;
  onDetailChange: (draft: DraftDetail) => void;
}) {
  const [open, setOpen] = React.useState(false);
  const [text, setText] = React.useState("");
  const [role, setRole] = React.useState("");
  const [position, setPosition] = React.useState("");
  const [busy, setBusy] = React.useState(false);

  async function handleAdd() {
    if (!text.trim()) {
      toast.error("手工段落不能为空");
      return;
    }
    setBusy(true);
    try {
      const updated = await addDraftItem(draft.id, {
        edited_text: text.trim(),
        role: role.trim() || null,
        position: position.trim() || null,
        metadata: {}
      });
      setText("");
      setRole("");
      setPosition("");
      setOpen(false);
      onDetailChange(updated);
      toast.success("段落已添加");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "添加段落失败");
    } finally {
      setBusy(false);
    }
  }

  if (!open) {
    return (
      <Button size="sm" variant="outline" onClick={() => setOpen(true)}>
        <Plus />
        手工添加
      </Button>
    );
  }

  return (
    <div className="w-full rounded-lg border border-border bg-muted/20 p-3">
      <Textarea
        value={text}
        onChange={(event) => setText(event.target.value)}
        className="min-h-[90px]"
        placeholder="写入一段草稿文案"
      />
      <div className="mt-2 grid gap-2 sm:grid-cols-2">
        <Input
          value={role}
          onChange={(event) => setRole(event.target.value)}
          placeholder="角色，例如 hook"
        />
        <Input
          value={position}
          onChange={(event) => setPosition(event.target.value)}
          placeholder="位置，例如 opening"
        />
      </div>
      <div className="mt-2 flex justify-end gap-2">
        <Button
          size="sm"
          variant="outline"
          onClick={() => setOpen(false)}
          disabled={busy}
        >
          取消
        </Button>
        <Button size="sm" onClick={handleAdd} disabled={busy}>
          {busy ? <Loader2 className="animate-spin" /> : null}
          添加
        </Button>
      </div>
    </div>
  );
}

function DraftItemCard({
  draft,
  item,
  index,
  onDetailChange
}: {
  draft: DraftDetail;
  item: DraftItem;
  index: number;
  onDetailChange: (draft: DraftDetail) => void;
}) {
  const [text, setText] = React.useState(item.edited_text);
  const [role, setRole] = React.useState(item.role ?? "");
  const [position, setPosition] = React.useState(item.position ?? "");
  const [saving, setSaving] = React.useState(false);
  const [deleting, setDeleting] = React.useState(false);
  const [reordering, setReordering] = React.useState(false);

  React.useEffect(() => {
    setText(item.edited_text);
    setRole(item.role ?? "");
    setPosition(item.position ?? "");
  }, [item.id, item.edited_text, item.role, item.position]);

  async function handleSave() {
    if (!text.trim()) {
      toast.error("段落内容不能为空");
      return;
    }
    setSaving(true);
    try {
      const updated = await updateDraftItem(draft.id, item.id, {
        edited_text: text.trim(),
        role: role.trim() || null,
        position: position.trim() || null,
        metadata: item.metadata
      });
      onDetailChange(updated);
      toast.success("段落已保存");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "保存段落失败");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    setDeleting(true);
    try {
      await deleteDraftItem(draft.id, item.id);
      const updated = await fetchDraft(draft.id);
      onDetailChange(updated);
      toast.success("段落已删除");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "删除段落失败");
    } finally {
      setDeleting(false);
    }
  }

  async function move(direction: -1 | 1) {
    const nextIndex = index + direction;
    if (nextIndex < 0 || nextIndex >= draft.items.length) return;
    setReordering(true);
    try {
      const nextItems = [...draft.items];
      const [removed] = nextItems.splice(index, 1);
      nextItems.splice(nextIndex, 0, removed);
      const updated = await reorderDraftItems(
        draft.id,
        nextItems.map((current, orderIndex) => ({
          item_id: current.id,
          order_index: orderIndex
        }))
      );
      onDetailChange(updated);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "调整顺序失败");
    } finally {
      setReordering(false);
    }
  }

  return (
    <div className="rounded-lg border border-border bg-background p-3">
      <div className="mb-2 flex items-center justify-between gap-2">
        <div className="flex min-w-0 items-center gap-2">
          <Badge variant="outline">#{index + 1}</Badge>
          <span className="truncate text-xs text-muted-foreground">
            {item.source_fragment_id ? "来自片段库" : "手工段落"}
          </span>
        </div>
        <div className="flex shrink-0 gap-1">
          <Button
            size="icon"
            variant="ghost"
            onClick={() => void move(-1)}
            disabled={index === 0 || reordering}
            aria-label="上移"
          >
            <ChevronUp />
          </Button>
          <Button
            size="icon"
            variant="ghost"
            onClick={() => void move(1)}
            disabled={index === draft.items.length - 1 || reordering}
            aria-label="下移"
          >
            <ChevronDown />
          </Button>
          <Button
            size="icon"
            variant="ghost"
            onClick={handleDelete}
            disabled={deleting}
            aria-label="删除"
          >
            {deleting ? <Loader2 className="animate-spin" /> : <Trash2 />}
          </Button>
        </div>
      </div>
      <Textarea
        value={text}
        onChange={(event) => setText(event.target.value)}
        className="min-h-[120px]"
      />
      <div className="mt-2 grid gap-2 sm:grid-cols-[1fr_1fr_auto]">
        <ComboInput
          value={role}
          options={ROLE_OPTIONS}
          placeholder="角色"
          onChange={setRole}
        />
        <ComboInput
          value={position}
          options={POSITION_OPTIONS}
          placeholder="位置"
          onChange={setPosition}
        />
        <Button onClick={handleSave} disabled={saving}>
          {saving ? <Loader2 className="animate-spin" /> : <Save />}
          保存段落
        </Button>
      </div>
      {item.original_fragment_text &&
      item.original_fragment_text !== item.edited_text ? (
        <details className="mt-2 text-xs text-muted-foreground">
          <summary className="cursor-pointer">查看加入时原文</summary>
          <div className="mt-2 whitespace-pre-wrap rounded-md bg-muted/30 p-2 leading-5">
            {item.original_fragment_text}
          </div>
        </details>
      ) : null}
    </div>
  );
}

function DraftSidePanel({
  draft,
  versions,
  versionLabel,
  versionBusy,
  onVersionLabelChange,
  onSaveVersion,
  onDetailChange
}: {
  draft: DraftDetail;
  versions: DraftVersionSummary[];
  versionLabel: string;
  versionBusy: boolean;
  onVersionLabelChange: (value: string) => void;
  onSaveVersion: () => void;
  onDetailChange: (draft: DraftDetail) => void;
}) {
  return (
    <div className="flex h-full flex-col">
      <RecommendationPanel draft={draft} onDetailChange={onDetailChange} />
      <FragmentPicker draft={draft} onDetailChange={onDetailChange} />
      <div className="min-h-[220px] border-t border-border p-4">
        <div className="mb-3 flex items-center justify-between gap-3">
          <div className="text-sm font-semibold">版本快照</div>
          <Button size="sm" onClick={onSaveVersion} disabled={versionBusy}>
            {versionBusy ? <Loader2 className="animate-spin" /> : <Save />}
            保存版本
          </Button>
        </div>
        <Input
          value={versionLabel}
          onChange={(event) => onVersionLabelChange(event.target.value)}
          placeholder="版本说明，可选"
          className="mb-3"
        />
        <div className="max-h-[260px] space-y-2 overflow-y-auto pr-1">
          {versions.length === 0 ? (
            <EmptyState
              icon={<FileClock className="size-8" />}
              title="暂无版本"
              hint="保存版本后，可在这里查看历史快照。"
            />
          ) : (
            versions
              .slice()
              .sort((a, b) => b.version_number - a.version_number)
              .map((version) => (
                <div
                  key={version.id}
                  className="rounded-lg border border-border bg-background p-3"
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-sm font-medium">
                      V{version.version_number}
                    </span>
                    <Badge variant="outline">{version.item_count} 段</Badge>
                  </div>
                  <div className="mt-1 text-xs text-muted-foreground">
                    {version.label || "未命名版本"}
                  </div>
                  <div className="mt-2 line-clamp-3 whitespace-pre-wrap text-xs leading-5 text-muted-foreground">
                    {version.current_text || "空版本"}
                  </div>
                </div>
              ))
          )}
        </div>
      </div>
    </div>
  );
}

function RecommendationPanel({
  draft,
  onDetailChange
}: {
  draft: DraftDetail;
  onDetailChange: (draft: DraftDetail) => void;
}) {
  const [query, setQuery] = React.useState("");
  const [candidateCount, setCandidateCount] = React.useState("3");
  const [task, setTask] = React.useState<TaskResponse | null>(null);
  const [result, setResult] =
    React.useState<NextSentenceRecommendationResult | null>(null);
  const [creating, setCreating] = React.useState(false);
  const [acceptingId, setAcceptingId] = React.useState<string | null>(null);

  const isRunning = task ? ["queued", "running"].includes(task.status) : false;

  React.useEffect(() => {
    setTask(null);
    setResult(null);
    setQuery("");
  }, [draft.id]);

  React.useEffect(() => {
    if (!task || !["queued", "running"].includes(task.status)) return;
    const timer = window.setInterval(async () => {
      const next = await fetchTask(task.task_id);
      if (!next) return;
      setTask(next);
      if (next.status === "finished") {
        const parsed = parseRecommendationResult(next);
        setResult(parsed);
        if (parsed) toast.success("下一句推荐已生成");
      }
      if (next.status === "failed") {
        toast.error(next.error ?? "下一句推荐失败");
      }
    }, 1200);
    return () => window.clearInterval(timer);
  }, [task?.task_id, task?.status]);

  async function handleCreate() {
    setCreating(true);
    setResult(null);
    try {
      const payload = await createNextSentenceRecommendation({
        draft_id: draft.id,
        candidate_count: Number(candidateCount),
        cursor_item_id: null,
        q: query.trim() || null,
        metadata: {}
      });
      setTask(payload);
      const parsed = parseRecommendationResult(payload);
      if (payload.status === "finished" && parsed) {
        setResult(parsed);
        toast.success("下一句推荐已生成");
      } else {
        toast.message(payload.progress?.current_message ?? "推荐任务已创建");
      }
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "创建推荐任务失败");
    } finally {
      setCreating(false);
    }
  }

  async function handleAccept(candidate: RecommendationCandidate) {
    if (!task) return;
    setAcceptingId(candidate.candidate_id);
    try {
      const response = await acceptRecommendation({
        draft_id: draft.id,
        task_id: task.task_id,
        candidate_id: candidate.candidate_id,
        order_index: null,
        metadata: {}
      });
      onDetailChange(response.draft);
      toast.success("推荐已加入草稿");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "采纳推荐失败");
    } finally {
      setAcceptingId(null);
    }
  }

  return (
    <div className="border-b border-border p-4">
      <div className="mb-3 flex items-center justify-between gap-3">
        <div className="text-sm font-semibold">AI 下一句推荐</div>
        <Button
          size="sm"
          onClick={handleCreate}
          disabled={creating || isRunning || draft.status === "archived"}
        >
          {creating || isRunning ? (
            <Loader2 className="animate-spin" />
          ) : (
            <Sparkles />
          )}
          推荐
        </Button>
      </div>
      <div className="grid grid-cols-[1fr_86px] gap-2">
        <Input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="可选检索关键词"
        />
        <Select value={candidateCount} onValueChange={setCandidateCount}>
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {[1, 2, 3, 4, 5].map((count) => (
              <SelectItem key={count} value={String(count)}>
                {count} 条
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      {task?.progress ? (
        <div className="mt-2 rounded-md border border-border bg-muted/30 px-3 py-2 text-xs text-muted-foreground">
          {task.progress.current_message ?? task.progress.phase}
          {task.progress.model ? ` · ${task.progress.model}` : ""}
        </div>
      ) : null}
      {result ? (
        <div className="mt-3 space-y-3">
          <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
            <Badge variant="outline">下一功能：{result.next_function}</Badge>
            {result.model ? <span>{result.model}</span> : null}
          </div>
          <div className="max-h-[360px] space-y-2 overflow-y-auto pr-1">
            {result.candidates.map((candidate) => (
              <RecommendationCandidateCard
                key={candidate.candidate_id}
                candidate={candidate}
                references={result.reference_fragments}
                accepting={acceptingId === candidate.candidate_id}
                onAccept={() => handleAccept(candidate)}
              />
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}

function RecommendationCandidateCard({
  candidate,
  references,
  accepting,
  onAccept
}: {
  candidate: RecommendationCandidate;
  references: ReferenceFragmentSummary[];
  accepting: boolean;
  onAccept: () => void;
}) {
  const candidateReferences =
    candidate.reference_fragments.length > 0
      ? candidate.reference_fragments
      : references.filter((item) =>
          candidate.reference_fragment_ids.includes(item.id)
        );

  return (
    <div className="rounded-lg border border-border bg-background p-3">
      <div className="whitespace-pre-wrap text-sm leading-6">{candidate.text}</div>
      <div className="mt-2 flex flex-wrap gap-1 text-xs text-muted-foreground">
        <span>{candidate.function}</span>
        {candidate.tone ? <span>· {candidate.tone}</span> : null}
        <span>· 建议位置 {candidate.suggested_order_index + 1}</span>
      </div>
      {candidate.reason ? (
        <div className="mt-2 rounded-md bg-muted/30 p-2 text-xs leading-5 text-muted-foreground">
          {candidate.reason}
        </div>
      ) : null}
      {candidate.risk_warnings.length > 0 ? (
        <div className="mt-2 space-y-1">
          {candidate.risk_warnings.map((warning, index) => (
            <Badge key={index} variant="destructive">
              {warning.level}: {warning.message}
            </Badge>
          ))}
        </div>
      ) : null}
      {candidateReferences.length > 0 ? (
        <details className="mt-2 text-xs text-muted-foreground">
          <summary className="cursor-pointer">参考片段</summary>
          <div className="mt-2 space-y-2">
            {candidateReferences.map((item) => (
              <div key={item.id} className="rounded-md bg-muted/30 p-2 leading-5">
                <div className="text-foreground">{item.text}</div>
                <div className="mt-1">
                  {[item.role, item.position, item.source_display]
                    .filter(Boolean)
                    .join(" · ")}
                </div>
              </div>
            ))}
          </div>
        </details>
      ) : null}
      <Button
        size="sm"
        className="mt-3 w-full"
        onClick={onAccept}
        disabled={accepting}
      >
        {accepting ? <Loader2 className="animate-spin" /> : <Plus />}
        采纳到草稿
      </Button>
    </div>
  );
}

function FragmentPicker({
  draft,
  onDetailChange
}: {
  draft: DraftDetail;
  onDetailChange: (draft: DraftDetail) => void;
}) {
  const [query, setQuery] = React.useState("");
  const [role, setRole] = React.useState("");
  const [items, setItems] = React.useState<KnowledgeFragment[]>([]);
  const [loading, setLoading] = React.useState(false);
  const [addingId, setAddingId] = React.useState<string | null>(null);

  const load = React.useCallback(async () => {
    setLoading(true);
    try {
      const filters: FragmentFilters = {
        q: query.trim() || undefined,
        fragment_role: role.trim() || undefined,
        status: "approved"
      };
      setItems(await fetchFragments(filters));
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "加载片段失败");
    } finally {
      setLoading(false);
    }
  }, [query, role]);

  React.useEffect(() => {
    void load();
  }, [load]);

  async function handleAdd(fragment: KnowledgeFragment) {
    setAddingId(fragment.id);
    try {
      const updated = await addDraftItem(draft.id, {
        source_fragment_id: fragment.id,
        metadata: {}
      });
      onDetailChange(updated);
      toast.success("片段已加入草稿");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "加入草稿失败");
    } finally {
      setAddingId(null);
    }
  }

  return (
    <div className="min-h-0 flex-1 overflow-hidden p-4">
      <div className="mb-3 text-sm font-semibold">片段素材</div>
      <div className="mb-3 space-y-2">
        <div className="relative">
          <Search className="pointer-events-none absolute left-2 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            className="pl-7"
            placeholder="搜索片段"
          />
        </div>
        <ComboInput
          value={role}
          options={ROLE_OPTIONS}
          placeholder="按角色过滤"
          onChange={setRole}
        />
      </div>
      <div className="max-h-[calc(100vh-430px)] min-h-[220px] space-y-2 overflow-y-auto pr-1">
        {loading ? (
          Array.from({ length: 4 }).map((_, index) => (
            <Skeleton key={index} className="h-24 w-full rounded-lg" />
          ))
        ) : items.length === 0 ? (
          <EmptyState
            icon={<Search className="size-8" />}
            title="没有匹配片段"
            hint="默认只展示已通过审核的片段。"
          />
        ) : (
          items.map((item) => (
            <div
              key={item.id}
              className="rounded-lg border border-border bg-background p-3"
            >
              <div className="line-clamp-3 text-sm leading-6">
                {item.fragment_text}
              </div>
              <div className="mt-2 flex flex-wrap gap-1 text-xs text-muted-foreground">
                <span>{item.fragment_role}</span>
                <span>· {item.position}</span>
                {item.platform ? <span>· {item.platform}</span> : null}
              </div>
              <Button
                size="sm"
                className="mt-3 w-full"
                variant="outline"
                onClick={() => handleAdd(item)}
                disabled={addingId === item.id}
              >
                {addingId === item.id ? (
                  <Loader2 className="animate-spin" />
                ) : (
                  <Plus />
                )}
                加入草稿
              </Button>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

function DraftEditorSkeleton() {
  return (
    <div className="space-y-4 p-5">
      <Skeleton className="h-10 w-1/2 rounded-lg" />
      <div className="grid gap-3 md:grid-cols-2">
        {Array.from({ length: 6 }).map((_, index) => (
          <Skeleton key={index} className="h-9 w-full rounded-md" />
        ))}
      </div>
      <Skeleton className="h-36 w-full rounded-lg" />
      <Skeleton className="h-36 w-full rounded-lg" />
    </div>
  );
}

function TextField({
  label,
  value,
  onChange
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  const id = React.useId();
  return (
    <div className="space-y-1.5">
      <Label htmlFor={id}>{label}</Label>
      <Input id={id} value={value} onChange={(event) => onChange(event.target.value)} />
    </div>
  );
}

function SelectField<T extends string>({
  label,
  value,
  options,
  onChange
}: {
  label: string;
  value: T;
  options: Record<T, string>;
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
          {Object.entries(options).map(([key, text]) => (
            <SelectItem key={key} value={key}>
              {text as string}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}

function ComboInput({
  value,
  options,
  placeholder,
  onChange
}: {
  value: string;
  options: string[];
  placeholder: string;
  onChange: (value: string) => void;
}) {
  const id = React.useId();
  return (
    <>
      <Input
        value={value}
        list={id}
        placeholder={placeholder}
        onChange={(event) => onChange(event.target.value)}
      />
      <datalist id={id}>
        {options.map((option) => (
          <option key={option} value={option} />
        ))}
      </datalist>
    </>
  );
}

function emptyDraftForm(): DraftForm {
  return {
    title: "",
    goal: "",
    audience: "",
    platform: "",
    purpose: "",
    status: "draft"
  };
}

function draftToForm(draft: DraftDetail): DraftForm {
  return {
    title: draft.title,
    goal: draft.goal ?? "",
    audience: draft.audience ?? "",
    platform: draft.platform ?? "",
    purpose: draft.purpose ?? "",
    status: draft.status
  };
}

function toSummary(draft: DraftDetail): DraftSummary {
  return {
    id: draft.id,
    title: draft.title,
    goal: draft.goal,
    audience: draft.audience,
    platform: draft.platform,
    purpose: draft.purpose,
    status: draft.status,
    current_text: draft.current_text,
    item_count: draft.item_count,
    metadata: draft.metadata
  };
}

function parseRecommendationResult(
  task: TaskResponse
): NextSentenceRecommendationResult | null {
  const result = task.result;
  if (!result || typeof result !== "object") return null;
  if (
    typeof result.draft_id !== "string" ||
    typeof result.current_text !== "string" ||
    typeof result.next_function !== "string" ||
    !Array.isArray(result.candidates)
  ) {
    return null;
  }
  return {
    draft_id: result.draft_id,
    current_text: result.current_text,
    next_function: result.next_function,
    model: typeof result.model === "string" ? result.model : null,
    candidates: result.candidates as RecommendationCandidate[],
    reference_fragments: Array.isArray(result.reference_fragments)
      ? (result.reference_fragments as ReferenceFragmentSummary[])
      : []
  };
}
