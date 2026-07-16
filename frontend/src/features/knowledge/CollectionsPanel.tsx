import * as React from "react";
import { toast } from "sonner";
import { Library, Pencil, Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { deleteCollection } from "@/lib/api";
import type { KnowledgeCollection } from "@/lib/types";
import { EmptyState } from "@/features/shared/EmptyState";
import { ConfirmDialog } from "@/features/shared/ConfirmDialog";
import { CollectionDialog } from "./CollectionDialog";

export function CollectionsPanel({
  collections,
  total,
  loading,
  onChanged
}: {
  collections: KnowledgeCollection[];
  total: number;
  loading: boolean;
  onChanged: () => void;
}) {
  void total;
  const [dialogOpen, setDialogOpen] = React.useState(false);
  const [editing, setEditing] = React.useState<KnowledgeCollection | null>(null);
  const [deleting, setDeleting] = React.useState<KnowledgeCollection | null>(
    null
  );
  const [deleteBusy, setDeleteBusy] = React.useState(false);

  function openCreate() {
    setEditing(null);
    setDialogOpen(true);
  }

  function openEdit(collection: KnowledgeCollection) {
    setEditing(collection);
    setDialogOpen(true);
  }

  async function handleDelete() {
    if (!deleting) return;
    setDeleteBusy(true);
    try {
      await deleteCollection(deleting.id);
      toast.success("集合已删除");
      setDeleting(null);
      onChanged();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "删除失败");
    } finally {
      setDeleteBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold">集合（{collections.length}）</h2>
        <Button size="sm" onClick={openCreate}>
          <Plus /> 新建集合
        </Button>
      </div>

      {loading ? (
        <div className="space-y-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-16 w-full rounded-xl" />
          ))}
        </div>
      ) : collections.length === 0 ? (
        <EmptyState
          icon={<Library className="size-8" />}
          title="还没有集合"
          hint="集合用于把文案归类，例如美妆库、高转化库、某账号库。"
        />
      ) : (
        <div className="space-y-2">
          {collections.map((collection) => (
            <Card
              key={collection.id}
              className="flex items-center justify-between gap-3 p-4"
            >
              <div className="min-w-0">
                <div className="truncate text-sm font-medium">
                  {collection.name}
                </div>
                {collection.description ? (
                  <div className="mt-0.5 line-clamp-1 text-xs text-muted-foreground">
                    {collection.description}
                  </div>
                ) : null}
              </div>
              <div className="flex shrink-0 gap-1">
                <Button
                  size="icon"
                  variant="ghost"
                  onClick={() => openEdit(collection)}
                  aria-label="编辑"
                >
                  <Pencil />
                </Button>
                <Button
                  size="icon"
                  variant="ghost"
                  onClick={() => setDeleting(collection)}
                  aria-label="删除"
                >
                  <Trash2 />
                </Button>
              </div>
            </Card>
          ))}
        </div>
      )}

      <CollectionDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        collection={editing}
        onSaved={onChanged}
      />
      <ConfirmDialog
        open={deleting !== null}
        onOpenChange={(open) => !open && setDeleting(null)}
        title="删除集合"
        description={`确定删除「${deleting?.name ?? ""}」？文案与该集合的关联会一并移除。`}
        busy={deleteBusy}
        onConfirm={handleDelete}
      />
    </div>
  );
}
