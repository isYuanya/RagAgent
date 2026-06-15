import * as React from "react";
import { toast } from "sonner";
import { Sidebar, type AppView } from "@/features/Sidebar";
import { CsvUpload } from "@/features/CsvUpload";
import { ImportProgress, ImportErrors } from "@/features/ImportProgress";
import { AssetList } from "@/features/AssetList";
import { ReviewPanel } from "@/features/ReviewPanel";
import { KnowledgeView } from "@/features/knowledge/KnowledgeView";
import { Card } from "@/components/ui/card";
import {
  fetchAssets,
  fetchTask,
  importCsv,
  saveReview
} from "@/lib/api";
import type { Analysis, CopyAsset, TaskProgress, TaskResponse } from "@/lib/types";

export function App() {
  const [view, setView] = React.useState<AppView>("workbench");
  const [assets, setAssets] = React.useState<CopyAsset[]>([]);
  const [listLoading, setListLoading] = React.useState(true);
  const [selectedId, setSelectedId] = React.useState<string | null>(null);
  const [saving, setSaving] = React.useState(false);
  const [importing, setImporting] = React.useState(false);
  const [importTask, setImportTask] = React.useState<TaskResponse | null>(null);
  const [errors, setErrors] = React.useState<TaskProgress["errors"]>([]);

  const selected = assets.find((asset) => asset.id === selectedId) ?? null;

  const loadAssets = React.useCallback(async () => {
    try {
      const items = await fetchAssets();
      setAssets(items);
      setSelectedId((current) => current ?? items[0]?.id ?? null);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "加载资产失败");
    } finally {
      setListLoading(false);
    }
  }, []);

  React.useEffect(() => {
    void loadAssets();
  }, [loadAssets]);

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
        void loadAssets();
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
        await loadAssets();
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

  return (
    <div className="flex min-h-screen bg-background">
      <Sidebar
        view={view}
        onChangeView={setView}
        assetCount={assets.length}
      />

      {view === "knowledge" ? (
        <KnowledgeView />
      ) : (
        <main className="flex min-w-0 flex-1 flex-col">
          <header className="flex items-center justify-between gap-4 border-b border-border px-6 py-4">
            <div>
              <h1 className="text-lg font-semibold">文案资产审核工作台</h1>
              <p className="text-sm text-muted-foreground">
                批量导入样本文案，校正拆解结果，沉淀为可检索的文案资产。
              </p>
            </div>
            <CsvUpload
              busy={importing}
              disabled={importing || saving}
              onFile={handleUpload}
            />
          </header>

          <div className="grid min-h-0 flex-1 grid-cols-1 gap-4 p-6 lg:grid-cols-[minmax(320px,420px)_1fr]">
            <Card className="flex min-h-0 flex-col overflow-hidden p-4">
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
                  onSelect={setSelectedId}
                />
              </div>
            </Card>

            <Card className="flex min-h-0 flex-col overflow-hidden p-0">
              <ReviewPanel asset={selected} saving={saving} onSave={handleSave} />
            </Card>
          </div>
        </main>
      )}
    </div>
  );
}
