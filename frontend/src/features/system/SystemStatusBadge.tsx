import { Activity, AlertTriangle, CheckCircle2, Loader2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { SystemStatusResponse } from "@/lib/types";
import { STATUS_LABELS, statusBadgeVariant } from "./statusUtils";

export function SystemStatusBadge({
  status,
  loading,
  onClick
}: {
  status: SystemStatusResponse | null;
  loading: boolean;
  onClick: () => void;
}) {
  const current = status?.status;
  const label = current ? STATUS_LABELS[current] : "状态未知";
  const Icon = current === "ok" ? CheckCircle2 : current ? AlertTriangle : Activity;

  return (
    <Button
      type="button"
      variant="outline"
      size="sm"
      className="shrink-0"
      onClick={onClick}
      title="查看服务状态"
    >
      {loading ? <Loader2 className="animate-spin" /> : <Icon />}
      <span>服务状态</span>
      {current ? (
        <Badge variant={statusBadgeVariant(current)}>{label}</Badge>
      ) : (
        <Badge variant="muted">{label}</Badge>
      )}
    </Button>
  );
}
