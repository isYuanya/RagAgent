import { FileUp, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

export function CsvUpload({
  busy,
  disabled,
  onFile
}: {
  busy: boolean;
  disabled: boolean;
  onFile: (file: File) => void;
}) {
  return (
    <label
      className={cn(
        "inline-flex h-9 cursor-pointer items-center justify-center gap-2 whitespace-nowrap rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground shadow-sm transition-colors hover:bg-primary/90",
        disabled && "pointer-events-none opacity-50"
      )}
    >
      {busy ? (
        <Loader2 className="size-4 animate-spin" />
      ) : (
        <FileUp className="size-4" />
      )}
      <span>{busy ? "导入中" : "上传 CSV"}</span>
      <input
        type="file"
        accept=".csv,text/csv"
        className="hidden"
        disabled={disabled}
        onChange={(event) => {
          const file = event.target.files?.[0];
          event.target.value = "";
          if (file) onFile(file);
        }}
      />
    </label>
  );
}
