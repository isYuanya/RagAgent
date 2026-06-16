import * as React from "react";
import {
  CheckCircle2,
  Clock,
  ExternalLink,
  Loader2,
  Save,
  XCircle
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  emptyAnalysis,
  type Analysis,
  type CopyAsset,
  type RiskWarning,
  type ReviewStatus
} from "@/lib/types";
import { cn, formatFollowers, formatMetrics, splitLines } from "@/lib/utils";

const REVIEW_STATUS_OPTIONS: Array<{
  value: ReviewStatus;
  label: string;
  icon: React.ReactNode;
}> = [
  { value: "pending_review", label: "待审核", icon: <Clock className="size-4" /> },
  { value: "approved", label: "确认通过", icon: <CheckCircle2 className="size-4" /> },
  { value: "rejected", label: "拒绝入库", icon: <XCircle className="size-4" /> }
];

export function ReviewPanel({
  asset,
  saving,
  onSave
}: {
  asset: CopyAsset | null;
  saving: boolean;
  onSave: (status: ReviewStatus, draft: Analysis) => void;
}) {
  const [draft, setDraft] = React.useState<Analysis>(emptyAnalysis);
  const [status, setStatus] = React.useState<ReviewStatus>("pending_review");
  const [riskText, setRiskText] = React.useState("");

  React.useEffect(() => {
    if (!asset) return;
    const nextDraft =
      asset.reviewed_analysis ?? asset.auto_analysis ?? emptyAnalysis;
    setDraft(nextDraft);
    setRiskText(formatRiskWarnings(nextDraft.risk_warnings));
    setStatus((asset.status as ReviewStatus) ?? "pending_review");
  }, [asset?.id]);

  function update<K extends keyof Analysis>(key: K, value: Analysis[K]) {
    setDraft((current) => ({ ...current, [key]: value }));
  }

  function handleStatusClick(nextStatus: ReviewStatus) {
    setStatus(nextStatus);
    if (nextStatus === "approved" || nextStatus === "rejected") {
      onSave(nextStatus, draft);
    }
  }

  function handleRiskWarningsChange(value: string) {
    setRiskText(value);
    update("risk_warnings", parseRiskWarnings(value));
  }

  if (!asset) {
    return (
      <div className="flex h-full items-center justify-center rounded-xl border border-dashed border-border text-sm text-muted-foreground">
        选择一条导入记录后进行校正。
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between gap-3 border-b border-border px-5 py-4">
        <div>
          <h2 className="text-base font-semibold">校正拆解</h2>
          <p className="text-xs text-muted-foreground">
            校正 LLM 拆解结果，选择审核结论后保存。
          </p>
        </div>
        <Button onClick={() => onSave(status, draft)} disabled={saving}>
          {saving ? <Loader2 className="animate-spin" /> : <Save />}
          {saving ? "保存中" : "保存审核"}
        </Button>
      </div>

      <div className="min-h-0 flex-1 space-y-5 overflow-y-auto p-5">
        <section className="space-y-2 rounded-lg border border-border bg-muted/30 p-4">
          <div className="text-xs font-medium text-muted-foreground">原文</div>
          <p className="text-sm leading-relaxed">{asset.source_text}</p>
          <div className="flex flex-wrap gap-1.5 pt-1">
            <MetaPill>{asset.author_name ?? "未标作者"}</MetaPill>
            <MetaPill>{asset.platform ?? "未标平台"}</MetaPill>
            <MetaPill>{asset.industry ?? "未标行业"}</MetaPill>
            <MetaPill>{asset.audience ?? "未标人群"}</MetaPill>
            <MetaPill>{asset.purpose ?? "未标目的"}</MetaPill>
            <MetaPill>{asset.style ?? "未标风格"}</MetaPill>
            <MetaPill>{formatFollowers(asset.author_follower_count)}</MetaPill>
            <MetaPill>{formatMetrics(asset.metrics)}</MetaPill>
          </div>
          {asset.author_url ? (
            <a
              href={asset.author_url}
              target="_blank"
              rel="noreferrer"
              className="inline-flex w-fit items-center gap-1 text-xs font-medium text-primary hover:underline"
            >
              <ExternalLink className="size-3.5" />
              作者主页
            </a>
          ) : null}
          {asset.source_url ? (
            <a
              href={asset.source_url}
              target="_blank"
              rel="noreferrer"
              className="inline-flex w-fit items-center gap-1 text-xs font-medium text-primary hover:underline"
            >
              <ExternalLink className="size-3.5" />
              文案来源
            </a>
          ) : null}
        </section>

        <Field label="审核结论">
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
            {REVIEW_STATUS_OPTIONS.map((option) => (
              <button
                key={option.value}
                type="button"
                onClick={() => handleStatusClick(option.value)}
                disabled={saving}
                className={cn(
                  "flex h-10 items-center justify-center gap-2 rounded-md border px-3 text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-ring disabled:cursor-not-allowed disabled:opacity-60",
                  status === option.value
                    ? "border-primary bg-accent text-accent-foreground ring-1 ring-primary/20"
                    : "border-border bg-background text-muted-foreground hover:bg-accent/50 hover:text-foreground"
                )}
                aria-pressed={status === option.value}
              >
                {option.icon}
                {option.label}
              </button>
            ))}
          </div>
        </Field>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <TextField
            label="主题"
            value={draft.topic}
            onChange={(v) => update("topic", v)}
          />
          <TextField
            label="目标用户"
            value={draft.target_user}
            onChange={(v) => update("target_user", v)}
          />
          <TextField
            label="核心痛点"
            value={draft.core_pain}
            onChange={(v) => update("core_pain", v)}
          />
          <TextField
            label="开头钩子"
            value={draft.hook}
            onChange={(v) => update("hook", v)}
          />
          <ListField
            label="情绪按钮"
            value={draft.emotion_buttons}
            onChange={(v) => update("emotion_buttons", v)}
          />
          <ListField
            label="内容结构"
            value={draft.structure}
            onChange={(v) => update("structure", v)}
          />
          <ListField
            label="表达技巧"
            value={draft.expression_skills}
            onChange={(v) => update("expression_skills", v)}
          />
          <ListField
            label="适用场景"
            value={draft.suitable_scenarios}
            onChange={(v) => update("suitable_scenarios", v)}
          />
        </div>

        <Field label="可复用模板">
          <Textarea
            value={draft.reusable_template}
            onChange={(e) => update("reusable_template", e.target.value)}
            className="min-h-[100px]"
          />
        </Field>

        <Field label="风险提示（每行一条：级别｜提示｜建议）">
          <Textarea
            aria-label="风险提示"
            value={riskText}
            onChange={(e) => handleRiskWarningsChange(e.target.value)}
            className="min-h-[100px]"
            placeholder="medium｜可能涉及夸大承诺｜改成经验分享口吻"
          />
        </Field>

        <Field label={`置信度（${draft.confidence.toFixed(2)}）`}>
          <Input
            type="number"
            min="0"
            max="1"
            step="0.01"
            value={draft.confidence}
            onChange={(e) => update("confidence", Number(e.target.value))}
          />
        </Field>
      </div>
    </div>
  );
}

function formatRiskWarnings(warnings: RiskWarning[]): string {
  return warnings
    .map((warning) => {
      const parts = [warning.level, warning.message];
      if (warning.suggestion) parts.push(warning.suggestion);
      return parts.join("｜");
    })
    .join("\n");
}

function parseRiskWarnings(value: string): RiskWarning[] {
  return splitLines(value).map((line) => {
    const parts = line
      .split(/[|｜]/)
      .map((item) => item.trim());
    if (parts.length === 1) {
      return {
        level: "medium",
        message: parts[0],
        suggestion: null
      };
    }
    const [level = "medium", message = "", suggestion = ""] = parts;
    return {
      level: level || "medium",
      message: message || line.trim(),
      suggestion: suggestion || null
    };
  });
}

function MetaPill({ children }: { children: React.ReactNode }) {
  return (
    <Badge variant="secondary" className="font-normal">
      {children}
    </Badge>
  );
}

function Field({
  label,
  children
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1.5">
      <Label>{label}</Label>
      {children}
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
  return (
    <Field label={label}>
      <Input value={value} onChange={(e) => onChange(e.target.value)} />
    </Field>
  );
}

function ListField({
  label,
  value,
  onChange
}: {
  label: string;
  value: string[];
  onChange: (value: string[]) => void;
}) {
  return (
    <Field label={`${label}（每行一条）`}>
      <Textarea
        className="min-h-[84px]"
        value={value.join("\n")}
        onChange={(e) => onChange(splitLines(e.target.value))}
      />
    </Field>
  );
}
