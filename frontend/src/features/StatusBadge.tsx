import { CheckCircle2, Clock, XCircle } from "lucide-react";
import { Badge } from "@/components/ui/badge";

export function StatusBadge({ status }: { status: string }) {
  if (status === "approved") {
    return (
      <Badge variant="success">
        <CheckCircle2 className="size-3.5" /> 已确认
      </Badge>
    );
  }
  if (status === "rejected") {
    return (
      <Badge variant="destructive">
        <XCircle className="size-3.5" /> 已拒绝
      </Badge>
    );
  }
  return (
    <Badge variant="muted">
      <Clock className="size-3.5" /> 待审核
    </Badge>
  );
}

export const STATUS_LABELS: Record<string, string> = {
  pending_review: "待审核",
  approved: "已确认",
  rejected: "已拒绝"
};
