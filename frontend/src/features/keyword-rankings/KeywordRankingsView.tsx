import * as React from "react";
import {
  ExternalLink,
  FileUp,
  Loader2,
  Plus,
  Search,
  Trash2
} from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
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
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/features/shared/EmptyState";
import { ConfirmDialog } from "@/features/shared/ConfirmDialog";
import {
  createKeywordGroup,
  createKeywordIndustry,
  deleteKeywordGroup,
  fetchKeywordGroupsPage,
  fetchKeywordIndustriesPage,
  fetchKeywordVideosPage,
  importKeywordVideos
} from "@/lib/api";
import type { KeywordGroup, KeywordIndustry, KeywordVideo } from "@/lib/types";

const DEFAULT_INDUSTRY_NAME = "贷款";
const KEYWORD_PAGE_SIZE = 100;
const TOP_VIDEO_COUNT = 10;

type RankingBoard = {
  industry: KeywordIndustry;
  keyword: KeywordGroup;
  videos: KeywordVideo[];
  loading: boolean;
};

export function KeywordRankingsView({
  headerAction
}: {
  headerAction?: React.ReactNode;
}) {
  const [industries, setIndustries] = React.useState<KeywordIndustry[]>([]);
  const [boards, setBoards] = React.useState<RankingBoard[]>([]);
  const [searchText, setSearchText] = React.useState("");
  const [loading, setLoading] = React.useState(true);
  const [actionBusy, setActionBusy] = React.useState(false);
  const [importTarget, setImportTarget] = React.useState<RankingBoard | null>(null);
  const [deletingBoard, setDeletingBoard] = React.useState<RankingBoard | null>(null);
  const [deleteBusy, setDeleteBusy] = React.useState(false);

  const loadTopVideos = React.useCallback(async (keyword: KeywordGroup) => {
    const payload = await fetchKeywordVideosPage(keyword.id, 1, TOP_VIDEO_COUNT);
    return payload.items;
  }, []);

  const loadBoards = React.useCallback(async () => {
    setLoading(true);
    try {
      const industryPayload = await fetchKeywordIndustriesPage(1, 100);
      setIndustries(industryPayload.items);
      const keywordResults = await Promise.all(
        industryPayload.items.map(async (industry) => {
          const keywordPayload = await fetchKeywordGroupsPage(
            industry.id,
            1,
            KEYWORD_PAGE_SIZE
          );
          return keywordPayload.items.map((keyword) => ({ industry, keyword }));
        })
      );
      const entries = keywordResults.flat();
      const nextBoards = await Promise.all(
        entries.map(async ({ industry, keyword }) => ({
          industry,
          keyword,
          videos: await loadTopVideos(keyword),
          loading: false
        }))
      );
      setBoards(nextBoards);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "加载关键词榜单失败");
      setBoards([]);
    } finally {
      setLoading(false);
    }
  }, [loadTopVideos]);

  React.useEffect(() => {
    void loadBoards();
  }, [loadBoards]);

  async function ensureDefaultIndustry() {
    const active = industries.find((item) => item.status === "active");
    if (active) return active;
    const existing = industries[0];
    if (existing) return existing;
    const created = await createKeywordIndustry({
      name: DEFAULT_INDUSTRY_NAME,
      description: "贷款、征信、经营贷相关热点视频",
      status: "active"
    });
    setIndustries([created]);
    return created;
  }

  async function handleAddBoard() {
    const keywordText = searchText.trim();
    if (!keywordText) {
      toast.error("请输入关键词");
      return;
    }
    setActionBusy(true);
    try {
      const existingBoard = boards.find(
        (board) => board.keyword.keyword.toLowerCase() === keywordText.toLowerCase()
      );
      if (existingBoard) {
        await refreshBoard(existingBoard.keyword.id);
        toast.success("已刷新该关键词 Top10 榜单");
        return;
      }

      const industry = await ensureDefaultIndustry();
      const keyword = await createKeywordGroup({
        industry_id: industry.id,
        keyword: keywordText
      });
      const videos = await loadTopVideos(keyword);
      setBoards((current) => [
        ...current,
        { industry, keyword, videos, loading: false }
      ]);
      toast.success(videos.length > 0 ? "榜单已添加" : "关键词已添加，可导入 CSV 后生成榜单");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "添加关键词榜单失败");
    } finally {
      setActionBusy(false);
    }
  }

  async function refreshBoard(keywordId: string) {
    setBoards((current) =>
      current.map((board) =>
        board.keyword.id === keywordId ? { ...board, loading: true } : board
      )
    );
    try {
      const videos = await fetchKeywordVideosPage(keywordId, 1, TOP_VIDEO_COUNT);
      setBoards((current) =>
        current.map((board) =>
          board.keyword.id === keywordId
            ? {
                ...board,
                keyword: { ...board.keyword, video_count: videos.total },
                videos: videos.items,
                loading: false
              }
            : board
        )
      );
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "刷新榜单失败");
      setBoards((current) =>
        current.map((board) =>
          board.keyword.id === keywordId ? { ...board, loading: false } : board
        )
      );
    }
  }

  async function handleDeleteBoard() {
    if (!deletingBoard) return;
    setDeleteBusy(true);
    try {
      await deleteKeywordGroup(deletingBoard.keyword.id);
      setBoards((current) =>
        current.filter((board) => board.keyword.id !== deletingBoard.keyword.id)
      );
      setDeletingBoard(null);
      toast.success("关键词榜单已删除");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "删除关键词榜单失败");
    } finally {
      setDeleteBusy(false);
    }
  }

  return (
    <main className="flex min-w-0 flex-1 flex-col">
      <header className="border-b border-border px-6 py-4">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-lg font-semibold">关键词榜单</h1>
            <p className="text-sm text-muted-foreground">
              直接查看关键词 Top10 热点视频，新增关键词会追加到下方榜单墙。
            </p>
          </div>
          <div className="flex shrink-0 items-center gap-2">{headerAction}</div>
        </div>
        <div className="mt-4 flex max-w-3xl items-center gap-2">
          <div className="relative min-w-0 flex-1">
            <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={searchText}
              onChange={(event) => setSearchText(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") void handleAddBoard();
              }}
              className="pl-9"
              placeholder="输入关键词，例如：征信查询太多影响贷款吗"
            />
          </div>
          <Button onClick={handleAddBoard} disabled={actionBusy}>
            {actionBusy ? <Loader2 className="size-4 animate-spin" /> : <Plus className="size-4" />}
            添加榜单
          </Button>
        </div>
      </header>

      <div className="min-h-0 flex-1 overflow-auto p-6">
        {loading ? (
          <div className="grid min-w-[1120px] grid-cols-2 items-start gap-4">
            {Array.from({ length: 4 }).map((_, index) => (
              <Skeleton key={index} className="h-[440px] rounded-lg" />
            ))}
          </div>
        ) : boards.length === 0 ? (
          <EmptyState
            icon={<Search className="size-8" />}
            title="还没有关键词榜单"
            hint="在顶部输入关键词并添加榜单，或先导入 CSV 生成对应数据。"
          />
        ) : (
          <div className="grid min-w-[1120px] grid-cols-2 items-start gap-4">
            {boards.map((board) => (
              <RankingCard
                key={board.keyword.id}
                board={board}
                onRefresh={() => void refreshBoard(board.keyword.id)}
                onImport={() => setImportTarget(board)}
                onDelete={() => setDeletingBoard(board)}
              />
            ))}
          </div>
        )}
      </div>

      <ImportCsvDialog
        open={importTarget !== null}
        industry={importTarget?.industry ?? null}
        keyword={importTarget?.keyword ?? null}
        onOpenChange={(open) => {
          if (!open) setImportTarget(null);
        }}
        onImported={async (keywordId) => {
          setImportTarget(null);
          await refreshBoard(keywordId);
        }}
      />
      <ConfirmDialog
        open={deletingBoard !== null}
        onOpenChange={(open) => {
          if (!open) setDeletingBoard(null);
        }}
        title="删除关键词榜单"
        description={`确定删除「${deletingBoard?.keyword.keyword ?? ""}」吗？该关键词下的视频数据会一起删除。`}
        busy={deleteBusy}
        onConfirm={handleDeleteBoard}
      />
    </main>
  );
}

function RankingCard({
  board,
  onRefresh,
  onImport,
  onDelete
}: {
  board: RankingBoard;
  onRefresh: () => void;
  onImport: () => void;
  onDelete: () => void;
}) {
  return (
    <Card className="flex h-[520px] min-w-0 flex-col overflow-hidden">
      <div className="flex items-start justify-between gap-3 border-b border-border px-4 py-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <h2 className="truncate text-base font-semibold">{board.keyword.keyword}</h2>
            <Badge variant="outline">Top10</Badge>
          </div>
          <p className="mt-1 text-xs text-muted-foreground">
            {board.industry.name} · 共 {board.keyword.video_count} 条视频
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-1">
          <Button variant="outline" size="sm" onClick={onRefresh} disabled={board.loading}>
            {board.loading ? <Loader2 className="size-4 animate-spin" /> : null}
            刷新
          </Button>
          <Button variant="outline" size="sm" onClick={onImport}>
            <FileUp className="size-4" />
            导入
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="size-8 text-muted-foreground hover:text-destructive"
            onClick={onDelete}
            aria-label="删除关键词榜单"
          >
            <Trash2 className="size-4" />
          </Button>
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto">
        {board.loading ? (
          <div className="space-y-3 p-4">
            {Array.from({ length: 5 }).map((_, index) => (
              <Skeleton key={index} className="h-14 rounded-md" />
            ))}
          </div>
        ) : board.videos.length === 0 ? (
          <div className="p-5">
            <EmptyState
              icon={<FileUp className="size-8" />}
              title="暂无视频数据"
              hint="点击本卡片右上角“导入”，上传该关键词 CSV 后生成 Top10。"
            />
          </div>
        ) : (
          <div className="divide-y divide-border">
            {board.videos.map((video) => (
              <VideoRow key={video.id} video={video} />
            ))}
          </div>
        )}
      </div>
    </Card>
  );
}

function VideoRow({ video }: { video: KeywordVideo }) {
  return (
    <div className="grid min-h-[82px] grid-cols-[38px_minmax(0,1fr)_96px] gap-2 px-4 py-2.5 text-sm">
      <div className="font-semibold tabular-nums text-primary">#{video.rank}</div>
      <div className="min-w-0">
        <div className="max-h-10 overflow-hidden text-foreground [display:-webkit-box] [-webkit-box-orient:vertical] [-webkit-line-clamp:2]">
          {video.source_text}
        </div>
        <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
          <span>{video.author_name || "未知作者"}</span>
          <span>赞 {formatNumber(video.likes)}</span>
          <span>评 {formatNumber(video.comments)}</span>
          <span>藏 {formatNumber(video.favorites)}</span>
          <span>转 {formatNumber(video.shares)}</span>
        </div>
      </div>
      <div className="flex flex-col items-end justify-between gap-2">
        <span className="rounded-md bg-primary/10 px-2 py-1 text-xs font-semibold tabular-nums text-primary">
          {formatNumber(video.hot_score)}
        </span>
        {video.source_url ? (
          <a
            className="inline-flex items-center gap-1 text-xs text-primary hover:underline"
            href={video.source_url}
            target="_blank"
            rel="noreferrer"
          >
            视频
            <ExternalLink className="size-3" />
          </a>
        ) : (
          <span className="text-xs text-muted-foreground">无链接</span>
        )}
      </div>
    </div>
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
  const [file, setFile] = React.useState<File | null>(null);
  const [busy, setBusy] = React.useState(false);

  React.useEffect(() => {
    if (open) setFile(null);
  }, [open]);

  async function handleSubmit() {
    if (!industry || !keyword) return;
    if (!file) {
      toast.error("请选择 CSV 文件");
      return;
    }
    setBusy(true);
    try {
      const csv_text = await file.text();
      const result = await importKeywordVideos({
        industry_id: industry.id,
        keyword: keyword.keyword,
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
            当前关键词：{keyword?.keyword ?? "未选择"}。重复视频会更新数据，不会重复创建。
          </DialogDescription>
        </DialogHeader>
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
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            取消
          </Button>
          <Button disabled={busy || !industry || !keyword} onClick={handleSubmit}>
            {busy ? <Loader2 className="size-4 animate-spin" /> : null}
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
