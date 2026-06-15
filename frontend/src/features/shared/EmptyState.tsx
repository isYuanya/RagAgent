import * as React from "react";

export function EmptyState({
  icon,
  title,
  hint
}: {
  icon: React.ReactNode;
  title: string;
  hint?: string;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-border py-12 text-center">
      <div className="text-muted-foreground">{icon}</div>
      <div className="text-sm font-medium">{title}</div>
      {hint ? (
        <div className="max-w-[260px] text-xs text-muted-foreground">{hint}</div>
      ) : null}
    </div>
  );
}
