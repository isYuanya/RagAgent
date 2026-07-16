import * as React from "react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { fetchCollectionsPage, fetchKnowledgeStats } from "@/lib/api";
import type { KnowledgeCollection, KnowledgeStatsResponse } from "@/lib/types";
import { CollectionsPanel } from "./CollectionsPanel";
import { RawCopiesPanel } from "./RawCopiesPanel";
import { AnalysesPanel } from "./AnalysesPanel";
import { ManualKnowledgePanel } from "./ManualKnowledgePanel";
import { FragmentsPanel } from "./FragmentsPanel";

type KbTab =
  | "collections"
  | "raw-copies"
  | "analyses"
  | "templates"
  | "fragments";

const TABS: Array<{ key: KbTab; label: string }> = [
  { key: "collections", label: "集合" },
  { key: "raw-copies", label: "原始文案库" },
  { key: "analyses", label: "结构化拆解库" },
  { key: "templates", label: "模板库" },
  { key: "fragments", label: "片段库" }
];

export function KnowledgeView({
  headerAction
}: {
  headerAction?: React.ReactNode;
}) {
  const [tab, setTab] = React.useState<KbTab>("collections");
  const [collections, setCollections] = React.useState<KnowledgeCollection[]>(
    []
  );
  const [collectionsTotal, setCollectionsTotal] = React.useState(0);
  const [collectionsLoading, setCollectionsLoading] = React.useState(true);
  const [stats, setStats] = React.useState<KnowledgeStatsResponse | null>(null);
  const [fragmentSourceCopyId, setFragmentSourceCopyId] = React.useState<
    string | undefined
  >();

  const loadCollections = React.useCallback(async () => {
    try {
      const payload = await fetchCollectionsPage(1, 20);
      setCollections(payload.items);
      setCollectionsTotal(payload.total);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "加载集合失败");
    } finally {
      setCollectionsLoading(false);
    }
  }, []);

  const loadStats = React.useCallback(async () => {
    try {
      setStats(await fetchKnowledgeStats());
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "加载知识库统计失败");
    }
  }, []);

  const refreshKnowledge = React.useCallback(() => {
    void loadCollections();
    void loadStats();
  }, [loadCollections, loadStats]);

  React.useEffect(() => {
    refreshKnowledge();
  }, [refreshKnowledge]);

  function viewFragmentsForRawCopy(rawCopyId: string) {
    setFragmentSourceCopyId(rawCopyId);
    setTab("fragments");
  }

  return (
    <main className="flex min-w-0 flex-1 flex-col">
      <header className="flex items-center justify-between gap-4 border-b border-border px-6 py-4">
        <div>
          <h1 className="text-lg font-semibold">知识库</h1>
          <p className="text-sm text-muted-foreground">
            管理集合，浏览沉淀的原始文案、结构化拆解和人工维护素材。
          </p>
        </div>
        <div className="flex shrink-0 flex-wrap items-center justify-end gap-2">
          {headerAction}
          <div className="flex max-w-3xl flex-wrap justify-end gap-1 rounded-lg border border-border bg-muted/40 p-1">
            {TABS.map((item) => (
              <button
                key={item.key}
                type="button"
                onClick={() => setTab(item.key)}
                className={cn(
                  "rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
                  tab === item.key
                    ? "bg-background text-foreground shadow-sm"
                    : "text-muted-foreground hover:text-foreground"
                )}
              >
                {item.label}
              </button>
            ))}
          </div>
        </div>
      </header>

      <div className="min-h-0 flex-1 overflow-y-auto p-6">
        {tab === "collections" ? (
          <CollectionsPanel
            collections={collections}
            total={collectionsTotal}
            loading={collectionsLoading}
            onChanged={refreshKnowledge}
          />
        ) : tab === "raw-copies" ? (
          <RawCopiesPanel
            collections={collections}
            onChanged={refreshKnowledge}
            onViewFragments={viewFragmentsForRawCopy}
          />
        ) : tab === "analyses" ? (
          <AnalysesPanel onChanged={refreshKnowledge} />
        ) : tab === "fragments" ? (
          <FragmentsPanel sourceCopyId={fragmentSourceCopyId} onChanged={refreshKnowledge} />
        ) : (
          <ManualKnowledgePanel kind={tab} onChanged={refreshKnowledge} />
        )}
      </div>
      <KnowledgeStatsPanel stats={stats} />
    </main>
  );
}

function KnowledgeStatsPanel({
  stats
}: {
  stats: KnowledgeStatsResponse | null;
}) {
  const items = [
    ["集合", stats?.collections],
    ["原始文案", stats?.raw_copies],
    ["结构化拆解", stats?.analyses],
    ["模板", stats?.templates],
    ["片段", stats?.fragments]
  ];
  return (
    <div className="pointer-events-none fixed bottom-8 left-4 z-20 rounded-md border border-border bg-background/95 px-3 py-2 text-xs shadow-sm">
      <div className="mb-1 font-medium text-foreground">知识库资产</div>
      <div className="grid grid-cols-[auto_auto] gap-x-3 gap-y-1 text-muted-foreground">
        {items.map(([label, value]) => (
          <React.Fragment key={label}>
            <span>{label}</span>
            <span className="text-right text-foreground">{value ?? "..."}</span>
          </React.Fragment>
        ))}
      </div>
    </div>
  );
}
