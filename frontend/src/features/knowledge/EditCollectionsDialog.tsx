import * as React from "react";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { updateRawCopy } from "@/lib/api";
import type { KnowledgeCollection, RawCopySummary } from "@/lib/types";

export function EditCollectionsDialog({
  open,
  onOpenChange,
  rawCopy,
  collections,
  onSaved
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  rawCopy: RawCopySummary | null;
  collections: KnowledgeCollection[];
  onSaved: (updated: RawCopySummary) => void;
}) {
  const [selected, setSelected] = React.useState<string[]>([]);
  const [busy, setBusy] = React.useState(false);

  React.useEffect(() => {
    if (!open) return;
    setSelected(rawCopy?.collection_ids ?? []);
  }, [open, rawCopy]);

  function toggle(id: string) {
    setSelected((current) =>
      current.includes(id)
        ? current.filter((x) => x !== id)
        : [...current, id]
    );
  }

  async function handleSave() {
    if (!rawCopy) return;
    setBusy(true);
    try {
      const updated = await updateRawCopy(rawCopy.id, {
        collection_ids: selected
      });
      toast.success("已更新所属集合");
      onOpenChange(false);
      onSaved(updated);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "更新失败");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>设置所属集合</DialogTitle>
        </DialogHeader>
        <div className="py-2">
          {collections.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              还没有集合，请先到「集合」标签创建。
            </p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {collections.map((collection) => {
                const active = selected.includes(collection.id);
                return (
                  <button
                    key={collection.id}
                    type="button"
                    onClick={() => toggle(collection.id)}
                  >
                    <Badge
                      variant={active ? "default" : "outline"}
                      className={cn(
                        "cursor-pointer select-none",
                        !active && "hover:bg-accent"
                      )}
                    >
                      {collection.name}
                    </Badge>
                  </button>
                );
              })}
            </div>
          )}
        </div>
        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={busy}
          >
            取消
          </Button>
          <Button
            onClick={handleSave}
            disabled={busy || collections.length === 0}
          >
            {busy ? <Loader2 className="animate-spin" /> : null}
            保存
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
