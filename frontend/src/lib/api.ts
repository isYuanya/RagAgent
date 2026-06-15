import type {
  Analysis,
  AssetListResponse,
  CopyAsset,
  TaskResponse
} from "./types";

export const apiBase =
  import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8002";

async function parseJson(response: Response) {
  try {
    return await response.json();
  } catch {
    return null;
  }
}

export async function fetchAssets(): Promise<CopyAsset[]> {
  const response = await fetch(
    `${apiBase}/api/copy/assets?page=1&page_size=100`
  );
  if (!response.ok) throw new Error("加载资产失败");
  const payload = (await response.json()) as AssetListResponse;
  return payload.items;
}

export async function importCsv(csvText: string): Promise<TaskResponse> {
  const response = await fetch(`${apiBase}/api/copy/import`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ csv_text: csvText })
  });
  const payload = await parseJson(response);
  if (!response.ok) {
    throw new Error((payload?.detail as string) ?? "导入失败");
  }
  return payload as TaskResponse;
}

export async function fetchTask(taskId: string): Promise<TaskResponse | null> {
  const response = await fetch(`${apiBase}/api/tasks/${taskId}`);
  if (!response.ok) return null;
  return (await response.json()) as TaskResponse;
}

export async function saveReview(
  assetId: string,
  status: string,
  reviewedAnalysis: Analysis
): Promise<CopyAsset> {
  const response = await fetch(`${apiBase}/api/copy/assets/${assetId}/review`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status, reviewed_analysis: reviewedAnalysis })
  });
  const payload = await parseJson(response);
  if (!response.ok) {
    throw new Error((payload?.detail as string) ?? "保存失败");
  }
  return payload as CopyAsset;
}
