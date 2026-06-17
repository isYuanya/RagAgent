import { Database, FileText, Library, NotebookPen, ServerCog } from "lucide-react";
import { cn } from "@/lib/utils";

export type AppView = "workbench" | "drafts" | "knowledge" | "system";

export function Sidebar({
  view,
  onChangeView,
  assetCount
}: {
  view: AppView;
  onChangeView: (view: AppView) => void;
  assetCount: number;
}) {
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
        <SidebarItem
          icon={<FileText className="size-4" />}
          label="审核工作台"
          active={view === "workbench"}
          onClick={() => onChangeView("workbench")}
        />
        <SidebarItem
          icon={<NotebookPen className="size-4" />}
          label="草稿工作台"
          active={view === "drafts"}
          onClick={() => onChangeView("drafts")}
        />
        <SidebarItem
          icon={<Library className="size-4" />}
          label="知识库"
          active={view === "knowledge"}
          onClick={() => onChangeView("knowledge")}
        />
        <SidebarItem
          icon={<ServerCog className="size-4" />}
          label="服务状态"
          active={view === "system"}
          onClick={() => onChangeView("system")}
        />
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
  active = false,
  onClick
}: {
  icon: React.ReactNode;
  label: string;
  active?: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "flex w-full items-center gap-2.5 rounded-md px-3 py-2 text-sm transition-colors",
        active
          ? "bg-accent font-medium text-accent-foreground"
          : "text-muted-foreground hover:bg-accent/50"
      )}
    >
      {icon}
      {label}
    </button>
  );
}
