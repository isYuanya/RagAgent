import * as React from "react";
import { AlertTriangle } from "lucide-react";
import { toast } from "sonner";
import { Sidebar, type AppView } from "@/features/Sidebar";
import { CsvUpload } from "@/features/CsvUpload";
import { TextImportDialog } from "@/features/TextImportDialog";
import { ImportProgress, ImportErrors } from "@/features/ImportProgress";
import { AssetList } from "@/features/AssetList";
import { ReviewPanel } from "@/features/ReviewPanel";
import { DraftWorkbenchView } from "@/features/drafts/DraftWorkbenchView";
import { DiagnosticView } from "@/features/diagnostics/DiagnosticView";
import { KnowledgeView } from "@/features/knowledge/KnowledgeView";
import { SystemStatusBadge } from "@/features/system/SystemStatusBadge";
import { SystemStatusView } from "@/features/system/SystemStatusView";
import { getService, isServiceDown } from "@/features/system/statusUtils";
import { Badge } from "@/components/ui/badge";
import { ConfirmDialog } from "@/features/shared/ConfirmDialog";
import { Card } from "@/components/ui/card";
import {
  deleteAsset,
  fetchAssets,
  fetchSystemStatus,
  fetchTask,
  importCsv,
  importText,
  saveReview
} from "@/lib/api";
import type {
  Analysis,
  CopyAsset,
  SystemStatusResponse,
  TaskProgress,
  TaskResponse
} from "@/lib/types";

function getFirstImportedAssetId(task: TaskResponse): string | null {
  const assetIds = task.result?.asset_ids;
  return Array.isArray(assetIds) && typeof assetIds[0] === "string"
    ? assetIds[0]
    : null;
}

function ServiceDependencyWarnings({
  redisDown,
  workerDown,
  postgresDown,
  workerMessage
}: {
  redisDown: boolean;
  workerDown: boolean;
  postgresDown: boolean;
  workerMessage?: string;
}) {
  if (!redisDown && !workerDown && !postgresDown) return null;

  return (
    <div className="mb-3 space-y-2 rounded-lg border border-border bg-muted/30 p-3 text-sm">
      {redisDown ? (
        <DependencyWarning
          tone="danger"
          title="Redis 不可用"
          text="任务队列不可用，导入功能已暂停。"
        />
      ) : null}
      {workerDown ? (
        <DependencyWarning
          tone="warning"
          title="导入 Worker 未就绪"
          text={
            workerMessage ??
            "导入任务可能会一直停留在队列中，请启动 worker。"
          }
        />
      ) : null}
      {postgresDown ? (
        <DependencyWarning
          tone="danger"
          title="PostgreSQL 不可用"
          text="数据可能无法真正落库，请先检查数据库服务。"
        />
      ) : null}
    </div>
  );
}

function DependencyWarning({
  tone,
  title,
  text
}: {
  tone: "danger" | "warning";
  title: string;
  text: string;
}) {
  return (
    <div className="flex items-start gap-2">
      <AlertTriangle
        className={
          tone === "danger"
            ? "mt-0.5 size-4 text-destructive"
            : "mt-0.5 size-4 text-amber-700"
        }
      />
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="font-medium">{title}</span>
          <Badge variant={tone === "danger" ? "destructive" : "outline"}>
            {tone === "danger" ? "阻塞" : "提醒"}
          </Badge>
        </div>
        <p className="text-xs text-muted-foreground">{text}</p>
      </div>
    </div>
  );
}

export function App() {
  const [view, setView] = React.useState<AppView>("workbench");
  const [assets, setAssets] = React.useState<CopyAsset[]>([]);
  const [listLoading, setListLoading] = React.useState(true);
  const [selectedId, setSelectedId] = React.useState<string | null>(null);
  const [saving, setSaving] = React.useState(false);
  const [deleting, setDeleting] = React.useState<CopyAsset | null>(null);
  const [deleteBusy, setDeleteBusy] = React.useState(false);
  const [importing, setImporting] = React.useState(false);
  const [importTask, setImportTask] = React.useState<TaskResponse | null>(null);
  const [errors, setErrors] = React.useState<TaskProgress["errors"]>([]);
  const [systemStatus, setSystemStatus] =
    React.useState<SystemStatusResponse | null>(null);
  const [statusLoading, setStatusLoading] = React.useState(false);
  const [statusCheckedAt, setStatusCheckedAt] = React.useState<Date | null>(
    null
  );
  const [autoRefreshStatus, setAutoRefreshStatus] = React.useState(true);

  const selected = assets.find((asset) => asset.id === selectedId) ?? null;
  const redisDown = isServiceDown(systemStatus, "redis");
  const workerDown = isServiceDown(systemStatus, "copy_import_worker");
  const postgresDown = isServiceDown(systemStatus, "postgres");
  const importDisabled = importing || saving || redisDown;

  const statusBadge = (
    <SystemStatusBadge
      status={systemStatus}
      loading={statusLoading}
      onClick={() => setView("system")}
    />
  );

  const loadAssets = React.useCallback(async (preferredId?: string | null) => {
    try {
      const items = await fetchAssets();
      setAssets(items);
      setSelectedId((current) => preferredId ?? current ?? items[0]?.id ?? null);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "加载资产失败");
    } finally {
      setListLoading(false);
    }
  }, []);

  React.useEffect(() => {
    void loadAssets();
  }, [loadAssets]);

  const loadSystemStatus = React.useCallback(async (notifyOnError = true) => {
    setStatusLoading(true);
    try {
      setSystemStatus(await fetchSystemStatus());
      setStatusCheckedAt(new Date());
    } catch (error) {
      setSystemStatus(null);
      if (notifyOnError) {
        toast.error(error instanceof Error ? error.message : "加载服务状态失败");
      }
    } finally {
      setStatusLoading(false);
    }
  }, []);

  React.useEffect(() => {
    void loadSystemStatus();
  }, [loadSystemStatus]);

  React.useEffect(() => {
    if (!autoRefreshStatus) return;
    const timer = window.setInterval(() => {
      void loadSystemStatus(false);
    }, 5000);
    return () => window.clearInterval(timer);
  }, [autoRefreshStatus, loadSystemStatus]);

  // poll import task progress
  React.useEffect(() => {
    if (!importTask || !["queued", "running"].includes(importTask.status))
      return;

    const timer = window.setInterval(async () => {
      const payload = await fetchTask(importTask.task_id);
      if (!payload) return;
      setImportTask(payload);
      setErrors(payload.progress?.errors ?? []);

      if (payload.status === "finished") {
        setImporting(false);
        toast.success("导入完成");
        void loadAssets(getFirstImportedAssetId(payload));
      }
      if (payload.status === "failed") {
        setImporting(false);
        toast.error(payload.error ?? "导入失败");
      }
    }, 1000);

    return () => window.clearInterval(timer);
  }, [importTask?.task_id, importTask?.status, loadAssets]);

  async function handleUpload(file: File) {
    setImporting(true);
    setImportTask(null);
    setErrors([]);
    try {
      const csvText = await file.text();
      const task = await importCsv(csvText);
      setImportTask(task);
      setErrors(task.progress?.errors ?? []);
      if (task.status === "finished") {
        setImporting(false);
        toast.success("导入完成");
        await loadAssets(getFirstImportedAssetId(task));
      } else {
        toast.message(task.progress?.current_message ?? "导入任务已创建");
      }
    } catch (error) {
      setImporting(false);
      toast.error(error instanceof Error ? error.message : "导入失败");
    }
  }

  async function handleTextImport(text: string) {
    setImporting(true);
    setImportTask(null);
    setErrors([]);
    try {
      const task = await importText(text);
      setImportTask(task);
      setErrors(task.progress?.errors ?? []);
      if (task.status === "finished") {
        setImporting(false);
        toast.success("导入完成");
        await loadAssets(getFirstImportedAssetId(task));
      } else {
        toast.message(task.progress?.current_message ?? "导入任务已创建");
      }
    } catch (error) {
      setImporting(false);
      toast.error(error instanceof Error ? error.message : "导入失败");
    }
  }

  async function handleSave(status: string, draft: Analysis) {
    if (!selected) return;
    setSaving(true);
    try {
      const updated = await saveReview(selected.id, status, draft);
      setAssets((current) =>
        current.map((asset) => (asset.id === selected.id ? updated : asset))
      );
      toast.success("审核结果已保存");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "保存失败");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    if (!deleting) return;
    setDeleteBusy(true);
    try {
      await deleteAsset(deleting.id);
      const nextAssets = assets.filter((asset) => asset.id !== deleting.id);
      setAssets(nextAssets);
      if (selectedId === deleting.id) {
        setSelectedId(nextAssets[0]?.id ?? null);
      }
      toast.success("待审文案已删除");
      setDeleting(null);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "删除失败");
    } finally {
      setDeleteBusy(false);
    }
  }

  return (
    <div className="flex min-h-screen bg-background">
      <Sidebar
        view={view}
        onChangeView={setView}
        assetCount={assets.length}
      />

      {view === "system" ? (
        <SystemStatusView
          status={systemStatus}
          loading={statusLoading}
          lastCheckedAt={statusCheckedAt}
          autoRefresh={autoRefreshStatus}
          onAutoRefreshChange={setAutoRefreshStatus}
          onRefresh={() => void loadSystemStatus()}
        />
      ) : view === "drafts" ? (
        <DraftWorkbenchView headerAction={statusBadge} />
      ) : view === "diagnostics" ? (
        <DiagnosticView headerAction={statusBadge} />
      ) : view === "knowledge" ? (
        <KnowledgeView headerAction={statusBadge} />
      ) : (
        <main className="flex min-w-0 flex-1 flex-col">
          <header className="flex items-center justify-between gap-4 border-b border-border px-6 py-4">
            <div>
              <h1 className="text-lg font-semibold">文案资产审核工作台</h1>
              <p className="text-sm text-muted-foreground">
                批量导入样本文案，校正拆解结果，沉淀为可检索的文案资产。
              </p>
            </div>
            <div className="flex shrink-0 items-center gap-2">
              {statusBadge}
              <TextImportDialog
                busy={importing}
                disabled={importDisabled}
                onSubmit={handleTextImport}
              />
              <CsvUpload
                busy={importing}
                disabled={importDisabled}
                onFile={handleUpload}
              />
            </div>
          </header>

          <div className="grid min-h-0 flex-1 grid-cols-1 gap-4 p-6 lg:grid-cols-[minmax(320px,420px)_1fr]">
            <Card className="flex min-h-0 flex-col overflow-hidden p-4">
              <ServiceDependencyWarnings
                redisDown={redisDown}
                workerDown={workerDown}
                postgresDown={postgresDown}
                workerMessage={getService(systemStatus, "copy_import_worker")?.message}
              />
              {importTask?.progress ? (
                <div className="mb-3">
                  <ImportProgress task={importTask} />
                </div>
              ) : null}
              {errors.length > 0 ? (
                <div className="mb-3">
                  <ImportErrors errors={errors} />
                </div>
              ) : null}
              <div className="mb-3 text-sm font-semibold">导入与待审</div>
              <div className="min-h-0 flex-1">
                <AssetList
                  assets={assets}
                  loading={listLoading}
                  selectedId={selectedId}
                  deletingId={deleting?.id ?? null}
                  onSelect={setSelectedId}
                  onDelete={setDeleting}
                />
              </div>
            </Card>

            <Card className="flex min-h-0 flex-col overflow-hidden p-0">
              <ReviewPanel asset={selected} saving={saving} onSave={handleSave} />
            </Card>
          </div>

          <ConfirmDialog
            open={deleting !== null}
            onOpenChange={(open) => !open && setDeleting(null)}
            title="删除待审文案"
            description="删除后该文案资产不再出现在待审列表中。"
            busy={deleteBusy}
            onConfirm={handleDelete}
          />
        </main>
      )}
    </div>
  );
}
