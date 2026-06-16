import { ExternalLink } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { formatFollowers, formatMetrics } from "@/lib/utils";
import type { Analysis, CopyAsset } from "@/lib/types";

/** 只读展示一条拆解结果，可选附带原文资产上下文。 */
export function AnalysisView({
  analysis,
  asset
}: {
  analysis: Analysis | null;
  asset?: CopyAsset | null;
}) {
  return (
    <div className="space-y-5">
      {asset ? (
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
            <MetaPill>{asset.content_type ?? "未标内容类型"}</MetaPill>
            <MetaPill>{asset.structure_type ?? "未标结构类型"}</MetaPill>
            <MetaPill>{formatFollowers(asset.author_follower_count)}</MetaPill>
            <MetaPill>{formatMetrics(asset.metrics)}</MetaPill>
            {asset.storage_backend ? (
              <MetaPill>存储：{asset.storage_backend}</MetaPill>
            ) : null}
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
          {asset.source_url ? (
            <a
              href={asset.source_url}
              target="_blank"
              rel="noreferrer"
              className="inline-flex w-fit items-center gap-1 text-xs font-medium text-primary hover:underline"
            >
              <ExternalLink className="size-3.5" /> 文案来源
            </a>
          ) : null}
        </section>
      ) : null}

      {analysis ? (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <TextItem label="主题" value={analysis.topic} />
            <TextItem label="目标用户" value={analysis.target_user} />
            <TextItem label="核心痛点" value={analysis.core_pain} />
            <TextItem label="开头钩子" value={analysis.hook} />
            <ListItem label="情绪按钮" value={analysis.emotion_buttons} />
            <ListItem label="内容结构" value={analysis.structure} />
            <ListItem label="表达技巧" value={analysis.expression_skills} />
            <ListItem label="适用场景" value={analysis.suitable_scenarios} />
          </div>

          <Block label="可复用模板">
            <p className="whitespace-pre-wrap text-sm">
              {analysis.reusable_template || "—"}
            </p>
          </Block>

          <Block label="风险提示">
            {analysis.risk_warnings.length > 0 ? (
              <div className="space-y-2">
                {analysis.risk_warnings.map((warning, index) => (
                  <div
                    key={`${warning.level}-${warning.message}-${index}`}
                    className="rounded-md border border-border bg-muted/30 p-3 text-sm"
                  >
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge variant="outline">{warning.level}</Badge>
                      <span>{warning.message || "—"}</span>
                    </div>
                    {warning.suggestion ? (
                      <p className="mt-1 text-xs text-muted-foreground">
                        建议：{warning.suggestion}
                      </p>
                    ) : null}
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">—</p>
            )}
          </Block>

          <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
            <span>置信度</span>
            <Badge variant="secondary">{analysis.confidence.toFixed(2)}</Badge>
          </div>
        </>
      ) : (
        <p className="text-sm text-muted-foreground">该条目暂无拆解结果。</p>
      )}
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

function Block({
  label,
  children
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1.5">
      <div className="text-sm font-medium text-foreground/80">{label}</div>
      {children}
    </div>
  );
}

function TextItem({ label, value }: { label: string; value: string }) {
  return (
    <Block label={label}>
      <p className="text-sm">{value || "—"}</p>
    </Block>
  );
}

function ListItem({ label, value }: { label: string; value: string[] }) {
  return (
    <Block label={label}>
      {value.length > 0 ? (
        <ul className="list-disc space-y-0.5 pl-4 text-sm">
          {value.map((item, i) => (
            <li key={i}>{item}</li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-muted-foreground">—</p>
      )}
    </Block>
  );
}
