import * as React from "react";
import { toast } from "sonner";
import { Sparkles, Trash2 } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { fetchAnalysesPage, deleteAnalysis } from "@/lib/api";
import type { AnalysisSummary } from "@/lib/types";
import { StatusBadge } from "@/features/StatusBadge";
import { EmptyState } from "@/features/shared/EmptyState";
import { ConfirmDialog } from "@/features/shared/ConfirmDialog";
import { AnalysisView } from "./AnalysisView";

export function AnalysesPanel({ onChanged }: { onChanged: () => void }) {
  const [items, setItems] = React.useState<AnalysisSummary[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [loadingMore, setLoadingMore] = React.useState(false);
  const [page, setPage] = React.useState(1);
  const [total, setTotal] = React.useState(0);
  const [selectedId, setSelectedId] = React.useState<string | null>(null);
  const [deleting, setDeleting] = React.useState<AnalysisSummary | null>(null);
  const [deleteBusy, setDeleteBusy] = React.useState(false);

  const selected = items.find((x) => x.id === selectedId) ?? null;

  const load = React.useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchAnalysesPage();
      setItems(data.items);
      setTotal(data.total);
      setPage(data.page);
      setSelectedId((current) => current ?? data.items[0]?.id ?? null);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "加载失败");
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    void load();
  }, [load]);

  async function loadMore() {
    setLoadingMore(true);
    try {
      const data = await fetchAnalysesPage(page + 1);
      setItems((current) => [...current, ...data.items]);
      setTotal(data.total);
      setPage(data.page);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "加载更多失败");
    } finally {
      setLoadingMore(false);
    }
  }

  async function handleDelete() {
    if (!deleting) return;
    setDeleteBusy(true);
    try {
      await deleteAnalysis(deleting.id);
      toast.success("已删除");
      setItems((current) => current.filter((x) => x.id !== deleting.id));
      if (selectedId === deleting.id) setSelectedId(null);
      setDeleting(null);
      onChanged();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "删除失败");
    } finally {
      setDeleteBusy(false);
    }
  }

  return (
    <div className="grid min-h-0 grid-cols-1 gap-4 lg:grid-cols-[minmax(300px,380px)_1fr]">
      <Card className="flex min-h-0 flex-col overflow-hidden p-4">
        <div className="mb-3 text-sm font-semibold">拆解记录（{items.length}）</div>
        <div className="min-h-0 flex-1 space-y-2 overflow-y-auto pr-1">
          {loading ? (
            Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-14 w-full rounded-lg" />
            ))
          ) : items.length === 0 ? (
            <EmptyState
              icon={<Sparkles className="size-8" />}
              title="没有拆解记录"
              hint="CSV 导入并完成 LLM 拆解后会出现在这里。"
            />
          ) : (
            items.map((item) => {
              const analysis = item.reviewed_analysis ?? item.auto_analysis;
              const title = analysis?.topic || `拆解 ${item.id.slice(0, 8)}`;
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
                    <span className="line-clamp-1 text-sm font-medium">
                      {title}
                    </span>
                    <StatusBadge status={item.status} />
                  </div>
                  <div className="mt-1 truncate text-xs text-muted-foreground">
                    raw_copy_id: {item.raw_copy_id.slice(0, 8)}…
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
          <div className="flex h-full flex-col">
            <div className="flex items-center justify-between gap-3 border-b border-border px-5 py-4">
              <div className="flex items-center gap-2">
                <span className="text-base font-semibold">拆解详情</span>
                <StatusBadge status={selected.status} />
              </div>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setDeleting(selected)}
                aria-label="删除"
              >
                <Trash2 />
              </Button>
            </div>
            <div className="min-h-0 flex-1 overflow-y-auto p-5">
              <AnalysisView
                analysis={selected.reviewed_analysis ?? selected.auto_analysis ?? null}
              />
            </div>
          </div>
        ) : (
          <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
            选择一条拆解记录查看详情。
          </div>
        )}
      </Card>

      <ConfirmDialog
        open={deleting !== null}
        onOpenChange={(open) => !open && setDeleting(null)}
        title="删除拆解记录"
        description="删除后该记录不再显示。"
        busy={deleteBusy}
        onConfirm={handleDelete}
      />
    </div>
  );
}
