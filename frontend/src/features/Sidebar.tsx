import { Database, FileText, ShieldCheck, Sparkles } from "lucide-react";

export function Sidebar({ assetCount }: { assetCount: number }) {
  return (
    <aside className="hidden w-64 shrink-0 flex-col border-r border-border bg-card/60 px-5 py-6 lg:flex">
      <div className="flex items-center gap-2.5">
        <div className="flex size-9 items-center justify-center rounded-lg bg-primary text-primary-foreground">
          <Database className="size-5" />
        </div>
        <div className="leading-tight">
          <div className="text-sm font-semibold">RagAgent</div>
          <div className="text-xs text-muted-foreground">文案资产工作台</div>
        </div>
      </div>

      <div className="mt-8 space-y-1.5">
        <SidebarItem icon={<FileText className="size-4" />} label="文案资产" active />
        <SidebarItem icon={<Sparkles className="size-4" />} label="拆解校正" />
        <SidebarItem icon={<ShieldCheck className="size-4" />} label="审核状态" />
      </div>

      <div className="mt-auto rounded-lg border border-border bg-background p-3">
        <div className="text-xs text-muted-foreground">已加载资产</div>
        <div className="mt-0.5 text-2xl font-semibold tabular-nums">
          {assetCount}
        </div>
      </div>
    </aside>
  );
}

function SidebarItem({
  icon,
  label,
  active = false
}: {
  icon: React.ReactNode;
  label: string;
  active?: boolean;
}) {
  return (
    <div
      className={
        active
          ? "flex items-center gap-2.5 rounded-md bg-accent px-3 py-2 text-sm font-medium text-accent-foreground"
          : "flex items-center gap-2.5 rounded-md px-3 py-2 text-sm text-muted-foreground"
      }
    >
      {icon}
      {label}
    </div>
  );
}
