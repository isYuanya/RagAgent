import * as React from "react";
import { toast } from "sonner";
import { Inbox } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from "@/components/ui/select";
import { cn } from "@/lib/utils";
import {
  bulkDeleteRawCopies,
  deleteRawCopy,
  extractFragmentsForRawCopy,
  fetchRawCopiesPage,
  previewBulkDeleteRawCopies
} from "@/lib/api";
import type { KnowledgeCollection, RawCopySummary } from "@/lib/types";
import { StatusBadge } from "@/features/StatusBadge";
import { EmptyState } from "@/features/shared/EmptyState";
import { ConfirmDialog } from "@/features/shared/ConfirmDialog";
import { RawCopyDetail } from "./RawCopyDetail";
import { EditCollectionsDialog } from "./EditCollectionsDialog";

const ALL = "__all__";

export function RawCopiesPanel({
  collections,
  onChanged,
  onViewFragments
}: {
  collections: KnowledgeCollection[];
  onChanged: () => void;
  onViewFragments: (rawCopyId: string) => void;
}) {
  const [items, setItems] = React.useState<RawCopySummary[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [loadingMore, setLoadingMore] = React.useState(false);
  const [page, setPage] = React.useState(1);
  const [total, setTotal] = React.useState(0);
  const [collectionId, setCollectionId] = React.useState(ALL);
  const [selectedId, setSelectedId] = React.useState<string | null>(null);
  const [checkedIds, setCheckedIds] = React.useState<string[]>([]);
  const [editOpen, setEditOpen] = React.useState(false);
  const [deleting, setDeleting] = React.useState<RawCopySummary | null>(null);
  const [deleteBusy, setDeleteBusy] = React.useState(false);
  const [bulkDeleteMode, setBulkDeleteMode] = React.useState<"selected" | "filtered" | null>(null);
  const [bulkDeleteCount, setBulkDeleteCount] = React.useState(0);
  const [bulkDeleteBusy, setBulkDeleteBusy] = React.useState(false);
  const [extractingId, setExtractingId] = React.useState<string | null>(null);

  const selected = items.find((x) => x.id === selectedId) ?? null;
  const hasActiveFilter = collectionId !== ALL;

  const load = React.useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchRawCopiesPage(
        collectionId === ALL ? undefined : collectionId
      );
      setItems(data.items);
      setTotal(data.total);
      setPage(data.page);
      setSelectedId((current) => current ?? data.items[0]?.id ?? null);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "加载失败");
    } finally {
      setLoading(false);
    }
  }, [collectionId]);

  React.useEffect(() => {
    void load();
  }, [load]);

  async function loadMore() {
    setLoadingMore(true);
    try {
      const data = await fetchRawCopiesPage(
        collectionId === ALL ? undefined : collectionId,
        page + 1
      );
      setItems((current) => [...current, ...data.items]);
      setTotal(data.total);
      setPage(data.page);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "加载更多失败");
    } finally {
      setLoadingMore(false);
    }
  }

  function buildBulkPayload(confirm: boolean) {
    return {
      confirm,
      collection_id: collectionId === ALL ? null : collectionId,
      raw_copy_ids: bulkDeleteMode === "selected" ? checkedIds : null
    };
  }

  async function openBulkDelete(mode: "selected" | "filtered") {
    if (mode === "selected" && checkedIds.length === 0) {
      toast.error("请先选择要删除的文案");
      return;
    }
    if (mode === "filtered" && !hasActiveFilter) {
      toast.error("请先选择一个集合筛选，或使用删除所选");
      return;
    }
    setBulkDeleteBusy(true);
    setBulkDeleteMode(mode);
    try {
      const result = await previewBulkDeleteRawCopies({
        confirm: false,
        collection_id: collectionId === ALL ? null : collectionId,
        raw_copy_ids: mode === "selected" ? checkedIds : null
      });
      setBulkDeleteCount(result.matched_count);
    } catch (error) {
      setBulkDeleteMode(null);
      toast.error(error instanceof Error ? error.message : "计算删除数量失败");
    } finally {
      setBulkDeleteBusy(false);
    }
  }

  async function handleBulkDelete() {
    if (!bulkDeleteMode) return;
    setBulkDeleteBusy(true);
    try {
      const result = await bulkDeleteRawCopies(buildBulkPayload(true));
      toast.success(`已删除 ${result.deleted_count} 条`);
      setBulkDeleteMode(null);
      setCheckedIds([]);
      await load();
      onChanged();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "批量删除失败");
    } finally {
      setBulkDeleteBusy(false);
    }
  }

  function applyUpdated(updated: RawCopySummary) {
    setItems((current) =>
      current.map((x) => (x.id === updated.id ? updated : x))
    );
  }

  function removeLocalItem(id: string) {
    const next = items.filter((x) => x.id !== id);
    setItems(next);
    setSelectedId((selected) => {
      if (selected !== id) return selected;
      return next[0]?.id ?? null;
    });
  }

  async function handleDelete() {
    if (!deleting) return;
    const deletingId = deleting.id;
    setDeleteBusy(true);
    try {
      await deleteRawCopy(deletingId);
      toast.success("已删除");
      removeLocalItem(deletingId);
      setDeleting(null);
      onChanged();
    } catch (error) {
      const message = error instanceof Error ? error.message : "删除失败";
      if (message === "Raw copy not found") {
        removeLocalItem(deletingId);
        setDeleting(null);
        toast.info("该文案已删除");
        return;
      }
      toast.error(message);
    } finally {
      setDeleteBusy(false);
    }
  }

  async function handleExtractFragments(rawCopy: RawCopySummary) {
    setExtractingId(rawCopy.id);
    try {
      const result = await extractFragmentsForRawCopy(rawCopy.id);
      if (result.status === "created") {
        toast.success(`已生成 ${result.fragment_count} 条片段`);
      } else if (result.status === "skipped") {
        toast.info(result.message ?? "该文案已存在片段，已跳过生成");
      } else {
        toast.error(result.message ?? "生成片段失败");
      }
      onViewFragments(rawCopy.id);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "生成片段失败");
    } finally {
      setExtractingId(null);
    }
  }

  return (
    <div className="grid min-h-0 grid-cols-1 gap-4 lg:grid-cols-[minmax(300px,380px)_1fr]">
      <Card className="flex min-h-0 flex-col overflow-hidden p-4">
        <div className="mb-3">
          <Select value={collectionId} onValueChange={setCollectionId}>
            <SelectTrigger className="h-8 text-xs">
              <SelectValue placeholder="全部集合" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL}>全部集合</SelectItem>
              {collections.map((c) => (
                <SelectItem key={c.id} value={c.id}>
                  {c.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="mb-3 flex flex-wrap items-center justify-between gap-2 text-xs text-muted-foreground">
          <span>
            已加载 {items.length} / {total}，已选 {checkedIds.length}
          </span>
          <div className="flex gap-2">
            <Button
              size="sm"
              variant="outline"
              onClick={() => void openBulkDelete("selected")}
              disabled={checkedIds.length === 0 || bulkDeleteBusy}
            >
              删除所选
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={() => void openBulkDelete("filtered")}
              disabled={!hasActiveFilter || total === 0 || bulkDeleteBusy}
            >
              删除筛选结果
            </Button>
          </div>
        </div>

        <div className="min-h-0 flex-1 space-y-2 overflow-y-auto pr-1">
          {loading ? (
            Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-16 w-full rounded-lg" />
            ))
          ) : items.length === 0 ? (
            <EmptyState
              icon={<Inbox className="size-8" />}
              title="没有原始文案"
              hint="CSV 导入成功后会自动出现在这里。"
            />
          ) : (
            items.map((item) => {
              const title =
                item.auto_analysis?.topic || item.source_text.slice(0, 28);
              return (
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
                    <span className="flex min-w-0 items-start gap-2">
                      <input
                        type="checkbox"
                        className="mt-0.5 size-4"
                        checked={checkedIds.includes(item.id)}
                        onClick={(event) => event.stopPropagation()}
                        onChange={(event) => {
                          setCheckedIds((current) =>
                            event.target.checked
                              ? [...current, item.id]
                              : current.filter((id) => id !== item.id)
                          );
                        }}
                      />
                      <span className="line-clamp-1 text-sm font-medium">
                        {title}
                      </span>
                    </span>
                    <StatusBadge status={item.status} />
                  </div>
                  <div className="mt-1 line-clamp-1 text-xs text-muted-foreground">
                    {item.author_name ?? "未标作者"} ·{" "}
                    {item.platform ?? "未标平台"} ·{" "}
                    {item.collections.length > 0
                      ? item.collections.map((c) => c.name).join("、")
                      : "未归类"}
                  </div>
                </button>
              );
            })
          )}
        </div>
        {!loading && items.length < total ? (
          <Button
            className="mt-3 w-full"
            size="sm"
            variant="outline"
            onClick={() => void loadMore()}
            disabled={loadingMore}
          >
            {loadingMore ? "加载中..." : "加载更多"}
          </Button>
        ) : null}
      </Card>

      <Card className="flex min-h-0 flex-col overflow-hidden p-0">
        {selected ? (
          <RawCopyDetail
            rawCopy={selected}
            onEditCollections={() => setEditOpen(true)}
            onViewFragments={() => onViewFragments(selected.id)}
            onExtractFragments={() => void handleExtractFragments(selected)}
            extractingFragments={extractingId === selected.id}
            deleting={deleteBusy && deleting?.id === selected.id}
            onDelete={() => setDeleting(selected)}
          />
        ) : (
          <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
            选择一条原始文案查看详情。
          </div>
        )}
      </Card>

      <EditCollectionsDialog
        open={editOpen}
        onOpenChange={setEditOpen}
        rawCopy={selected}
        collections={collections}
        onSaved={applyUpdated}
      />
      <ConfirmDialog
        open={deleting !== null}
        onOpenChange={(open) => !open && setDeleting(null)}
        title="删除原始文案"
        description="删除后该条目不再显示。"
        busy={deleteBusy}
        onConfirm={handleDelete}
      />
      <ConfirmDialog
        open={bulkDeleteMode !== null}
        onOpenChange={(open) => !open && setBulkDeleteMode(null)}
        title="批量删除原始文案"
        description={`将删除 ${bulkDeleteCount} 条匹配文案，并同步清理关联数据和向量。`}
        busy={bulkDeleteBusy}
        onConfirm={handleBulkDelete}
      />
    </div>
  );
}
