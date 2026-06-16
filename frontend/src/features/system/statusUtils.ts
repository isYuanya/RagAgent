import type {
  DependencyStatus,
  ServiceHealthStatus,
  SystemStatusResponse
} from "@/lib/types";

export const STATUS_LABELS: Record<ServiceHealthStatus, string> = {
  ok: "服务正常",
  degraded: "部分受限",
  down: "核心异常"
};

export const SERVICE_LABELS: Record<string, string> = {
  postgres: "PostgreSQL",
  redis: "Redis",
  copy_import_worker: "导入 Worker",
  milvus: "Milvus"
};

export function statusTone(status: ServiceHealthStatus) {
  if (status === "ok") return "text-primary";
  if (status === "degraded") return "text-amber-700";
  return "text-destructive";
}

export function statusBadgeVariant(status: ServiceHealthStatus) {
  if (status === "ok") return "success";
  if (status === "degraded") return "outline";
  return "destructive";
}

export function getService(
  status: SystemStatusResponse | null,
  name: string
): DependencyStatus | null {
  return status?.services.find((service) => service.name === name) ?? null;
}

export function isServiceDown(
  status: SystemStatusResponse | null,
  name: string
) {
  return getService(status, name)?.status === "down";
}
