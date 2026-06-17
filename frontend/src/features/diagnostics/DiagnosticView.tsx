import * as React from "react";
import {
  ChevronDown,
  ChevronUp,
  FileText,
  Loader2,
  Save,
  Search,
  ShieldCheck
} from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { EmptyState } from "@/features/shared/EmptyState";
import {
  acceptDiagnosticRewrite,
  createCopyDiagnosis,
  fetchDraft,
  fetchDrafts,
  fetchTask
} from "@/lib/api";
import { cn } from "@/lib/utils";
import type {
  CopyDiagnosisResult,
  DraftDetail,
  DraftSummary,
  TaskResponse
} from "@/lib/types";

export function DiagnosticView({
  headerAction
}: {
  headerAction?: React.ReactNode;
}) {
  const [drafts, setDrafts] = React.useState<DraftSummary[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [selectedId, setSelectedId] = React.useState<string | null>(null);
  const [detail, setDetail] = React.useState<DraftDetail | null>(null);
  const [detailLoading, setDetailLoading] = React.useState(false);

  const loadDrafts = React.useCallback(async (preferredId?: string | null) => {
    setLoading(true);
    try {
      const items = (await fetchDrafts("all")).filter(
        (item) => item.status !== "archived"
      );
      setDrafts(items);
      setSelectedId((current) => preferredId ?? current ?? items[0]?.id ?? null);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "加载草稿失败");
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    void loadDrafts();
  }, [loadDrafts]);

  React.useEffect(() => {
    if (!selectedId) {
      setDetail(null);
      return;
    }
    setDetailLoading(true);
    fetchDraft(selectedId)
      .then(setDetail)
      .catch((error) => {
        toast.error(error instanceof Error ? error.message : "加载草稿详情失败");
        setDetail(null);
      })
      .finally(() => setDetailLoading(false));
  }, [selectedId]);

  function handleDraftUpdated(next: DraftDetail) {
    setDetail(next);
    setDrafts((current) =>
      current.map((item) =>
        item.id === next.id
          ? {
              id: next.id,
              title: next.title,
              goal: next.goal,
              audience: next.audience,
              platform: next.platform,
              purpose: next.purpose,
              status: next.status,
              current_text: next.current_text,
              item_count: next.item_count,
              metadata: next.metadata
            }
          : item
      )
    );
  }

  return (
    <main className="flex min-w-0 flex-1 flex-col">
      <header className="flex items-center justify-between gap-4 border-b border-border px-6 py-4">
        <div>
          <h1 className="text-lg font-semibold">文案诊断</h1>
          <p className="text-sm text-muted-foreground">
            组稿完成后，在这里对草稿进行质量诊断、合规检查和原创改写。
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-2">{headerAction}</div>
      </header>

      <div className="grid min-h-0 flex-1 grid-cols-1 gap-4 p-6 lg:grid-cols-[340px_minmax(0,1fr)]">
        <Card className="flex min-h-0 flex-col overflow-hidden p-4">
          <div className="mb-3 text-sm font-semibold">可诊断草稿</div>
          <DraftDiagnosisList
            drafts={drafts}
            loading={loading}
            selectedId={selectedId}
            onSelect={setSelectedId}
          />
        </Card>

        <Card className="flex min-h-0 flex-col overflow-hidden p-0">
          {detailLoading ? (
            <div className="space-y-4 p-5">
              <Skeleton className="h-10 w-1/2 rounded-lg" />
              <Skeleton className="h-32 w-full rounded-lg" />
              <Skeleton className="h-48 w-full rounded-lg" />
            </div>
          ) : detail ? (
            <DiagnosisWorkspace draft={detail} onDraftUpdated={handleDraftUpdated} />
          ) : (
            <div className="flex h-full items-center justify-center p-6">
              <EmptyState
                icon={<ShieldCheck className="size-8" />}
                title="请选择草稿"
                hint="从左侧选择组稿后的草稿，再发起文案诊断。"
              />
            </div>
          )}
        </Card>
      </div>
    </main>
  );
}

function DraftDiagnosisList({
  drafts,
  loading,
  selectedId,
  onSelect
}: {
  drafts: DraftSummary[];
  loading: boolean;
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  const [query, setQuery] = React.useState("");
  const filtered = drafts.filter((item) => {
    const haystack = `${item.title} ${item.current_text} ${item.platform ?? ""} ${item.purpose ?? ""}`;
    return haystack.toLowerCase().includes(query.trim().toLowerCase());
  });

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="relative mb-3">
        <Search className="pointer-events-none absolute left-2 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground" />
        <Input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          className="pl-7"
          placeholder="搜索草稿"
        />
      </div>
      <div className="min-h-0 flex-1 space-y-2 overflow-y-auto pr-1">
        {loading ? (
          Array.from({ length: 6 }).map((_, index) => (
            <Skeleton key={index} className="h-20 w-full rounded-lg" />
          ))
        ) : filtered.length === 0 ? (
          <EmptyState
            icon={<FileText className="size-8" />}
            title="暂无可诊断草稿"
            hint="先到草稿工作台完成组稿，再回到这里诊断。"
          />
        ) : (
          filtered.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => onSelect(item.id)}
              className={cn(
                "w-full rounded-lg border bg-card p-3 text-left transition-colors hover:border-primary/40 hover:bg-accent/40",
                selectedId === item.id &&
                  "border-primary bg-accent/60 ring-1 ring-primary/20"
              )}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <div className="truncate text-sm font-medium">{item.title}</div>
                  <div className="mt-1 line-clamp-2 text-xs text-muted-foreground">
                    {item.current_text || item.goal || "暂无正文"}
                  </div>
                </div>
                <Badge variant="outline">{item.item_count} 段</Badge>
              </div>
              <div className="mt-2 flex flex-wrap gap-1 text-xs text-muted-foreground">
                {item.platform ? <span>{item.platform}</span> : null}
                {item.purpose ? <span>· {item.purpose}</span> : null}
                {item.audience ? <span>· {item.audience}</span> : null}
              </div>
            </button>
          ))
        )}
      </div>
    </div>
  );
}

function DiagnosisWorkspace({
  draft,
  onDraftUpdated
}: {
  draft: DraftDetail;
  onDraftUpdated: (draft: DraftDetail) => void;
}) {
  const [constraints, setConstraints] = React.useState("");
  const [task, setTask] = React.useState<TaskResponse | null>(null);
  const [result, setResult] = React.useState<CopyDiagnosisResult | null>(null);
  const [creating, setCreating] = React.useState(false);
  const [acceptingId, setAcceptingId] = React.useState<string | null>(null);
  const [previewExpanded, setPreviewExpanded] = React.useState(false);
  const isRunning = task ? ["queued", "running"].includes(task.status) : false;

  React.useEffect(() => {
    setTask(null);
    setResult(null);
    setConstraints("");
    setPreviewExpanded(false);
  }, [draft.id]);

  React.useEffect(() => {
    if (!task || !["queued", "running"].includes(task.status)) return;
    const timer = window.setInterval(async () => {
      const next = await fetchTask(task.task_id);
      if (!next) return;
      setTask(next);
      if (next.status === "finished") {
        const parsed = parseCopyDiagnosisResult(next);
        setResult(parsed);
        if (parsed) toast.success("文案诊断已完成");
      }
      if (next.status === "failed") {
        toast.error(next.error ?? "文案诊断失败");
      }
    }, 1200);
    return () => window.clearInterval(timer);
  }, [task?.task_id, task?.status]);

  async function handleCreate() {
    if (!draft.current_text.trim()) {
      toast.error("当前草稿没有正文，无法诊断");
      return;
    }
    setCreating(true);
    setResult(null);
    try {
      const payload = await createCopyDiagnosis({
        draft_id: draft.id,
        platform: draft.platform,
        audience: draft.audience,
        purpose: draft.purpose,
        constraints: splitInputList(constraints),
        rewrite_modes: ["conservative", "conversion", "compliance_safe"],
        metadata: { source: "diagnostic_view" }
      });
      setTask(payload);
      const parsed = parseCopyDiagnosisResult(payload);
      if (payload.status === "finished" && parsed) {
        setResult(parsed);
        toast.success("文案诊断已完成");
      } else {
        toast.message(payload.progress?.current_message ?? "文案诊断任务已创建");
      }
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "创建文案诊断任务失败");
    } finally {
      setCreating(false);
    }
  }

  async function handleAccept(
    candidate: CopyDiagnosisResult["rewrite_candidates"][number]
  ) {
    if (!task) return;
    setAcceptingId(candidate.candidate_id);
    try {
      const response = await acceptDiagnosticRewrite({
        draft_id: draft.id,
        task_id: task.task_id,
        candidate_id: candidate.candidate_id,
        label: candidate.title || "AI 诊断改写",
        metadata: { rewrite_mode: candidate.mode }
      });
      onDraftUpdated(response.draft);
      toast.success("诊断改写已采纳并保存版本");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "采纳诊断改写失败");
    } finally {
      setAcceptingId(null);
    }
  }

  return (
    <div className="grid min-h-0 flex-1 grid-cols-1 lg:grid-cols-[minmax(0,1fr)_420px]">
      <section className="min-h-0 overflow-y-auto border-r border-border p-5">
        <div className="sticky top-0 z-10 rounded-lg border border-border bg-card p-3 shadow-sm">
        <div className="mb-3 flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h2 className="truncate text-base font-semibold">{draft.title}</h2>
            <div className="mt-1 flex flex-wrap gap-1 text-xs text-muted-foreground">
              {draft.platform ? <span>{draft.platform}</span> : null}
              {draft.purpose ? <span>· {draft.purpose}</span> : null}
              {draft.audience ? <span>· {draft.audience}</span> : null}
            </div>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <Badge variant="outline">{draft.item_count} 段</Badge>
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
        </div>
        <div
          className={cn(
            "overflow-y-auto whitespace-pre-wrap rounded-md bg-muted/30 p-3 text-sm leading-7",
            previewExpanded ? "max-h-[calc(100vh-220px)]" : "max-h-56"
          )}
        >
          {draft.current_text || "暂无正文"}
        </div>
        </div>
      </section>

      <section className="min-h-0 overflow-y-auto p-5">
        <div className="mb-3 flex items-center justify-between gap-3">
          <div className="text-sm font-semibold">诊断控制台</div>
          <Button onClick={handleCreate} disabled={creating || isRunning}>
            {creating || isRunning ? (
              <Loader2 className="animate-spin" />
            ) : (
              <ShieldCheck />
            )}
            开始诊断
          </Button>
        </div>
        <Textarea
          value={constraints}
          onChange={(event) => setConstraints(event.target.value)}
          className="min-h-[80px]"
          placeholder="可选约束，例如：不要绝对承诺、语气更口播、CTA 更轻"
        />

        {task?.progress ? (
          <div className="mt-3 rounded-md border border-border bg-muted/30 p-3">
            <div className="mb-2 flex items-center justify-between gap-2 text-xs text-muted-foreground">
              <span>{task.progress.current_message ?? task.progress.phase}</span>
              <span>{task.progress.percent}%</span>
            </div>
            <Progress value={task.progress.percent} />
            {task.progress.model ? (
              <div className="mt-2 text-xs text-muted-foreground">
                模型：{task.progress.model}
              </div>
            ) : null}
          </div>
        ) : null}

        {result ? (
          <DiagnosisResultView
            result={result}
            acceptingId={acceptingId}
            onAccept={handleAccept}
          />
        ) : null}
      </section>
    </div>
  );
}

function DiagnosisResultView({
  result,
  acceptingId,
  onAccept
}: {
  result: CopyDiagnosisResult;
  acceptingId: string | null;
  onAccept: (
    candidate: CopyDiagnosisResult["rewrite_candidates"][number]
  ) => void;
}) {
  return (
    <div className="mt-4 space-y-3">
      <div className="rounded-lg border border-border bg-background p-3">
        <div className="mb-2 flex flex-wrap items-center gap-2">
          <Badge variant={diagnosticBadgeVariant(result.overall_level)}>
            {diagnosticLevelLabel(result.overall_level)}
          </Badge>
          {result.model ? (
            <span className="text-xs text-muted-foreground">{result.model}</span>
          ) : null}
        </div>
        <div className="text-sm leading-6">{result.summary}</div>
      </div>

      <div className="grid gap-2">
        {result.dimensions.map((item) => (
          <div key={item.dimension} className="rounded-md border border-border bg-background p-2">
            <div className="mb-1 flex items-center justify-between gap-2">
              <span className="text-xs font-medium">
                {diagnosticDimensionLabel(item.dimension)}
              </span>
              <Badge variant={diagnosticBadgeVariant(item.level)}>
                {diagnosticLevelLabel(item.level)}
              </Badge>
            </div>
            <div className="text-xs leading-5 text-muted-foreground">
              {item.reason}
            </div>
            <div className="mt-1 text-xs leading-5">{item.suggestion}</div>
          </div>
        ))}
      </div>

      {result.sentence_issues.length > 0 ? (
        <details className="rounded-lg border border-border bg-background p-3 text-sm">
          <summary className="cursor-pointer font-medium">句子级问题</summary>
          <div className="mt-3 space-y-2">
            {result.sentence_issues.map((issue, index) => (
              <div key={`${issue.text}-${index}`} className="rounded-md bg-muted/30 p-2">
                <Badge variant={diagnosticBadgeVariant(issue.level)}>
                  {diagnosticLevelLabel(issue.level)}
                </Badge>
                <div className="mt-2 text-xs leading-5 text-muted-foreground">
                  原句：{issue.text}
                </div>
                <div className="mt-1 text-xs leading-5">{issue.reason}</div>
                <div className="mt-1 text-xs leading-5 text-primary">
                  替换：{issue.replacement}
                </div>
              </div>
            ))}
          </div>
        </details>
      ) : null}

      <div className="space-y-2">
        {result.rewrite_candidates.map((candidate) => (
          <div key={candidate.candidate_id} className="rounded-lg border border-border bg-background p-3">
            <div className="mb-2 flex items-start justify-between gap-2">
              <div className="min-w-0">
                <div className="truncate text-sm font-medium">{candidate.title}</div>
                <div className="mt-1 text-xs text-muted-foreground">
                  {rewriteModeLabel(candidate.mode)}
                </div>
              </div>
              <Button
                size="sm"
                onClick={() => onAccept(candidate)}
                disabled={acceptingId === candidate.candidate_id}
              >
                {acceptingId === candidate.candidate_id ? (
                  <Loader2 className="animate-spin" />
                ) : (
                  <Save />
                )}
                采纳
              </Button>
            </div>
            <div className="whitespace-pre-wrap text-sm leading-6">{candidate.text}</div>
            {candidate.reason ? (
              <div className="mt-2 rounded-md bg-muted/30 p-2 text-xs leading-5 text-muted-foreground">
                {candidate.reason}
              </div>
            ) : null}
          </div>
        ))}
      </div>
    </div>
  );
}

function parseCopyDiagnosisResult(task: TaskResponse): CopyDiagnosisResult | null {
  const result = task.result;
  if (!result || typeof result !== "object") return null;
  if (
    !result.source ||
    typeof result.summary !== "string" ||
    typeof result.overall_level !== "string" ||
    !Array.isArray(result.dimensions) ||
    !Array.isArray(result.rewrite_candidates)
  ) {
    return null;
  }
  return {
    source: result.source as CopyDiagnosisResult["source"],
    summary: result.summary,
    overall_level: result.overall_level as CopyDiagnosisResult["overall_level"],
    dimensions: result.dimensions as CopyDiagnosisResult["dimensions"],
    sentence_issues: Array.isArray(result.sentence_issues)
      ? (result.sentence_issues as CopyDiagnosisResult["sentence_issues"])
      : [],
    rewrite_candidates:
      result.rewrite_candidates as CopyDiagnosisResult["rewrite_candidates"],
    risk_warnings: Array.isArray(result.risk_warnings)
      ? (result.risk_warnings as CopyDiagnosisResult["risk_warnings"])
      : [],
    model: typeof result.model === "string" ? result.model : null
  };
}

function splitInputList(value: string): string[] {
  return value
    .split(/[\n,，;；]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function diagnosticLevelLabel(level: string): string {
  const labels: Record<string, string> = {
    weak: "弱",
    fair: "一般",
    strong: "强",
    risk: "有风险",
    high_risk: "高风险"
  };
  return labels[level] ?? level;
}

function diagnosticBadgeVariant(level: string) {
  if (level === "high_risk") return "destructive" as const;
  if (level === "risk" || level === "weak") return "secondary" as const;
  if (level === "strong") return "success" as const;
  return "outline" as const;
}

function diagnosticDimensionLabel(dimension: string): string {
  const labels: Record<string, string> = {
    opening_attractiveness: "开头吸引力",
    audience_clarity: "人群清晰度",
    pain_specificity: "痛点具体度",
    context_coherence: "上下文连贯性",
    emotional_resonance: "情绪共鸣",
    spoken_naturalness: "口播自然度",
    conversion_action: "转化动作",
    originality_risk: "原创风险",
    compliance_risk: "合规风险"
  };
  return labels[dimension] ?? dimension;
}

function rewriteModeLabel(mode: string): string {
  const labels: Record<string, string> = {
    conservative: "保守改写",
    conversion: "转化增强",
    compliance_safe: "合规安全"
  };
  return labels[mode] ?? mode;
}
