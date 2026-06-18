import * as React from "react";
import {
  Archive,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Copy,
  Download,
  FileClock,
  FileJson,
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
  acceptComposition,
  acceptRecommendation,
  addDraftItem,
  approveDraft,
  archiveDraft,
  createAutoComposition,
  createDraft,
  createDraftVersion,
  createDraftVideoExport,
  createNextSentenceRecommendation,
  deleteDraftItem,
  fetchDraft,
  fetchDraftVideoExports,
  fetchDraftVersions,
  fetchDrafts,
  fetchFragments,
  fetchTask,
  reorderDraftItems,
  updateDraft,
  updateDraftItem
} from "@/lib/api";
import {
  cn,
  formatPositionLabel,
  formatQuoteModeLabel,
  formatRoleLabel
} from "@/lib/utils";
import type {
  AutoCompositionBrief,
  AutoCompositionResult,
  CompositionCandidate,
  DraftDetail,
  DraftItem,
  DraftStatus,
  DraftSummary,
  DraftVideoExportPayload,
  DraftVideoExportRecord,
  DraftVersionSummary,
  FragmentFilters,
  KnowledgeFragment,
  NextSentenceRecommendationResult,
  RecommendationCandidate,
  ReferenceFragmentSummary,
  TaskResponse
} from "@/lib/types";
import { Progress } from "@/components/ui/progress";

const STATUS_LABELS: Record<DraftStatus, string> = {
  draft: "编辑中",
  ready: "已审批通过",
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
  const [approvalBusy, setApprovalBusy] = React.useState(false);
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

  async function handleApproveDraft() {
    if (!detail) return;
    setApprovalBusy(true);
    try {
      const response = await approveDraft(detail.id);
      applyDetail(response.draft);
      setDraftForm(draftToForm(response.draft));
      await loadDrafts(response.draft.id);
      const fragmentCount = response.fragment_extraction.fragment_count;
      const resultLabel =
        response.fragment_extraction.status === "created"
          ? `已拆解 ${fragmentCount} 个片段`
          : response.fragment_extraction.status === "skipped"
            ? "片段已存在，已跳过重复拆解"
            : response.fragment_extraction.message || "片段拆解失败";
      toast.success(`审批通过，已进入知识库。${resultLabel}`);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "审批通过失败");
    } finally {
      setApprovalBusy(false);
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
                <SelectItem value="ready">已审批通过</SelectItem>
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
              approving={approvalBusy}
              onFormChange={setDraftForm}
              onSaveDraft={handleSaveDraft}
              onApproveDraft={handleApproveDraft}
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
              onCompositionAccepted={(nextDraft) => {
                applyDetail(nextDraft);
                setDraftForm(draftToForm(nextDraft));
                void loadDrafts(nextDraft.id);
              }}
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
  approving,
  onFormChange,
  onSaveDraft,
  onApproveDraft,
  onDetailChange
}: {
  draft: DraftDetail;
  form: DraftForm;
  saving: boolean;
  approving: boolean;
  onFormChange: (form: DraftForm) => void;
  onSaveDraft: () => void;
  onApproveDraft: () => void;
  onDetailChange: (draft: DraftDetail) => void;
}) {
  const [previewExpanded, setPreviewExpanded] = React.useState(false);
  const canApprove =
    draft.status !== "archived" &&
    draft.status !== "ready" &&
    Boolean(draft.current_text.trim());

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
          <div className="flex shrink-0 items-center gap-2">
            <Button onClick={onApproveDraft} disabled={!canApprove || approving}>
              {approving ? <Loader2 className="animate-spin" /> : <CheckCircle2 />}
              审批通过
            </Button>
            <Button onClick={onSaveDraft} disabled={saving}>
              {saving ? <Loader2 className="animate-spin" /> : <Save />}
              保存信息
            </Button>
          </div>
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
        <section className="sticky top-0 z-10 mb-4 rounded-lg border border-border bg-card p-3 shadow-sm">
          <div className="mb-2 flex items-center justify-between gap-3">
            <div className="text-xs font-medium text-muted-foreground">
            全文预览
          </div>
            <Button
              type="button"
              size="sm"
              variant="ghost"
              className="h-7 px-2 text-xs"
              onClick={() => setPreviewExpanded((current) => !current)}
            >
              {previewExpanded ? <ChevronUp /> : <ChevronDown />}
              {previewExpanded ? "收起" : "展开"}
            </Button>
          </div>
          <div
            className={cn(
              "overflow-y-auto whitespace-pre-wrap rounded-md bg-muted/30 p-3 text-sm leading-7",
              previewExpanded ? "max-h-[420px]" : "max-h-36"
            )}
          >
            {draft.current_text || "暂无正文"}
          </div>
        </section>

        <DraftVideoExportPanel draft={draft} />

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
      </div>
    </div>
  );
}

function DraftVideoExportPanel({ draft }: { draft: DraftDetail }) {
  const [records, setRecords] = React.useState<DraftVideoExportRecord[]>([]);
  const [selectedId, setSelectedId] = React.useState<string | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [task, setTask] = React.useState<TaskResponse | null>(null);
  const [creating, setCreating] = React.useState(false);

  const isRunning = task ? ["queued", "running"].includes(task.status) : false;
  const selected = records.find((item) => item.id === selectedId) ?? records[0] ?? null;
  const canCreate = draft.status !== "archived" && Boolean(draft.current_text.trim());

  const loadRecords = React.useCallback(async () => {
    setLoading(true);
    try {
      const items = await fetchDraftVideoExports(draft.id);
      setRecords(items);
      setSelectedId((current) =>
        current && items.some((item) => item.id === current)
          ? current
          : items[0]?.id ?? null
      );
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "加载视频 JSON 历史失败");
      setRecords([]);
      setSelectedId(null);
    } finally {
      setLoading(false);
    }
  }, [draft.id]);

  React.useEffect(() => {
    setTask(null);
    setSelectedId(null);
    void loadRecords();
  }, [loadRecords]);

  React.useEffect(() => {
    if (!task || !["queued", "running"].includes(task.status)) return;
    const timer = window.setInterval(async () => {
      const next = await fetchTask(task.task_id);
      if (!next) return;
      setTask(next);
      if (next.status === "finished") {
        const record = parseDraftVideoExportRecord(next.result);
        await loadRecords();
        if (record) setSelectedId(record.id);
        toast.success("视频 JSON 已生成");
      }
      if (next.status === "failed") {
        toast.error(next.error ?? "视频 JSON 生成失败");
      }
    }, 1200);
    return () => window.clearInterval(timer);
  }, [task?.task_id, task?.status, loadRecords]);

  async function handleCreate() {
    if (!canCreate) {
      toast.error("草稿正文为空，无法生成视频 JSON");
      return;
    }
    setCreating(true);
    try {
      const payload = await createDraftVideoExport(draft.id);
      setTask(payload);
      const record = parseDraftVideoExportRecord(payload.result);
      if (payload.status === "finished" && record) {
        await loadRecords();
        setSelectedId(record.id);
        toast.success("视频 JSON 已生成");
      } else if (payload.status === "failed") {
        toast.error(payload.error ?? "视频 JSON 生成失败");
      } else {
        toast.message(payload.progress?.current_message ?? "视频 JSON 任务已创建");
      }
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "创建视频 JSON 任务失败");
    } finally {
      setCreating(false);
    }
  }

  async function handleCopy(record: DraftVideoExportRecord) {
    try {
      await navigator.clipboard.writeText(formatVideoExportJson(record.result));
      toast.success("已复制视频 JSON");
    } catch {
      toast.error("复制失败，请手动复制");
    }
  }

  function handleDownload(record: DraftVideoExportRecord) {
    const blob = new Blob([formatVideoExportJson(record.result)], {
      type: "application/json;charset=utf-8"
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${record.result.title || "video-copy"}.json`;
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <section className="mb-4 rounded-lg border border-border bg-card p-4">
      <div className="mb-3 flex items-center justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2 text-sm font-semibold">
            <FileJson className="size-4 text-primary" />
            视频处理 JSON
          </div>
          <div className="mt-0.5 text-xs text-muted-foreground">
            生成结果会保存为历史；复制和下载只包含六个视频处理字段。
          </div>
        </div>
        <Button size="sm" onClick={handleCreate} disabled={!canCreate || creating || isRunning}>
          {creating || isRunning ? <Loader2 className="animate-spin" /> : <Sparkles />}
          生成
        </Button>
      </div>

      {task?.progress ? (
        <div className="mb-3 space-y-2 rounded-md border border-border bg-muted/30 p-3">
          <div className="flex items-center justify-between text-xs">
            <span className="font-medium">{task.progress.current_message ?? task.progress.phase}</span>
            <span className="tabular-nums text-primary">{task.progress.percent}%</span>
          </div>
          <Progress value={task.progress.percent} aria-label="视频 JSON 生成进度" />
          <div className="text-xs text-muted-foreground">
            {task.progress.model ? `模型：${task.progress.model}` : "模型：未配置"}
          </div>
        </div>
      ) : null}

      {loading ? (
        <Skeleton className="h-24 w-full" />
      ) : selected ? (
        <div className="space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            {records.slice(0, 5).map((record) => (
              <Button
                key={record.id}
                type="button"
                size="sm"
                variant={record.id === selected.id ? "secondary" : "outline"}
                onClick={() => setSelectedId(record.id)}
              >
                {formatExportTime(record.created_at)}
              </Button>
            ))}
          </div>

          <div className="grid gap-3 lg:grid-cols-[260px_1fr]">
            <div className="space-y-2 rounded-md border border-border bg-muted/20 p-3 text-sm">
              <div className="font-medium">{selected.result.title}</div>
              <div className="whitespace-pre-wrap text-xs text-muted-foreground">
                {selected.result.title_break}
              </div>
              <div className="text-xs text-muted-foreground">
                {selected.model ? `模型：${selected.model}` : "模型：未记录"}
              </div>
              <div className="text-xs text-muted-foreground">
                话题：{selected.result.hashtags.join(", ") || "无"}
              </div>
              <div className="flex gap-2 pt-1">
                <Button size="sm" variant="outline" onClick={() => handleCopy(selected)}>
                  <Copy />
                  复制
                </Button>
                <Button size="sm" variant="outline" onClick={() => handleDownload(selected)}>
                  <Download />
                  下载
                </Button>
              </div>
            </div>
            <pre className="max-h-72 overflow-auto rounded-md bg-muted/40 p-3 text-xs leading-5">
              {formatVideoExportJson(selected.result)}
            </pre>
          </div>
        </div>
      ) : (
        <div className="rounded-md border border-dashed border-border p-4 text-sm text-muted-foreground">
          暂无视频 JSON 历史。
        </div>
      )}
    </section>
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
          placeholder="角色，例如 开头钩子（hook）"
        />
        <Input
          value={position}
          onChange={(event) => setPosition(event.target.value)}
          placeholder="位置，例如 开头（opening）"
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
          formatOption={formatRoleLabel}
          onChange={setRole}
        />
        <ComboInput
          value={position}
          options={POSITION_OPTIONS}
          placeholder="位置"
          formatOption={formatPositionLabel}
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
  onDetailChange,
  onCompositionAccepted
}: {
  draft: DraftDetail;
  versions: DraftVersionSummary[];
  versionLabel: string;
  versionBusy: boolean;
  onVersionLabelChange: (value: string) => void;
  onSaveVersion: () => void;
  onDetailChange: (draft: DraftDetail) => void;
  onCompositionAccepted: (draft: DraftDetail) => void;
}) {
  return (
    <div className="flex h-full flex-col">
      <AutoCompositionPanel
        draft={draft}
        onCompositionAccepted={onCompositionAccepted}
      />
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

function AutoCompositionPanel({
  draft,
  onCompositionAccepted
}: {
  draft: DraftDetail;
  onCompositionAccepted: (draft: DraftDetail) => void;
}) {
  const [product, setProduct] = React.useState(draft.goal ?? draft.title);
  const [audience, setAudience] = React.useState(draft.audience ?? "");
  const [platform, setPlatform] = React.useState(draft.platform ?? "");
  const [purpose, setPurpose] = React.useState(draft.purpose ?? "");
  const [style, setStyle] = React.useState("实用、清晰、可信");
  const [sellingPoints, setSellingPoints] = React.useState("");
  const [constraints, setConstraints] = React.useState("");
  const [targetLength, setTargetLength] = React.useState("");
  const [task, setTask] = React.useState<TaskResponse | null>(null);
  const [result, setResult] = React.useState<AutoCompositionResult | null>(null);
  const [creating, setCreating] = React.useState(false);
  const [acceptingId, setAcceptingId] = React.useState<string | null>(null);

  const isRunning = task ? ["queued", "running"].includes(task.status) : false;

  React.useEffect(() => {
    setProduct(draft.goal ?? draft.title);
    setAudience(draft.audience ?? "");
    setPlatform(draft.platform ?? "");
    setPurpose(draft.purpose ?? "");
    setTask(null);
    setResult(null);
  }, [draft.id, draft.goal, draft.title, draft.audience, draft.platform, draft.purpose]);

  React.useEffect(() => {
    if (!task || !["queued", "running"].includes(task.status)) return;
    const timer = window.setInterval(async () => {
      const next = await fetchTask(task.task_id);
      if (!next) return;
      setTask(next);
      if (next.status === "finished") {
        const parsed = parseAutoCompositionResult(next);
        setResult(parsed);
        if (parsed) toast.success("自动组稿已生成");
      }
      if (next.status === "failed") {
        toast.error(next.error ?? "自动组稿失败");
      }
    }, 1200);
    return () => window.clearInterval(timer);
  }, [task?.task_id, task?.status]);

  function buildBrief(): AutoCompositionBrief | null {
    const keySellingPoints = sellingPoints
      .split(/[\n,，]/)
      .map((item) => item.trim())
      .filter(Boolean);
    if (
      !product.trim() ||
      !audience.trim() ||
      !platform.trim() ||
      !purpose.trim() ||
      !style.trim() ||
      keySellingPoints.length === 0
    ) {
      toast.error("请补齐产品、人群、平台、目的、风格和卖点");
      return null;
    }
    return {
      product: product.trim(),
      audience: audience.trim(),
      platform: platform.trim(),
      purpose: purpose.trim(),
      style: style.trim(),
      key_selling_points: keySellingPoints,
      constraints: constraints.trim() || null,
      target_length: targetLength.trim() || null,
      metadata: { source_draft_id: draft.id }
    };
  }

  async function handleCreate() {
    const brief = buildBrief();
    if (!brief) return;
    setCreating(true);
    setResult(null);
    try {
      const payload = await createAutoComposition({ brief });
      setTask(payload);
      const parsed = parseAutoCompositionResult(payload);
      if (payload.status === "finished" && parsed) {
        setResult(parsed);
        toast.success("自动组稿已生成");
      } else {
        toast.message(payload.progress?.current_message ?? "自动组稿任务已创建");
      }
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "创建自动组稿任务失败");
    } finally {
      setCreating(false);
    }
  }

  async function handleAccept(candidate: CompositionCandidate) {
    if (!task) return;
    setAcceptingId(candidate.candidate_id);
    try {
      const response = await acceptComposition({
        task_id: task.task_id,
        candidate_id: candidate.candidate_id,
        metadata: { accepted_from_draft_id: draft.id }
      });
      onCompositionAccepted(response.draft);
      toast.success("自动组稿已生成新草稿");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "采纳自动组稿失败");
    } finally {
      setAcceptingId(null);
    }
  }

  return (
    <div className="border-b border-border p-4">
      <div className="mb-3 flex items-center justify-between gap-3">
        <div className="text-sm font-semibold">AI 自动组稿</div>
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
          生成
        </Button>
      </div>
      <div className="space-y-2">
        <Input
          value={product}
          onChange={(event) => setProduct(event.target.value)}
          placeholder="产品 / 主题"
        />
        <div className="grid grid-cols-2 gap-2">
          <Input
            value={platform}
            onChange={(event) => setPlatform(event.target.value)}
            placeholder="平台"
          />
          <Input
            value={purpose}
            onChange={(event) => setPurpose(event.target.value)}
            placeholder="目的"
          />
        </div>
        <Input
          value={audience}
          onChange={(event) => setAudience(event.target.value)}
          placeholder="目标人群"
        />
        <Input
          value={style}
          onChange={(event) => setStyle(event.target.value)}
          placeholder="表达风格"
        />
        <Textarea
          value={sellingPoints}
          onChange={(event) => setSellingPoints(event.target.value)}
          className="min-h-[72px]"
          placeholder="核心卖点；可用换行或逗号分隔"
        />
        <div className="grid grid-cols-2 gap-2">
          <Input
            value={targetLength}
            onChange={(event) => setTargetLength(event.target.value)}
            placeholder="目标长度，可选"
          />
          <Input
            value={constraints}
            onChange={(event) => setConstraints(event.target.value)}
            placeholder="约束，可选"
          />
        </div>
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
            <Badge variant="outline">{result.candidates.length} 个候选</Badge>
            {result.fallback_reason ? (
              <Badge variant="muted">未命中片段，已兜底生成</Badge>
            ) : (
              <Badge variant="outline">
                参考 {result.reference_fragments.length} 个片段
              </Badge>
            )}
            {result.model ? <span>{result.model}</span> : null}
          </div>
          <div className="max-h-[460px] space-y-2 overflow-y-auto pr-1">
            {result.candidates.map((candidate) => (
              <CompositionCandidateCard
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

function CompositionCandidateCard({
  candidate,
  references,
  accepting,
  onAccept
}: {
  candidate: CompositionCandidate;
  references: ReferenceFragmentSummary[];
  accepting: boolean;
  onAccept: () => void;
}) {
  const referenceLookup = new Map(references.map((item) => [item.id, item]));
  return (
    <div className="rounded-lg border border-border bg-background p-3">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="truncate text-sm font-medium">{candidate.title}</div>
          {candidate.strategy ? (
            <div className="mt-1 text-xs leading-5 text-muted-foreground">
              {candidate.strategy}
            </div>
          ) : null}
        </div>
        <Badge variant="outline">{candidate.items.length} 段</Badge>
      </div>
      <div className="mt-3 space-y-2">
        {candidate.items.map((item, index) => (
          <div key={`${item.role}-${index}`} className="rounded-md bg-muted/30 p-2">
            <div className="mb-1 flex flex-wrap gap-1 text-xs text-muted-foreground">
              <span>
                {index + 1}. {formatRoleLabel(item.role)}
              </span>
              <span>· {formatPositionLabel(item.position)}</span>
              <span>· {formatQuoteModeLabel(item.quote_mode)}</span>
            </div>
            <div className="whitespace-pre-wrap text-sm leading-6">{item.text}</div>
            {item.reference_fragment_ids.length > 0 ? (
              <div className="mt-1 text-xs text-muted-foreground">
                来源：
                {item.reference_fragment_ids
                  .map((id) => referenceLookup.get(id)?.text ?? id)
                  .join(" / ")}
              </div>
            ) : null}
          </div>
        ))}
      </div>
      <Button
        size="sm"
        className="mt-3 w-full"
        onClick={onAccept}
        disabled={accepting}
      >
        {accepting ? <Loader2 className="animate-spin" /> : <Plus />}
        采纳为新草稿
      </Button>
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
            <Badge variant="outline">
              下一功能：{formatRoleLabel(result.next_function)}
            </Badge>
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
        <span>{formatRoleLabel(candidate.function)}</span>
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
                  {[
                    formatRoleLabel(item.role),
                    formatPositionLabel(item.position),
                    item.source_display
                  ]
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
          formatOption={formatRoleLabel}
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
                <span>{formatRoleLabel(item.fragment_role)}</span>
                <span>· {formatPositionLabel(item.position)}</span>
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
  formatOption,
  onChange
}: {
  value: string;
  options: string[];
  placeholder: string;
  formatOption?: (value: string) => string;
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
          <option key={option} value={option} label={formatOption?.(option) ?? option} />
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

function parseDraftVideoExportRecord(
  result: TaskResponse["result"]
): DraftVideoExportRecord | null {
  if (!result || typeof result !== "object") return null;
  const payload = result.result;
  if (!payload || typeof payload !== "object") return null;
  const payloadRecord = payload as Record<string, unknown>;
  if (
    typeof result.id !== "string" ||
    typeof result.draft_id !== "string" ||
    typeof result.status !== "string" ||
    typeof payloadRecord.title !== "string" ||
    typeof payloadRecord.title_break !== "string" ||
    typeof payloadRecord.description !== "string" ||
    typeof payloadRecord.script !== "string" ||
    typeof payloadRecord.tts_script !== "string" ||
    !Array.isArray(payloadRecord.hashtags)
  ) {
    return null;
  }
  return {
    id: result.id,
    draft_id: result.draft_id,
    status: result.status,
    result: payload as DraftVideoExportPayload,
    model: typeof result.model === "string" ? result.model : null,
    error: typeof result.error === "string" ? result.error : null,
    metadata:
      result.metadata && typeof result.metadata === "object"
        ? (result.metadata as Record<string, unknown>)
        : {},
    created_at: typeof result.created_at === "string" ? result.created_at : null,
    updated_at: typeof result.updated_at === "string" ? result.updated_at : null
  };
}

function formatVideoExportJson(result: DraftVideoExportPayload): string {
  return JSON.stringify(
    {
      title: result.title,
      title_break: result.title_break,
      description: result.description,
      script: result.script,
      tts_script: result.tts_script,
      hashtags: result.hashtags
    },
    null,
    2
  );
}

function formatExportTime(value?: string | null): string {
  if (!value) return "最新";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "最新";
  return date.toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  });
}

function parseAutoCompositionResult(task: TaskResponse): AutoCompositionResult | null {
  const result = task.result;
  if (!result || typeof result !== "object") return null;
  if (!Array.isArray(result.candidates) || !result.brief) {
    return null;
  }
  return {
    brief: result.brief as AutoCompositionBrief,
    model: typeof result.model === "string" ? result.model : null,
    fallback_reason:
      typeof result.fallback_reason === "string" ? result.fallback_reason : null,
    candidates: result.candidates as CompositionCandidate[],
    reference_fragments: Array.isArray(result.reference_fragments)
      ? (result.reference_fragments as ReferenceFragmentSummary[])
      : []
  };
}
