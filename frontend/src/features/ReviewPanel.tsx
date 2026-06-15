import * as React from "react";
import { ExternalLink, Loader2, Save } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from "@/components/ui/select";
import {
  emptyAnalysis,
  type Analysis,
  type CopyAsset
} from "@/lib/types";
import { formatFollowers, formatMetrics, splitLines } from "@/lib/utils";

export function ReviewPanel({
  asset,
  saving,
  onSave
}: {
  asset: CopyAsset | null;
  saving: boolean;
  onSave: (status: string, draft: Analysis) => void;
}) {
  const [draft, setDraft] = React.useState<Analysis>(emptyAnalysis);
  const [status, setStatus] = React.useState("pending_review");

  React.useEffect(() => {
    if (!asset) return;
    setDraft(asset.reviewed_analysis ?? asset.auto_analysis ?? emptyAnalysis);
    setStatus(asset.status);
  }, [asset?.id]);

  function update<K extends keyof Analysis>(key: K, value: Analysis[K]) {
    setDraft((current) => ({ ...current, [key]: value }));
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
            校正 LLM 拆解结果，保存为审核资产。
          </p>
        </div>
        <Button onClick={() => onSave(status, draft)} disabled={saving}>
          {saving ? (
            <Loader2 className="animate-spin" />
          ) : (
            <Save />
          )}
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
            <MetaPill>{asset.audience ?? "未标人群"}</MetaPill>
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
              <ExternalLink className="size-3.5" /> 作者主页
            </a>
          ) : null}
        </section>

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

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
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
          <Field label="审核状态">
            <Select value={status} onValueChange={setStatus}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="pending_review">待审核</SelectItem>
                <SelectItem value="approved">已确认</SelectItem>
                <SelectItem value="rejected">已拒绝</SelectItem>
              </SelectContent>
            </Select>
          </Field>
        </div>
      </div>
    </div>
  );
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
