import * as React from "react";
import {
  Bot,
  CheckCircle2,
  Clock3,
  FileText,
  Loader2,
  Play,
  RefreshCw,
  Sparkles,
  XCircle
} from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { EmptyState } from "@/features/shared/EmptyState";
import {
  createSmartCompositionRun,
  fetchSmartCompositionRun,
  fetchSmartCompositionRuns,
  fetchSmartCompositionOptions,
  prefillSmartCompositionBrief
} from "@/lib/api";
import { cn } from "@/lib/utils";
import type {
  SmartCompositionBrief,
  SmartCompositionMode,
  SmartCompositionOptions,
  SmartCompositionRunDetail,
  SmartCompositionRunSummary,
  SmartCompositionStep
} from "@/lib/types";

type BriefForm = {
  product: string;
  audience: string;
  platform: string;
  purpose: string;
  style: string;
  sellingPoints: string;
  constraints: string;
  targetLength: string;
  extraNotes: string;
  collectionIds: string[];
};

const emptyForm: BriefForm = {
  product: "",
  audience: "new_users",
  platform: "xhs",
  purpose: "conversion",
  style: "practical",
  sellingPoints: "",
  constraints: "",
  targetLength: "",
  extraNotes: "",
  collectionIds: []
};

const STEP_LABELS: Record<string, string> = {
  brief_prefill: "需求整理",
  knowledge_retrieval: "检索素材",
  composition_generation: "生成组稿",
  composition_selection: "选择组稿",
  initial_draft_save: "保存初稿",
  diagnosis: "文案诊断",
  rewrite_selection: "选择改写",
  final_draft_save: "保存终稿"
};

export function SmartCompositionView({
  headerAction
}: {
  headerAction?: React.ReactNode;
}) {
  const [options, setOptions] = React.useState<SmartCompositionOptions | null>(null);
  const [optionsLoading, setOptionsLoading] = React.useState(true);
  const [history, setHistory] = React.useState<SmartCompositionRunSummary[]>([]);
  const [historyLoading, setHistoryLoading] = React.useState(true);
  const [mode, setMode] = React.useState<SmartCompositionMode>("auto");
  const [form, setForm] = React.useState<BriefForm>(emptyForm);
  const [prefillText, setPrefillText] = React.useState("");
  const [prefilling, setPrefilling] = React.useState(false);
  const [running, setRunning] = React.useState(false);
  const [selectedRun, setSelectedRun] = React.useState<SmartCompositionRunDetail | null>(null);

  const loadHistory = React.useCallback(async () => {
    setHistoryLoading(true);
    try {
      setHistory(await fetchSmartCompositionRuns());
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "加载智能组稿历史失败");
    } finally {
      setHistoryLoading(false);
    }
  }, []);

  React.useEffect(() => {
    fetchSmartCompositionOptions()
      .then(setOptions)
      .catch((error) => {
        toast.error(error instanceof Error ? error.message : "加载智能组稿选项失败");
      })
      .finally(() => setOptionsLoading(false));
    void loadHistory();
  }, [loadHistory]);

  async function handlePrefill() {
    const text = prefillText.trim();
    if (!text) return;
    setPrefilling(true);
    try {
      const payload = await prefillSmartCompositionBrief(text);
      setForm(formFromBrief(payload.brief));
      toast.success(`已解析需求，置信度 ${Math.round(payload.confidence * 100)}%`);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "解析组稿需求失败");
    } finally {
      setPrefilling(false);
    }
  }

  async function handleRun() {
    const brief = briefFromForm(form);
    if (!brief.product.trim()) {
      toast.error("请先填写产品或主题");
      return;
    }
    if (brief.key_selling_points.length === 0) {
      toast.error("请至少填写一个卖点");
      return;
    }
    setRunning(true);
    try {
      const run = await createSmartCompositionRun({ mode, brief });
      setSelectedRun(run);
      await loadHistory();
      if (run.status === "finished") {
        toast.success("智能组稿已完成");
      } else if (run.status === "waiting_for_user") {
        toast.message("已生成候选，等待分步确认");
      }
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "启动智能组稿失败");
    } finally {
      setRunning(false);
    }
  }

  async function openRun(id: string) {
    try {
      setSelectedRun(await fetchSmartCompositionRun(id));
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "加载智能组稿详情失败");
    }
  }

  return (
    <main className="flex min-w-0 flex-1 flex-col">
      <header className="flex items-center justify-between gap-4 border-b border-border px-6 py-4">
        <div>
          <h1 className="text-lg font-semibold">智能组稿助手</h1>
          <p className="text-sm text-muted-foreground">
            从需求、素材检索、组稿、诊断到终稿保存的一键流程。
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-2">{headerAction}</div>
      </header>

      <div className="grid min-h-0 flex-1 grid-cols-1 gap-4 p-6 xl:grid-cols-[420px_minmax(0,1fr)]">
        <div className="min-h-0 space-y-4 overflow-y-auto pr-1">
          <Card className="p-4">
            <div className="mb-3 flex items-center justify-between gap-3">
              <div className="flex items-center gap-2 text-sm font-semibold">
                <Bot className="size-4" />
                组稿需求
              </div>
              <ModeSwitch mode={mode} onChange={setMode} />
            </div>

            <div className="space-y-4">
              <div className="space-y-2">
                <Label>自然语言预填</Label>
                <div className="flex gap-2">
                  <Input
                    value={prefillText}
                    onChange={(event) => setPrefillText(event.target.value)}
                    placeholder="例如：给小红书新用户写一篇护肤顺序转化文案"
                  />
                  <Button
                    type="button"
                    variant="outline"
                    disabled={prefilling || !prefillText.trim()}
                    onClick={handlePrefill}
                  >
                    {prefilling ? <Loader2 className="size-4 animate-spin" /> : <Sparkles className="size-4" />}
                  </Button>
                </div>
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                <Field label="产品或主题">
                  <Input
                    value={form.product}
                    onChange={(event) => setForm({ ...form, product: event.target.value })}
                    placeholder="护肤顺序"
                  />
                </Field>
                <SelectField
                  label="目标人群"
                  value={form.audience}
                  options={options?.audiences}
                  loading={optionsLoading}
                  onChange={(audience) => setForm({ ...form, audience })}
                />
                <SelectField
                  label="发布平台"
                  value={form.platform}
                  options={options?.platforms}
                  loading={optionsLoading}
                  onChange={(platform) => setForm({ ...form, platform })}
                />
                <SelectField
                  label="内容目的"
                  value={form.purpose}
                  options={options?.purposes}
                  loading={optionsLoading}
                  onChange={(purpose) => setForm({ ...form, purpose })}
                />
                <SelectField
                  label="表达风格"
                  value={form.style}
                  options={options?.styles}
                  loading={optionsLoading}
                  onChange={(style) => setForm({ ...form, style })}
                />
                <Field label="目标长度">
                  <Input
                    value={form.targetLength}
                    onChange={(event) => setForm({ ...form, targetLength: event.target.value })}
                    placeholder="300 字以内"
                  />
                </Field>
              </div>

              <Field label="关键卖点">
                <Textarea
                  value={form.sellingPoints}
                  onChange={(event) => setForm({ ...form, sellingPoints: event.target.value })}
                  placeholder="一行一个卖点"
                  rows={3}
                />
              </Field>
              <Field label="约束">
                <Textarea
                  value={form.constraints}
                  onChange={(event) => setForm({ ...form, constraints: event.target.value })}
                  placeholder="不要绝对化表达；语气克制"
                  rows={2}
                />
              </Field>
              <CollectionPicker
                options={options}
                selectedIds={form.collectionIds}
                onChange={(collectionIds) => setForm({ ...form, collectionIds })}
              />
              <Button className="w-full" disabled={running} onClick={handleRun}>
                {running ? <Loader2 className="mr-2 size-4 animate-spin" /> : <Play className="mr-2 size-4" />}
                {mode === "auto" ? "一键生成终稿" : "启动分步向导"}
              </Button>
            </div>
          </Card>

          <Card className="p-4">
            <div className="mb-3 flex items-center justify-between">
              <div className="text-sm font-semibold">最近工作流</div>
              <Button variant="ghost" size="icon" onClick={() => void loadHistory()}>
                <RefreshCw className="size-4" />
              </Button>
            </div>
            <RunHistory
              runs={history}
              loading={historyLoading}
              selectedId={selectedRun?.id ?? null}
              onSelect={openRun}
            />
          </Card>
        </div>

        <Card className="min-h-0 overflow-hidden p-0">
          {selectedRun ? (
            <RunDetail run={selectedRun} />
          ) : (
            <div className="flex h-full items-center justify-center p-6">
              <EmptyState
                icon={<Sparkles className="size-8" />}
                title="还没有组稿结果"
                hint="填写需求后启动智能组稿，完成后会在这里显示步骤、模型和终稿。"
              />
            </div>
          )}
        </Card>
      </div>
    </main>
  );
}

function ModeSwitch({
  mode,
  onChange
}: {
  mode: SmartCompositionMode;
  onChange: (mode: SmartCompositionMode) => void;
}) {
  return (
    <div className="grid h-8 grid-cols-2 rounded-md border border-border p-0.5 text-xs">
      {(["auto", "guided"] as SmartCompositionMode[]).map((item) => (
        <button
          key={item}
          type="button"
          onClick={() => onChange(item)}
          className={cn(
            "rounded px-2 transition-colors",
            mode === item ? "bg-primary text-primary-foreground" : "text-muted-foreground"
          )}
        >
          {item === "auto" ? "全自动" : "向导型"}
        </button>
      ))}
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-2">
      <Label>{label}</Label>
      {children}
    </div>
  );
}

function SelectField({
  label,
  value,
  options,
  loading,
  onChange
}: {
  label: string;
  value: string;
  options?: Array<{ value: string; label: string }>;
  loading: boolean;
  onChange: (value: string) => void;
}) {
  return (
    <Field label={label}>
      <Select value={value} onValueChange={onChange} disabled={loading}>
        <SelectTrigger>
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {(options ?? []).map((item) => (
            <SelectItem key={item.value} value={item.value}>
              {item.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </Field>
  );
}

function CollectionPicker({
  options,
  selectedIds,
  onChange
}: {
  options: SmartCompositionOptions | null;
  selectedIds: string[];
  onChange: (ids: string[]) => void;
}) {
  const collections = options?.collections ?? [];
  if (collections.length === 0) return null;
  return (
    <div className="space-y-2">
      <Label>知识库范围</Label>
      <div className="max-h-32 space-y-1 overflow-y-auto rounded-md border border-border p-2">
        {collections.map((collection) => {
          const checked = selectedIds.includes(collection.id);
          return (
            <label key={collection.id} className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={checked}
                onChange={(event) => {
                  onChange(
                    event.target.checked
                      ? [...selectedIds, collection.id]
                      : selectedIds.filter((id) => id !== collection.id)
                  );
                }}
              />
              <span className="truncate">{collection.name}</span>
            </label>
          );
        })}
      </div>
    </div>
  );
}

function RunHistory({
  runs,
  loading,
  selectedId,
  onSelect
}: {
  runs: SmartCompositionRunSummary[];
  loading: boolean;
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  if (loading) {
    return <div className="space-y-2">{Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-16 w-full" />)}</div>;
  }
  if (runs.length === 0) {
    return <div className="text-sm text-muted-foreground">暂无历史记录</div>;
  }
  return (
    <div className="space-y-2">
      {runs.map((run) => (
        <button
          key={run.id}
          type="button"
          onClick={() => onSelect(run.id)}
          className={cn(
            "w-full rounded-md border border-border p-3 text-left text-sm transition-colors hover:bg-accent/50",
            selectedId === run.id && "bg-accent"
          )}
        >
          <div className="flex items-center justify-between gap-2">
            <span className="truncate font-medium">{run.brief.product}</span>
            <StatusBadge status={run.status} />
          </div>
          <div className="mt-1 truncate text-xs text-muted-foreground">
            {run.brief.platform} / {run.brief.purpose} / {new Date(run.created_at).toLocaleString()}
          </div>
        </button>
      ))}
    </div>
  );
}

function RunDetail({ run }: { run: SmartCompositionRunDetail }) {
  const currentPercent = run.timeline.reduce(
    (value, step) => (step.status === "completed" ? Math.max(value, step.percent) : value),
    0
  );
  const finalText = run.result.draft?.current_text ?? "";
  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="border-b border-border p-5">
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base font-semibold">{run.brief.product}</h2>
              <StatusBadge status={run.status} />
            </div>
            <p className="mt-1 text-sm text-muted-foreground">
              {run.brief.audience} / {run.brief.platform} / {run.brief.purpose}
            </p>
          </div>
          {run.result.composition?.model ? (
            <Badge variant="outline">{run.result.composition.model}</Badge>
          ) : null}
        </div>
        <Progress value={currentPercent} className="mt-4 h-2" />
      </div>

      <div className="grid min-h-0 flex-1 grid-cols-1 xl:grid-cols-[360px_minmax(0,1fr)]">
        <div className="min-h-0 overflow-y-auto border-b border-border p-4 xl:border-b-0 xl:border-r">
          <div className="space-y-2">
            {run.timeline.map((step) => (
              <StepRow key={step.step_id} step={step} />
            ))}
          </div>
          <SelectionBlock title="组稿选择" selection={run.result.composition_selection} />
          <SelectionBlock title="改写选择" selection={run.result.rewrite_selection} />
        </div>
        <div className="min-h-0 overflow-y-auto p-5">
          {finalText ? (
            <div className="space-y-4">
              <div className="flex items-center gap-2 text-sm font-semibold">
                <FileText className="size-4" />
                终稿预览
              </div>
              <div className="whitespace-pre-wrap rounded-md border border-border bg-muted/20 p-4 text-sm leading-7">
                {finalText}
              </div>
            </div>
          ) : (
            <EmptyState
              icon={<Clock3 className="size-8" />}
              title="等待下一步"
              hint="向导型流程会在确认点暂停，后端确认接口补齐后可继续推进。"
            />
          )}
        </div>
      </div>
    </div>
  );
}

function StepRow({ step }: { step: SmartCompositionStep }) {
  const icon =
    step.status === "completed" ? (
      <CheckCircle2 className="size-4 text-emerald-600" />
    ) : step.status === "failed" ? (
      <XCircle className="size-4 text-destructive" />
    ) : step.status === "running" ? (
      <Loader2 className="size-4 animate-spin text-primary" />
    ) : (
      <Clock3 className="size-4 text-muted-foreground" />
    );
  return (
    <div className="rounded-md border border-border p-3 text-sm">
      <div className="flex items-center gap-2">
        {icon}
        <span className="font-medium">{STEP_LABELS[step.step_id] ?? step.label}</span>
        {step.model ? <Badge variant="outline">{step.model}</Badge> : null}
      </div>
      {step.message || step.reason ? (
        <p className="mt-1 text-xs text-muted-foreground">{step.message ?? step.reason}</p>
      ) : null}
    </div>
  );
}

function SelectionBlock({
  title,
  selection
}: {
  title: string;
  selection?: { method: string; reason?: string | null; fallback_reason?: string | null } | null;
}) {
  if (!selection) return null;
  return (
    <div className="mt-4 rounded-md border border-border p-3 text-sm">
      <div className="font-medium">{title}</div>
      <p className="mt-1 text-xs text-muted-foreground">
        {selection.method === "llm_judge" ? "LLM 选择" : "规则兜底"}
        {selection.reason ? `：${selection.reason}` : ""}
        {selection.fallback_reason ? `（${selection.fallback_reason}）` : ""}
      </p>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const labels: Record<string, string> = {
    pending: "等待",
    running: "运行中",
    waiting_for_user: "待确认",
    finished: "已完成",
    failed: "失败"
  };
  return (
    <Badge variant={status === "failed" ? "destructive" : "outline"}>
      {labels[status] ?? status}
    </Badge>
  );
}

function briefFromForm(form: BriefForm): SmartCompositionBrief {
  return {
    product: form.product.trim(),
    audience: form.audience,
    platform: form.platform,
    purpose: form.purpose,
    style: form.style,
    key_selling_points: form.sellingPoints
      .split(/\n|,|，/)
      .map((item) => item.trim())
      .filter(Boolean),
    constraints: form.constraints.trim() || null,
    target_length: form.targetLength.trim() || null,
    collection_ids: form.collectionIds,
    extra_notes: form.extraNotes.trim() || null
  };
}

function formFromBrief(brief: SmartCompositionBrief): BriefForm {
  return {
    product: brief.product,
    audience: brief.audience,
    platform: brief.platform,
    purpose: brief.purpose,
    style: brief.style,
    sellingPoints: brief.key_selling_points.join("\n"),
    constraints: brief.constraints ?? "",
    targetLength: brief.target_length ?? "",
    extraNotes: brief.extra_notes ?? "",
    collectionIds: brief.collection_ids ?? []
  };
}
