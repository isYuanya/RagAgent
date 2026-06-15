import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function splitLines(value: string): string[] {
  return value
    .split(/\r?\n/)
    .map((item) => item.trim())
    .filter(Boolean);
}

export function formatMetrics(metrics: Record<string, number>): string {
  const parts = Object.entries(metrics).map(([key, value]) => `${key} ${value}`);
  return parts.length > 0 ? parts.join(" / ") : "无指标";
}

export function formatFollowers(value?: number | null): string {
  if (value === null || value === undefined) return "粉丝数未知";
  return `粉丝 ${value.toLocaleString("zh-CN")}`;
}

const PHASE_LABELS: Record<string, string> = {
  queued: "等待导入",
  parsing_csv: "解析 CSV",
  calling_llm: "调用 LLM",
  saving_asset: "保存资产",
  finished: "导入完成",
  failed: "导入失败"
};

export function phaseLabel(phase: string): string {
  return PHASE_LABELS[phase] ?? phase;
}
