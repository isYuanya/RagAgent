import * as React from "react";
import { ArrowLeft, ExternalLink, FileUp, FolderPlus, Layers3, Plus, Search, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/features/shared/EmptyState";
import { ConfirmDialog } from "@/features/shared/ConfirmDialog";
import {
  createKeywordGroup,
  createKeywordIndustry,
  deleteKeywordGroup,
  deleteKeywordIndustry,
  fetchKeywordGroupsPage,
  fetchKeywordIndustriesPage,
  fetchKeywordVideosPage,
  importKeywordVideos
} from "@/lib/api";
import type { KeywordGroup, KeywordIndustry, KeywordVideo } from "@/lib/types";
import { cn } from "@/lib/utils";

const PAGE_SIZE = 20;

export function KeywordRankingsView({
  headerAction
}: {
  headerAction?: React.ReactNode;
}) {
  const [industries, setIndustries] = React.useState<KeywordIndustry[]>([]);
  const [industryPage, setIndustryPage] = React.useState(1);
  const [industryTotal, setIndustryTotal] = React.useState(0);
  const [industriesLoading, setIndustriesLoading] = React.useState(true);
  const [selectedIndustry, setSelectedIndustry] = React.useState<KeywordIndustry | null>(null);
  const [keywords, setKeywords] = React.useState<KeywordGroup[]>([]);
  const [keywordsLoading, setKeywordsLoading] = React.useState(false);
  const [selectedKeyword, setSelectedKeyword] = React.useState<KeywordGroup | null>(null);
  const [videos, setVideos] = React.useState<KeywordVideo[]>([]);
  const [videosLoading, setVideosLoading] = React.useState(false);
  const [industryDialogOpen, setIndustryDialogOpen] = React.useState(false);
  const [keywordDialogOpen, setKeywordDialogOpen] = React.useState(false);
  const [importDialogOpen, setImportDialogOpen] = React.useState(false);
  const [deletingIndustry, setDeletingIndustry] = React.useState<KeywordIndustry | null>(null);
  const [deletingKeyword, setDeletingKeyword] = React.useState<KeywordGroup | null>(null);
  const [deleteBusy, setDeleteBusy] = React.useState(false);

  const loadIndustries = React.useCallback(async (page = 1, append = false) => {
    setIndustriesLoading(true);
    try {
      const payload = await fetchKeywordIndustriesPage(page, PAGE_SIZE);
      setIndustries((current) => (append ? [...current, ...payload.items] : payload.items));
      setIndustryPage(payload.page);
      setIndustryTotal(payload.total);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "加载关键词行业失败");
    } finally {
      setIndustriesLoading(false);
    }
  }, []);

  const loadKeywords = React.useCallback(async (industryId: string) => {
    setKeywordsLoading(true);
    try {
      const payload = await fetchKeywordGroupsPage(industryId, 1, 100);
      setKeywords(payload.items);
      setSelectedKeyword((current) =>
        current && payload.items.some((item) => item.id === current.id) ? current : null
      );
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "加载关键词集合失败");
    } finally {
      setKeywordsLoading(false);
    }
  }, []);

  const loadVideos = React.useCallback(async (keywordId: string) => {
    setVideosLoading(true);
    try {
      const payload = await fetchKeywordVideosPage(keywordId, 1, 50);
      setVideos(payload.items);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "加载视频榜单失败");
    } finally {
      setVideosLoading(false);
    }
  }, []);

  React.useEffect(() => {
    void loadIndustries();
  }, [loadIndustries]);

  React.useEffect(() => {
    if (!selectedIndustry) return;
    void loadKeywords(selectedIndustry.id);
  }, [loadKeywords, selectedIndustry]);

  React.useEffect(() => {
    if (!selectedKeyword) {
      setVideos([]);
      return;
    }
    void loadVideos(selectedKeyword.id);
  }, [loadVideos, selectedKeyword]);

  async function refreshCurrent() {
    await loadIndustries(1);
    if (selectedIndustry) await loadKeywords(selectedIndustry.id);
    if (selectedKeyword) await loadVideos(selectedKeyword.id);
  }

  async function handleDeleteIndustry() {
    if (!deletingIndustry) return;
    setDeleteBusy(true);
    try {
      await deleteKeywordIndustry(deletingIndustry.id);
      toast.success("行业已删除");
      if (selectedIndustry?.id === deletingIndustry.id) {
        setSelectedIndustry(null);
        setSelectedKeyword(null);
        setKeywords([]);
        setVideos([]);
      }
      setDeletingIndustry(null);
      await loadIndustries(1);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "删除行业失败");
    } finally {
      setDeleteBusy(false);
    }
  }

  async function handleDeleteKeyword() {
    if (!deletingKeyword || !selectedIndustry) return;
    setDeleteBusy(true);
    try {
      await deleteKeywordGroup(deletingKeyword.id);
      toast.success("关键词集合已删除");
      if (selectedKeyword?.id === deletingKeyword.id) {
        setSelectedKeyword(null);
        setVideos([]);
      }
      setDeletingKeyword(null);
      await loadIndustries(1);
      await loadKeywords(selectedIndustry.id);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "删除关键词失败");
    } finally {
      setDeleteBusy(false);
    }
  }

  return (
    <main className="flex min-w-0 flex-1 flex-col">
      <header className="flex items-center justify-between gap-4 border-b border-border px-6 py-4">
        <div>
          <h1 className="text-lg font-semibold">关键词榜单</h1>
          <p className="text-sm text-muted-foreground">
            按行业管理爬虫关键词，导入热点视频 CSV，查看视频热度排行。
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {headerAction}
          {selectedIndustry ? (
            <Button variant="outline" onClick={() => setImportDialogOpen(true)}>
              <FileUp className="size-4" />
              导入 CSV
            </Button>
          ) : null}
          <Button onClick={() => setIndustryDialogOpen(true)}>
            <FolderPlus className="size-4" />
            创建行业
          </Button>
        </div>
      </header>

      <div className="min-h-0 flex-1 overflow-y-auto p-6">
        {!selectedIndustry ? (
          <IndustryGrid
            industries={industries}
            loading={industriesLoading}
            total={industryTotal}
            page={industryPage}
            onLoadMore={() => void loadIndustries(industryPage + 1, true)}
            onSelect={setSelectedIndustry}
            onDelete={setDeletingIndustry}
          />
        ) : (
          <div className="grid min-h-0 gap-4 lg:grid-cols-[minmax(300px,380px)_1fr]">
            <Card className="flex min-h-[620px] flex-col overflow-hidden p-4">
              <div className="mb-4 flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <Button
                    variant="ghost"
                    size="sm"
                    className="-ml-2 mb-2"
                    onClick={() => {
                      setSelectedIndustry(null);
                      setSelectedKeyword(null);
                    }}
                  >
                    <ArrowLeft className="size-4" />
                    返回行业
                  </Button>
                  <h2 className="truncate text-base font-semibold">{selectedIndustry.name}</h2>
                  <p className="mt-1 line-clamp-2 text-sm text-muted-foreground">
                    {selectedIndustry.description || "暂无行业描述"}
                  </p>
                </div>
                <Button variant="outline" size="sm" onClick={() => setKeywordDialogOpen(true)}>
                  <Plus className="size-4" />
                  关键词
                </Button>
              </div>

              <KeywordList
                keywords={keywords}
                loading={keywordsLoading}
                selectedId={selectedKeyword?.id ?? null}
                onSelect={setSelectedKeyword}
                onDelete={setDeletingKeyword}
              />
            </Card>

            <Card className="min-h-[620px] overflow-hidden p-0">
              <VideoRankingPanel
                industry={selectedIndustry}
                keyword={selectedKeyword}
                videos={videos}
                loading={videosLoading}
                onImport={() => setImportDialogOpen(true)}
              />
            </Card>
          </div>
        )}
      </div>

      <IndustryDialog
        open={industryDialogOpen}
        onOpenChange={setIndustryDialogOpen}
        onCreated={async (item) => {
          setIndustryDialogOpen(false);
          await loadIndustries(1);
          setSelectedIndustry(item);
        }}
      />
      <KeywordDialog
        open={keywordDialogOpen}
        industry={selectedIndustry}
        onOpenChange={setKeywordDialogOpen}
        onCreated={async (item) => {
          setKeywordDialogOpen(false);
          if (selectedIndustry) await loadKeywords(selectedIndustry.id);
          setSelectedKeyword(item);
        }}
      />
      <ImportCsvDialog
        open={importDialogOpen}
        industry={selectedIndustry}
        keyword={selectedKeyword}
        onOpenChange={setImportDialogOpen}
        onImported={async (keywordId) => {
          setImportDialogOpen(false);
          await refreshCurrent();
          const refreshed = await fetchKeywordGroupsPage(selectedIndustry?.id ?? "", 1, 100);
          setSelectedKeyword(refreshed.items.find((item) => item.id === keywordId) ?? null);
        }}
      />
      <ConfirmDialog
        open={deletingIndustry !== null}
        onOpenChange={(open) => {
          if (!open) setDeletingIndustry(null);
        }}
        title="删除行业"
        description={`确定删除「${deletingIndustry?.name ?? ""}」吗？该行业下的关键词集合和视频数据会一起删除。`}
        busy={deleteBusy}
        onConfirm={handleDeleteIndustry}
      />
      <ConfirmDialog
        open={deletingKeyword !== null}
        onOpenChange={(open) => {
          if (!open) setDeletingKeyword(null);
        }}
        title="删除关键词集合"
        description={`确定删除「${deletingKeyword?.keyword ?? ""}」吗？该关键词下的视频数据会一起删除。`}
        busy={deleteBusy}
        onConfirm={handleDeleteKeyword}
      />
    </main>
  );
}

function IndustryGrid({
  industries,
  loading,
  total,
  page,
  onLoadMore,
  onSelect,
  onDelete
}: {
  industries: KeywordIndustry[];
  loading: boolean;
  total: number;
  page: number;
  onLoadMore: () => void;
  onSelect: (industry: KeywordIndustry) => void;
  onDelete: (industry: KeywordIndustry) => void;
}) {
  if (loading && industries.length === 0) {
    return (
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 4 }).map((_, index) => (
          <Skeleton key={index} className="h-40 rounded-lg" />
        ))}
      </div>
    );
  }
  if (industries.length === 0) {
    return (
      <EmptyState
        icon={<Layers3 className="size-8" />}
        title="还没有行业"
        hint="先创建一个行业，再导入该行业下的关键词视频榜单。"
      />
    );
  }
  return (
    <div className="space-y-4">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {industries.map((industry) => (
          <div
            key={industry.id}
            className="rounded-lg border border-border bg-card p-4 text-left shadow-sm transition-colors hover:border-primary hover:bg-accent/40"
          >
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <button
                  type="button"
                  onClick={() => onSelect(industry)}
                  className="block max-w-full truncate text-base font-semibold hover:text-primary"
                >
                  {industry.name}
                </button>
                <p className="mt-1 line-clamp-2 min-h-10 text-sm text-muted-foreground">
                  {industry.description || "暂无描述"}
                </p>
              </div>
              <div className="flex shrink-0 items-center gap-2">
                <Badge variant={industry.status === "active" ? "success" : "secondary"}>
                  {industry.status === "active" ? "启用" : "停用"}
                </Badge>
                <Button
                  variant="ghost"
                  size="icon"
                  className="size-8 text-muted-foreground hover:text-destructive"
                  onClick={() => onDelete(industry)}
                  aria-label="删除行业"
                >
                  <Trash2 className="size-4" />
                </Button>
              </div>
            </div>
            <button
              type="button"
              onClick={() => onSelect(industry)}
              className="mt-5 grid w-full grid-cols-2 gap-3 text-left"
            >
              <MetricBlock label="关键词" value={industry.keyword_count} />
              <MetricBlock label="视频" value={industry.video_count} />
            </button>
            <button
              type="button"
              onClick={() => onSelect(industry)}
              className="mt-4 flex w-full items-center justify-between text-xs text-muted-foreground"
            >
              <span>最后更新</span>
              <span>{formatDate(industry.last_updated_at)}</span>
            </button>
          </div>
        ))}
      </div>
      {industries.length < total ? (
        <div className="flex justify-center">
          <Button variant="outline" disabled={loading} onClick={onLoadMore}>
            加载更多
            <span className="text-xs text-muted-foreground">
              {page * PAGE_SIZE}/{total}
            </span>
          </Button>
        </div>
      ) : null}
    </div>
  );
}

function MetricBlock({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-md border border-border bg-background p-3">
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="mt-1 text-2xl font-semibold tabular-nums">{value}</div>
    </div>
  );
}

function KeywordList({
  keywords,
  loading,
  selectedId,
  onSelect,
  onDelete
}: {
  keywords: KeywordGroup[];
  loading: boolean;
  selectedId: string | null;
  onSelect: (keyword: KeywordGroup) => void;
  onDelete: (keyword: KeywordGroup) => void;
}) {
  if (loading) return <Skeleton className="h-48 rounded-lg" />;
  if (keywords.length === 0) {
    return (
      <EmptyState
        icon={<Search className="size-8" />}
        title="暂无关键词"
        hint="创建关键词或直接导入 CSV 自动创建。"
      />
    );
  }
  return (
    <div className="min-h-0 flex-1 space-y-2 overflow-y-auto pr-1">
      {keywords.map((keyword) => (
        <div
          key={keyword.id}
          className={cn(
            "rounded-md border p-3 text-left transition-colors",
            selectedId === keyword.id
              ? "border-primary bg-accent/60 ring-1 ring-primary/20"
              : "border-border bg-background hover:bg-accent/40"
          )}
        >
          <div className="flex items-center justify-between gap-3">
            <button
              type="button"
              onClick={() => onSelect(keyword)}
              className="flex min-w-0 flex-1 items-center gap-2 text-left"
            >
              <Search className="size-4 shrink-0 text-muted-foreground" />
              <span className="truncate font-medium">{keyword.keyword}</span>
            </button>
            <div className="flex shrink-0 items-center gap-2">
              <Badge variant="outline">{keyword.video_count} 条</Badge>
              <Button
                variant="ghost"
                size="icon"
                className="size-8 text-muted-foreground hover:text-destructive"
                onClick={() => onDelete(keyword)}
                aria-label="删除关键词集合"
              >
                <Trash2 className="size-4" />
              </Button>
            </div>
          </div>
          <button
            type="button"
            onClick={() => onSelect(keyword)}
            className="mt-2 text-left text-xs text-muted-foreground"
          >
            更新于 {formatDate(keyword.last_updated_at)}
          </button>
        </div>
      ))}
    </div>
  );
}

function VideoRankingPanel({
  industry,
  keyword,
  videos,
  loading,
  onImport
}: {
  industry: KeywordIndustry;
  keyword: KeywordGroup | null;
  videos: KeywordVideo[];
  loading: boolean;
  onImport: () => void;
}) {
  return (
    <div className="flex h-full min-h-[620px] flex-col">
      <div className="border-b border-border px-5 py-4">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="text-base font-semibold">
              {keyword ? `${keyword.keyword} 热点视频` : "选择关键词"}
            </h2>
            <p className="text-sm text-muted-foreground">
              {industry.name} · 按综合热度从高到低排序
            </p>
          </div>
          <Button variant="outline" size="sm" onClick={onImport}>
            <FileUp className="size-4" />
            导入
          </Button>
        </div>
      </div>
      <div className="min-h-0 flex-1 overflow-auto">
        {!keyword ? (
          <div className="p-6">
            <EmptyState
              icon={<Search className="size-8" />}
              title="请选择关键词"
              hint="点击左侧关键词集合查看热点视频榜单。"
            />
          </div>
        ) : loading ? (
          <div className="space-y-3 p-5">
            {Array.from({ length: 5 }).map((_, index) => (
              <Skeleton key={index} className="h-24 rounded-lg" />
            ))}
          </div>
        ) : videos.length === 0 ? (
          <div className="p-6">
            <EmptyState
              icon={<FileUp className="size-8" />}
              title="暂无视频数据"
              hint="导入 CSV 后，这里会显示视频链接和流量信息。"
            />
          </div>
        ) : (
          <div className="min-w-[980px]">
            <div className="grid grid-cols-[70px_minmax(260px,1fr)_120px_110px_90px_90px_90px_90px_110px] border-b border-border bg-muted/40 px-4 py-2 text-xs font-medium text-muted-foreground">
              <span>排名</span>
              <span>视频内容</span>
              <span>作者</span>
              <span>粉丝</span>
              <span>点赞</span>
              <span>评论</span>
              <span>收藏</span>
              <span>转发</span>
              <span>综合热度</span>
            </div>
            {videos.map((video) => (
              <div
                key={video.id}
                className="grid grid-cols-[70px_minmax(260px,1fr)_120px_110px_90px_90px_90px_90px_110px] items-center border-b border-border px-4 py-3 text-sm"
              >
                <span className="font-semibold tabular-nums">#{video.rank}</span>
                <div className="min-w-0 pr-4">
                  <div className="line-clamp-2">{video.source_text}</div>
                  {video.source_url ? (
                    <a
                      className="mt-1 inline-flex items-center gap-1 text-xs text-primary hover:underline"
                      href={video.source_url}
                      target="_blank"
                      rel="noreferrer"
                    >
                      视频链接
                      <ExternalLink className="size-3" />
                    </a>
                  ) : (
                    <span className="mt-1 block text-xs text-muted-foreground">无链接</span>
                  )}
                </div>
                <div className="min-w-0">
                  <div className="truncate">{video.author_name || "未知作者"}</div>
                  {video.author_url ? (
                    <a
                      className="text-xs text-primary hover:underline"
                      href={video.author_url}
                      target="_blank"
                      rel="noreferrer"
                    >
                      作者主页
                    </a>
                  ) : null}
                </div>
                <NumberCell value={video.author_follower_count} />
                <NumberCell value={video.likes} />
                <NumberCell value={video.comments} />
                <NumberCell value={video.favorites} />
                <NumberCell value={video.shares} />
                <span className="font-semibold tabular-nums">{formatNumber(video.hot_score)}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function NumberCell({ value }: { value?: number | null }) {
  return <span className="tabular-nums">{value === null || value === undefined ? "-" : formatNumber(value)}</span>;
}

function IndustryDialog({
  open,
  onOpenChange,
  onCreated
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreated: (item: KeywordIndustry) => void | Promise<void>;
}) {
  const [name, setName] = React.useState("");
  const [description, setDescription] = React.useState("");
  const [status, setStatus] = React.useState<"active" | "inactive">("active");
  const [busy, setBusy] = React.useState(false);

  React.useEffect(() => {
    if (!open) return;
    setName("");
    setDescription("");
    setStatus("active");
  }, [open]);

  async function handleSubmit() {
    if (!name.trim()) {
      toast.error("请输入行业名称");
      return;
    }
    setBusy(true);
    try {
      const item = await createKeywordIndustry({
        name: name.trim(),
        description: description.trim() || null,
        status
      });
      toast.success("行业已创建");
      await onCreated(item);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "创建行业失败");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>创建行业</DialogTitle>
          <DialogDescription>用于归集同一赛道下的多个关键词榜单。</DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-2">
            <Label>行业名称</Label>
            <Input value={name} onChange={(event) => setName(event.target.value)} placeholder="贷款行业" />
          </div>
          <div className="space-y-2">
            <Label>行业描述</Label>
            <Textarea
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              placeholder="贷款、征信、经营贷相关热点视频"
            />
          </div>
          <div className="space-y-2">
            <Label>状态</Label>
            <select
              value={status}
              onChange={(event) => setStatus(event.target.value as "active" | "inactive")}
              className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
            >
              <option value="active">启用</option>
              <option value="inactive">停用</option>
            </select>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            取消
          </Button>
          <Button disabled={busy} onClick={handleSubmit}>
            创建
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function KeywordDialog({
  open,
  industry,
  onOpenChange,
  onCreated
}: {
  open: boolean;
  industry: KeywordIndustry | null;
  onOpenChange: (open: boolean) => void;
  onCreated: (item: KeywordGroup) => void | Promise<void>;
}) {
  const [keyword, setKeyword] = React.useState("");
  const [busy, setBusy] = React.useState(false);

  React.useEffect(() => {
    if (open) setKeyword("");
  }, [open]);

  async function handleSubmit() {
    if (!industry) return;
    if (!keyword.trim()) {
      toast.error("请输入关键词");
      return;
    }
    setBusy(true);
    try {
      const item = await createKeywordGroup({ industry_id: industry.id, keyword: keyword.trim() });
      toast.success("关键词已创建");
      await onCreated(item);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "创建关键词失败");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>创建关键词集合</DialogTitle>
          <DialogDescription>{industry?.name ?? "当前行业"} 下的新关键词榜单。</DialogDescription>
        </DialogHeader>
        <div className="space-y-2">
          <Label>关键词</Label>
          <Input value={keyword} onChange={(event) => setKeyword(event.target.value)} placeholder="借钱" />
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            取消
          </Button>
          <Button disabled={busy || !industry} onClick={handleSubmit}>
            创建
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function ImportCsvDialog({
  open,
  industry,
  keyword,
  onOpenChange,
  onImported
}: {
  open: boolean;
  industry: KeywordIndustry | null;
  keyword: KeywordGroup | null;
  onOpenChange: (open: boolean) => void;
  onImported: (keywordId: string) => void | Promise<void>;
}) {
  const [keywordText, setKeywordText] = React.useState("");
  const [file, setFile] = React.useState<File | null>(null);
  const [busy, setBusy] = React.useState(false);

  React.useEffect(() => {
    if (!open) return;
    setKeywordText(keyword?.keyword ?? "");
    setFile(null);
  }, [keyword?.keyword, open]);

  async function handleSubmit() {
    if (!industry) return;
    if (!keywordText.trim()) {
      toast.error("请输入关键词");
      return;
    }
    if (!file) {
      toast.error("请选择 CSV 文件");
      return;
    }
    setBusy(true);
    try {
      const csv_text = await file.text();
      const result = await importKeywordVideos({
        industry_id: industry.id,
        keyword: keywordText.trim(),
        csv_text
      });
      toast.success(
        `导入完成：新增 ${result.created_count} 条，更新 ${result.updated_count} 条，失败 ${result.failed_count} 条`
      );
      if (result.errors.length > 0) {
        toast.message(`首个错误：第 ${result.errors[0].row_number} 行 ${result.errors[0].message}`);
      }
      await onImported(result.keyword_id);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "导入 CSV 失败");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>导入关键词视频 CSV</DialogTitle>
          <DialogDescription>
            当前行业：{industry?.name ?? "未选择"}。关键词不存在时会自动创建。
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-2">
            <Label>关键词</Label>
            <Input
              value={keywordText}
              onChange={(event) => setKeywordText(event.target.value)}
              placeholder="借钱"
            />
          </div>
          <div className="space-y-2">
            <Label>CSV 文件</Label>
            <label className="flex min-h-24 cursor-pointer flex-col items-center justify-center gap-2 rounded-md border border-dashed border-border bg-muted/30 px-4 py-5 text-sm hover:bg-accent/40">
              <FileUp className="size-5 text-muted-foreground" />
              <span>{file ? file.name : "点击选择 CSV 文件"}</span>
              <input
                type="file"
                accept=".csv,text/csv"
                className="hidden"
                onChange={(event) => setFile(event.target.files?.[0] ?? null)}
              />
            </label>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            取消
          </Button>
          <Button disabled={busy || !industry} onClick={handleSubmit}>
            导入
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function formatNumber(value: number): string {
  return value.toLocaleString("zh-CN", { maximumFractionDigits: 2 });
}

function formatDate(value?: string | null): string {
  if (!value) return "暂无";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "暂无";
  return date.toLocaleDateString("zh-CN");
}
