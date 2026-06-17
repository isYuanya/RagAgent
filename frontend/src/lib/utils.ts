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

const ROLE_LABELS: Record<string, string> = {
  hook: "开头钩子",
  pain_point: "痛点",
  solution: "解决方案",
  proof: "证明背书",
  transition: "过渡句",
  cta: "行动引导",
  explanation: "解释说明",
  diagnostic_rewrite: "诊断改写"
};

const POSITION_LABELS: Record<string, string> = {
  opening: "开头",
  middle: "中段",
  body: "正文中段",
  ending: "结尾",
  full_copy: "全文"
};

const QUOTE_MODE_LABELS: Record<string, string> = {
  direct: "直接引用",
  adapted: "改写借鉴",
  original: "原创生成"
};

export function formatRoleLabel(value?: string | null): string {
  if (!value) return "未标角色";
  return ROLE_LABELS[value] ?? value;
}

export function formatPositionLabel(value?: string | null): string {
  if (!value) return "未标位置";
  return POSITION_LABELS[value] ?? value;
}

export function formatQuoteModeLabel(value?: string | null): string {
  if (!value) return "未标引用方式";
  return QUOTE_MODE_LABELS[value] ?? value;
}
