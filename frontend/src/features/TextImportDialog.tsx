import * as React from "react";
import { FileText, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

export function TextImportDialog({
  busy,
  disabled,
  onSubmit
}: {
  busy: boolean;
  disabled: boolean;
  onSubmit: (text: string) => Promise<void>;
}) {
  const [open, setOpen] = React.useState(false);
  const [text, setText] = React.useState("");

  async function handleSubmit() {
    const value = text.trim();
    if (!value) {
      toast.error("请输入要导入的文案");
      return;
    }
    await onSubmit(value);
    setText("");
    setOpen(false);
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <Button
        type="button"
        variant="outline"
        onClick={() => setOpen(true)}
        disabled={disabled}
      >
        {busy ? <Loader2 className="animate-spin" /> : <FileText />}
        粘贴文本
      </Button>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>导入单条文案</DialogTitle>
        </DialogHeader>
        <div className="space-y-2 py-2">
          <Label htmlFor="plain-copy-text">原始文案</Label>
          <Textarea
            id="plain-copy-text"
            value={text}
            onChange={(event) => setText(event.target.value)}
            placeholder="粘贴一段要拆解和沉淀的原始文案"
            className="min-h-[220px]"
            disabled={busy}
          />
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)} disabled={busy}>
            取消
          </Button>
          <Button onClick={handleSubmit} disabled={busy}>
            {busy ? <Loader2 className="animate-spin" /> : null}
            开始导入
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
