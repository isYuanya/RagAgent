import * as React from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Clock,
  Loader2,
  RefreshCcw,
  ServerCog
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import type { DependencyStatus, SystemStatusResponse } from "@/lib/types";
import {
  SERVICE_LABELS,
  STATUS_LABELS,
  statusBadgeVariant,
  statusTone
} from "./statusUtils";

export function SystemStatusView({
  status,
  loading,
  lastCheckedAt,
  autoRefresh,
  onAutoRefreshChange,
  onRefresh
}: {
  status: SystemStatusResponse | null;
  loading: boolean;
  lastCheckedAt: Date | null;
  autoRefresh: boolean;
  onAutoRefreshChange: (value: boolean) => void;
  onRefresh: () => void;
}) {
  const overall = status?.status ?? "down";
  const unhealthyRequired =
    status?.services.filter(
      (service) => service.required && service.status === "down"
    ) ?? [];
  const limitedOptional =
    status?.services.filter(
      (service) => !service.required && service.status !== "ok"
    ) ?? [];

  return (
    <main className="flex min-w-0 flex-1 flex-col">
      <header className="flex items-center justify-between gap-4 border-b border-border px-6 py-4">
        <div>
          <h1 className="text-lg font-semibold">服务状态</h1>
          <p className="text-sm text-muted-foreground">
            检查 PostgreSQL、Redis、导入 Worker 和 Milvus 的可用性。
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <Button
            type="button"
            variant={autoRefresh ? "secondary" : "outline"}
            size="sm"
            onClick={() => onAutoRefreshChange(!autoRefresh)}
          >
            <Clock />
            {autoRefresh ? "自动刷新中" : "自动刷新"}
          </Button>
          <Button type="button" size="sm" onClick={onRefresh} disabled={loading}>
            {loading ? <Loader2 className="animate-spin" /> : <RefreshCcw />}
            刷新
          </Button>
        </div>
      </header>

      <div className="min-h-0 flex-1 overflow-y-auto p-6">
        <div className="mb-4 grid grid-cols-1 gap-4 lg:grid-cols-[minmax(260px,360px)_1fr]">
          <Card className="p-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="text-sm text-muted-foreground">整体状态</div>
                <div className="mt-2 flex items-center gap-2">
                  <StatusIcon status={overall} />
                  <span className="text-2xl font-semibold">
                    {status ? STATUS_LABELS[overall] : "状态未知"}
                  </span>
                </div>
              </div>
              {status ? (
                <Badge variant={statusBadgeVariant(overall)}>
                  {overall.toUpperCase()}
                </Badge>
              ) : (
                <Badge variant="muted">UNKNOWN</Badge>
              )}
            </div>
            <div className="mt-4 text-xs text-muted-foreground">
              最后检查：
              {lastCheckedAt ? lastCheckedAt.toLocaleTimeString("zh-CN") : "尚未检查"}
            </div>
          </Card>

          <Card className="p-4">
            <div className="text-sm font-medium">影响提示</div>
            <div className="mt-3 space-y-2 text-sm">
              {!status ? (
                <ImpactLine tone="down" text="暂时无法读取服务状态，请检查后端 API。" />
              ) : unhealthyRequired.length > 0 ? (
                unhealthyRequired.map((service) => (
                  <ImpactLine
                    key={service.name}
                    tone="down"
                    text={`${serviceLabel(service.name)} 异常：${serviceImpact(service)}`}
                  />
                ))
              ) : limitedOptional.length > 0 ? (
                limitedOptional.map((service) => (
                  <ImpactLine
                    key={service.name}
                    tone="degraded"
                    text={`${serviceLabel(service.name)} 异常：部分检索能力可能受限。`}
                  />
                ))
              ) : (
                <ImpactLine tone="ok" text="核心工作流和可选能力都处于可用状态。" />
              )}
            </div>
          </Card>
        </div>

        <div className="grid grid-cols-1 gap-3">
          {(status?.services ?? []).map((service) => (
            <ServiceRow key={service.name} service={service} />
          ))}
          {!loading && !status ? (
            <Card className="flex items-center gap-3 p-4 text-sm text-muted-foreground">
              <ServerCog className="size-5" />
              暂无服务状态数据。
            </Card>
          ) : null}
        </div>
      </div>
    </main>
  );
}

function ServiceRow({ service }: { service: DependencyStatus }) {
  return (
    <Card className="p-4">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <StatusIcon status={service.status} />
            <span className="font-medium">{serviceLabel(service.name)}</span>
            <Badge variant={service.required ? "secondary" : "muted"}>
              {service.required ? "必需" : "可选"}
            </Badge>
            <Badge variant={statusBadgeVariant(service.status)}>
              {STATUS_LABELS[service.status]}
            </Badge>
          </div>
          <p className="mt-2 text-sm text-muted-foreground">{service.message}</p>
          {service.endpoint ? (
            <p className="mt-2 break-all rounded-md bg-muted px-2 py-1 font-mono text-xs text-muted-foreground">
              {service.endpoint}
            </p>
          ) : null}
        </div>
        <div className="shrink-0 text-sm text-muted-foreground">
          延迟：
          <span className="font-medium text-foreground">
            {service.latency_ms ?? "-"} ms
          </span>
        </div>
      </div>
    </Card>
  );
}

function StatusIcon({ status }: { status: SystemStatusResponse["status"] }) {
  if (status === "ok") {
    return <CheckCircle2 className={`size-5 ${statusTone(status)}`} />;
  }
  return <AlertTriangle className={`size-5 ${statusTone(status)}`} />;
}

function ImpactLine({
  tone,
  text
}: {
  tone: SystemStatusResponse["status"];
  text: string;
}) {
  return (
    <div className="flex items-start gap-2 rounded-md border border-border bg-muted/30 p-2">
      <StatusIcon status={tone} />
      <span>{text}</span>
    </div>
  );
}

function serviceLabel(name: string) {
  return SERVICE_LABELS[name] ?? name;
}

function serviceImpact(service: DependencyStatus) {
  if (service.name === "redis") return "任务队列不可用，导入功能需要暂停。";
  if (service.name === "copy_import_worker")
    return "导入任务可能会一直停留在队列中，请启动 worker。";
  if (service.name === "postgres") return "数据可能无法真正落库。";
  return service.message;
}
