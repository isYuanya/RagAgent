import { FolderPlus, ListTree, Loader2, Sparkles, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { StatusBadge } from "@/features/StatusBadge";
import { AnalysisView } from "./AnalysisView";
import type { RawCopySummary } from "@/lib/types";

export function RawCopyDetail({
  rawCopy,
  onEditCollections,
  onViewFragments,
  onExtractFragments,
  extractingFragments,
  deleting,
  onDelete
}: {
  rawCopy: RawCopySummary;
  onEditCollections: () => void;
  onViewFragments: () => void;
  onExtractFragments: () => void;
  extractingFragments: boolean;
  deleting?: boolean;
  onDelete: () => void;
}) {
  const analysis = rawCopy.reviewed_analysis ?? rawCopy.auto_analysis ?? null;

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between gap-3 border-b border-border px-5 py-4">
        <div className="flex items-center gap-2">
          <span className="text-base font-semibold">原始文案详情</span>
          <StatusBadge status={rawCopy.status} />
        </div>
        <div className="flex gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={onExtractFragments}
            disabled={extractingFragments || rawCopy.status !== "approved"}
          >
            {extractingFragments ? <Loader2 className="animate-spin" /> : <Sparkles />}
            生成片段
          </Button>
          <Button size="sm" variant="outline" onClick={onViewFragments}>
            <ListTree /> 查看片段
          </Button>
          <Button size="sm" variant="outline" onClick={onEditCollections}>
            <FolderPlus /> 设置集合
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={onDelete}
            disabled={deleting}
            aria-label="删除"
            title={deleting ? "正在删除" : "删除"}
          >
            <Trash2 />
          </Button>
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto p-5">
        <div className="mb-4 space-y-1.5">
          <div className="text-xs font-medium text-muted-foreground">
            所属集合
          </div>
          {rawCopy.collections.length > 0 ? (
            <div className="flex flex-wrap gap-1.5">
              {rawCopy.collections.map((c) => (
                <Badge key={c.id} variant="secondary">
                  {c.name}
                </Badge>
              ))}
            </div>
          ) : (
            <span className="text-sm text-muted-foreground">未归类</span>
          )}
        </div>

        <AnalysisView analysis={analysis} asset={rawCopy} />
      </div>
    </div>
  );
}
