import type {
  Analysis,
  AnalysisSummary,
  AssetListResponse,
  CopyAsset,
  KnowledgeCollection,
  KnowledgeCollectionCreate,
  ListResponse,
  RawCopySummary,
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

// ---- Knowledge base ----

const knowledgeBase = `${apiBase}/api/knowledge`;

async function writeJson<T>(
  url: string,
  method: "POST" | "PATCH",
  body: unknown,
  fallback: string
): Promise<T> {
  const response = await fetch(url, {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });
  const payload = await parseJson(response);
  if (!response.ok) {
    throw new Error((payload?.detail as string) ?? fallback);
  }
  return payload as T;
}

async function deleteResource(url: string, fallback: string): Promise<void> {
  const response = await fetch(url, { method: "DELETE" });
  if (!response.ok) {
    const payload = await parseJson(response);
    throw new Error((payload?.detail as string) ?? fallback);
  }
}

// collections

export async function fetchCollections(): Promise<KnowledgeCollection[]> {
  const response = await fetch(
    `${knowledgeBase}/collections?page=1&page_size=100`
  );
  if (!response.ok) throw new Error("加载集合失败");
  const payload = (await response.json()) as ListResponse<KnowledgeCollection>;
  return payload.items;
}

export function createCollection(
  body: KnowledgeCollectionCreate
): Promise<KnowledgeCollection> {
  return writeJson(`${knowledgeBase}/collections`, "POST", body, "创建集合失败");
}

export function updateCollection(
  id: string,
  body: Partial<KnowledgeCollectionCreate>
): Promise<KnowledgeCollection> {
  return writeJson(
    `${knowledgeBase}/collections/${id}`,
    "PATCH",
    body,
    "更新集合失败"
  );
}

export function deleteCollection(id: string): Promise<void> {
  return deleteResource(`${knowledgeBase}/collections/${id}`, "删除集合失败");
}

// raw-copies

export async function fetchRawCopies(
  collectionId?: string
): Promise<RawCopySummary[]> {
  const params = new URLSearchParams({ page: "1", page_size: "100" });
  if (collectionId) params.set("collection_id", collectionId);
  const response = await fetch(`${knowledgeBase}/raw-copies?${params}`);
  if (!response.ok) throw new Error("加载原始文案失败");
  const payload = (await response.json()) as ListResponse<RawCopySummary>;
  return payload.items;
}

export function updateRawCopy(
  id: string,
  body: { collection_ids: string[] }
): Promise<RawCopySummary> {
  return writeJson(
    `${knowledgeBase}/raw-copies/${id}`,
    "PATCH",
    body,
    "更新原始文案失败"
  );
}

export function deleteRawCopy(id: string): Promise<void> {
  return deleteResource(`${knowledgeBase}/raw-copies/${id}`, "删除原始文案失败");
}

// analyses

export async function fetchAnalyses(): Promise<AnalysisSummary[]> {
  const response = await fetch(
    `${knowledgeBase}/analyses?page=1&page_size=100`
  );
  if (!response.ok) throw new Error("加载拆解失败");
  const payload = (await response.json()) as ListResponse<AnalysisSummary>;
  return payload.items;
}

export function deleteAnalysis(id: string): Promise<void> {
  return deleteResource(`${knowledgeBase}/analyses/${id}`, "删除拆解失败");
}
