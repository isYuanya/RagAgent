import * as React from "react";
import { Inbox, Search } from "lucide-react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import type { CopyAsset } from "@/lib/types";
import { StatusBadge, STATUS_LABELS } from "./StatusBadge";

const ALL = "__all__";

type Filters = {
  platform: string;
  industry: string;
  status: string;
};

function uniqueValues(assets: CopyAsset[], key: "platform" | "industry") {
  const set = new Set<string>();
  for (const asset of assets) {
    const value = asset[key];
    if (value) set.add(value);
  }
  return Array.from(set).sort();
}

export function AssetList({
  assets,
  loading,
  selectedId,
  onSelect
}: {
  assets: CopyAsset[];
  loading: boolean;
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  const [filters, setFilters] = React.useState<Filters>({
    platform: ALL,
    industry: ALL,
    status: ALL
  });

  const platforms = React.useMemo(
    () => uniqueValues(assets, "platform"),
    [assets]
  );
  const industries = React.useMemo(
    () => uniqueValues(assets, "industry"),
    [assets]
  );

  const filtered = React.useMemo(
    () =>
      assets.filter((asset) => {
        if (filters.platform !== ALL && asset.platform !== filters.platform)
          return false;
        if (filters.industry !== ALL && asset.industry !== filters.industry)
          return false;
        if (filters.status !== ALL && asset.status !== filters.status)
          return false;
        return true;
      }),
    [assets, filters]
  );

  return (
    <div className="flex h-full flex-col gap-3">
      <div className="grid grid-cols-3 gap-2">
        <FilterSelect
          placeholder="平台"
          value={filters.platform}
          options={platforms}
          onChange={(value) => setFilters((f) => ({ ...f, platform: value }))}
        />
        <FilterSelect
          placeholder="行业"
          value={filters.industry}
          options={industries}
          onChange={(value) => setFilters((f) => ({ ...f, industry: value }))}
        />
        <FilterSelect
          placeholder="状态"
          value={filters.status}
          options={Object.keys(STATUS_LABELS)}
          labelMap={STATUS_LABELS}
          onChange={(value) => setFilters((f) => ({ ...f, status: value }))}
        />
      </div>

      <div className="min-h-0 flex-1 space-y-2 overflow-y-auto pr-1">
        {loading ? (
          <ListSkeleton />
        ) : assets.length === 0 ? (
          <EmptyState
            icon={<Inbox className="size-8" />}
            title="还没有文案资产"
            hint="上传包含 source_text 表头的 CSV 开始导入。"
          />
        ) : filtered.length === 0 ? (
          <EmptyState
            icon={<Search className="size-8" />}
            title="没有匹配的资产"
            hint="调整筛选条件试试。"
          />
        ) : (
          filtered.map((asset) => (
            <AssetRow
              key={asset.id}
              asset={asset}
              active={asset.id === selectedId}
              onClick={() => onSelect(asset.id)}
            />
          ))
        )}
      </div>
    </div>
  );
}

function FilterSelect({
  placeholder,
  value,
  options,
  labelMap,
  onChange
}: {
  placeholder: string;
  value: string;
  options: string[];
  labelMap?: Record<string, string>;
  onChange: (value: string) => void;
}) {
  return (
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger className="h-8 text-xs">
        <SelectValue placeholder={placeholder} />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value={ALL}>全部{placeholder}</SelectItem>
        {options.map((option) => (
          <SelectItem key={option} value={option}>
            {labelMap?.[option] ?? option}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}

function AssetRow({
  asset,
  active,
  onClick
}: {
  asset: CopyAsset;
  active: boolean;
  onClick: () => void;
}) {
  const title = asset.auto_analysis?.topic || asset.source_text.slice(0, 28);
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "w-full rounded-lg border bg-card p-3 text-left transition-colors hover:border-primary/40 hover:bg-accent/40",
        active && "border-primary bg-accent/60 ring-1 ring-primary/20"
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <span className="line-clamp-1 text-sm font-medium">{title}</span>
        <StatusBadge status={asset.status} />
      </div>
      <div className="mt-1 line-clamp-1 text-xs text-muted-foreground">
        {asset.author_name ?? "未标作者"} · {asset.platform ?? "未标平台"} ·{" "}
        {asset.industry ?? "未标行业"}
      </div>
    </button>
  );
}

function ListSkeleton() {
  return (
    <div className="space-y-2">
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} className="rounded-lg border bg-card p-3">
          <div className="flex items-center justify-between gap-2">
            <Skeleton className="h-4 w-1/2" />
            <Skeleton className="h-5 w-14 rounded-full" />
          </div>
          <Skeleton className="mt-2 h-3 w-3/4" />
        </div>
      ))}
    </div>
  );
}

function EmptyState({
  icon,
  title,
  hint
}: {
  icon: React.ReactNode;
  title: string;
  hint: string;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-border py-12 text-center">
      <div className="text-muted-foreground">{icon}</div>
      <div className="text-sm font-medium">{title}</div>
      <div className="max-w-[220px] text-xs text-muted-foreground">{hint}</div>
    </div>
  );
}
