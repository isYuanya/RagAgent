import * as React from "react";
import { Loader2 } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { createCollection, updateCollection } from "@/lib/api";
import { toast } from "sonner";
import type { KnowledgeCollection } from "@/lib/types";

export function CollectionDialog({
  open,
  onOpenChange,
  collection,
  onSaved
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  collection: KnowledgeCollection | null;
  onSaved: () => void;
}) {
  const isEdit = collection !== null;
  const [name, setName] = React.useState("");
  const [description, setDescription] = React.useState("");
  const [busy, setBusy] = React.useState(false);

  React.useEffect(() => {
    if (!open) return;
    setName(collection?.name ?? "");
    setDescription(collection?.description ?? "");
  }, [open, collection]);

  async function handleSubmit() {
    if (!name.trim()) {
      toast.error("集合名称不能为空");
      return;
    }
    setBusy(true);
    try {
      const body = { name: name.trim(), description: description.trim() || null };
      if (isEdit) {
        await updateCollection(collection.id, body);
        toast.success("集合已更新");
      } else {
        await createCollection(body);
        toast.success("集合已创建");
      }
      onOpenChange(false);
      onSaved();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "保存失败");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{isEdit ? "编辑集合" : "新建集合"}</DialogTitle>
        </DialogHeader>
        <div className="space-y-4 py-2">
          <div className="space-y-1.5">
            <Label htmlFor="collection-name">名称</Label>
            <Input
              id="collection-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="例如：美妆库"
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="collection-desc">描述</Label>
            <Textarea
              id="collection-desc"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="可选"
            />
          </div>
        </div>
        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={busy}
          >
            取消
          </Button>
          <Button onClick={handleSubmit} disabled={busy}>
            {busy ? <Loader2 className="animate-spin" /> : null}
            {isEdit ? "保存" : "创建"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
