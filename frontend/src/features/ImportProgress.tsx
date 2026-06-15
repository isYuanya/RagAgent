import { AlertTriangle } from "lucide-react";
import { Progress } from "@/components/ui/progress";
import { phaseLabel } from "@/lib/utils";
import type { TaskProgress, TaskResponse } from "@/lib/types";

export function ImportProgress({ task }: { task: TaskResponse }) {
  const progress = task.progress;
  if (!progress) return null;

  return (
    <div
      className="space-y-3 rounded-lg border border-border bg-muted/40 p-4"
      role="status"
      aria-live="polite"
    >
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium">{phaseLabel(progress.phase)}</span>
        <span className="tabular-nums text-primary">{progress.percent}%</span>
      </div>

      <Progress value={progress.percent} aria-label="导入进度" />

      <div className="flex flex-wrap gap-1.5 text-xs text-muted-foreground">
        <Stat label="模型" value={progress.model ?? "未配置"} />
        <Stat
          label="行"
          value={`${progress.processed_count}/${progress.total_rows}`}
        />
        <Stat label="成功" value={progress.success_count} />
        <Stat label="失败" value={progress.failed_count} />
      </div>

      {progress.current_message ? (
        <p className="text-xs text-muted-foreground">
          {progress.current_message}
        </p>
      ) : null}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <span className="rounded-full bg-background px-2 py-1">
      {label}：{value}
    </span>
  );
}

export function ImportErrors({ errors }: { errors: TaskProgress["errors"] }) {
  if (errors.length === 0) return null;
  return (
    <div className="space-y-1.5 rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">
      <div className="flex items-center gap-1.5 font-medium">
        <AlertTriangle className="size-4" /> 行级错误（{errors.length}）
      </div>
      <div className="space-y-1">
        {errors.map((error) => (
          <div key={`${error.row_number}-${error.message}`} className="text-xs">
            第 {error.row_number ?? "-"} 行：{error.message ?? "处理失败"}
          </div>
        ))}
      </div>
    </div>
  );
}
