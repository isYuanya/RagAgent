import type {
  Analysis,
  AnalysisSummary,
  AssetListResponse,
  CopyAsset,
  KnowledgeBlock,
  KnowledgeBlockCreate,
  KnowledgeCase,
  KnowledgeCaseCreate,
  KnowledgeCollection,
  KnowledgeCollectionCreate,
  FragmentExtractionBatchResponse,
  FragmentExtractionResult,
  KnowledgeFragment,
  KnowledgeFragmentCreate,
  KnowledgeTag,
  KnowledgeTagCreate,
  KnowledgeTemplate,
  KnowledgeTemplateCreate,
  FragmentFilters,
  ListResponse,
  RawCopySummary,
  SystemStatusResponse,
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

export async function importText(text: string): Promise<TaskResponse> {
  const response = await fetch(`${apiBase}/api/copy/import`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text })
  });
  const payload = await parseJson(response);
  if (!response.ok) {
    throw new Error((payload?.detail as string) ?? "导入文本失败");
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

export function deleteAsset(assetId: string): Promise<void> {
  return deleteResource(`${apiBase}/api/copy/assets/${assetId}`, "删除待审文案失败");
}

export async function fetchSystemStatus(): Promise<SystemStatusResponse> {
  const response = await fetch(`${apiBase}/api/system/status`);
  if (!response.ok) throw new Error("加载服务状态失败");
  return (await response.json()) as SystemStatusResponse;
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
// templates

export async function fetchTemplates(): Promise<KnowledgeTemplate[]> {
  const response = await fetch(`${knowledgeBase}/templates?page=1&page_size=100`);
  if (!response.ok) throw new Error("加载模板库失败");
  const payload = (await response.json()) as ListResponse<KnowledgeTemplate>;
  return payload.items;
}

export function createTemplate(
  body: KnowledgeTemplateCreate
): Promise<KnowledgeTemplate> {
  return writeJson(`${knowledgeBase}/templates`, "POST", body, "创建模板失败");
}

export function updateTemplate(
  id: string,
  body: Partial<KnowledgeTemplateCreate>
): Promise<KnowledgeTemplate> {
  return writeJson(`${knowledgeBase}/templates/${id}`, "PATCH", body, "更新模板失败");
}

export function deleteTemplate(id: string): Promise<void> {
  return deleteResource(`${knowledgeBase}/templates/${id}`, "删除模板失败");
}

// tags

export async function fetchTags(): Promise<KnowledgeTag[]> {
  const response = await fetch(`${knowledgeBase}/tags?page=1&page_size=100`);
  if (!response.ok) throw new Error("加载标签库失败");
  const payload = (await response.json()) as ListResponse<KnowledgeTag>;
  return payload.items;
}

export function createTag(body: KnowledgeTagCreate): Promise<KnowledgeTag> {
  return writeJson(`${knowledgeBase}/tags`, "POST", body, "创建标签失败");
}

export function updateTag(
  id: string,
  body: Partial<KnowledgeTagCreate>
): Promise<KnowledgeTag> {
  return writeJson(`${knowledgeBase}/tags/${id}`, "PATCH", body, "更新标签失败");
}

export function deleteTag(id: string): Promise<void> {
  return deleteResource(`${knowledgeBase}/tags/${id}`, "删除标签失败");
}

// cases

export async function fetchCases(): Promise<KnowledgeCase[]> {
  const response = await fetch(`${knowledgeBase}/cases?page=1&page_size=100`);
  if (!response.ok) throw new Error("加载案例库失败");
  const payload = (await response.json()) as ListResponse<KnowledgeCase>;
  return payload.items;
}

export function createCase(body: KnowledgeCaseCreate): Promise<KnowledgeCase> {
  return writeJson(`${knowledgeBase}/cases`, "POST", body, "创建案例失败");
}

export function updateCase(
  id: string,
  body: Partial<KnowledgeCaseCreate>
): Promise<KnowledgeCase> {
  return writeJson(`${knowledgeBase}/cases/${id}`, "PATCH", body, "更新案例失败");
}

export function deleteCase(id: string): Promise<void> {
  return deleteResource(`${knowledgeBase}/cases/${id}`, "删除案例失败");
}

// blocks

export async function fetchBlocks(): Promise<KnowledgeBlock[]> {
  const response = await fetch(`${knowledgeBase}/blocks?page=1&page_size=100`);
  if (!response.ok) throw new Error("加载禁用库失败");
  const payload = (await response.json()) as ListResponse<KnowledgeBlock>;
  return payload.items;
}

export function createBlock(
  body: KnowledgeBlockCreate
): Promise<KnowledgeBlock> {
  return writeJson(`${knowledgeBase}/blocks`, "POST", body, "创建禁用项失败");
}

export function updateBlock(
  id: string,
  body: Partial<KnowledgeBlockCreate>
): Promise<KnowledgeBlock> {
  return writeJson(`${knowledgeBase}/blocks/${id}`, "PATCH", body, "更新禁用项失败");
}

export function deleteBlock(id: string): Promise<void> {
  return deleteResource(`${knowledgeBase}/blocks/${id}`, "删除禁用项失败");
}
// fragments

export async function fetchFragments(
  filters: FragmentFilters = {}
): Promise<KnowledgeFragment[]> {
  const params = new URLSearchParams({ page: "1", page_size: "100" });
  for (const [key, value] of Object.entries(filters)) {
    if (value) params.set(key, value);
  }
  const response = await fetch(`${knowledgeBase}/fragments?${params}`);
  if (!response.ok) throw new Error("加载片段库失败");
  const payload = (await response.json()) as ListResponse<KnowledgeFragment>;
  return payload.items;
}

export function createFragment(
  body: KnowledgeFragmentCreate
): Promise<KnowledgeFragment> {
  return writeJson(`${knowledgeBase}/fragments`, "POST", body, "创建片段失败");
}

export function extractFragmentsForRawCopy(
  sourceCopyId: string
): Promise<FragmentExtractionResult> {
  return writeJson(
    `${knowledgeBase}/fragments/extract/${sourceCopyId}`,
    "POST",
    {},
    "生成片段失败"
  );
}

export function extractApprovedFragments(
  limit = 50
): Promise<FragmentExtractionBatchResponse> {
  return writeJson(
    `${knowledgeBase}/fragments/extract-approved?limit=${limit}`,
    "POST",
    {},
    "批量生成片段失败"
  );
}

export function updateFragment(
  id: string,
  body: Partial<KnowledgeFragmentCreate>
): Promise<KnowledgeFragment> {
  return writeJson(`${knowledgeBase}/fragments/${id}`, "PATCH", body, "更新片段失败");
}

export function deleteFragment(id: string): Promise<void> {
  return deleteResource(`${knowledgeBase}/fragments/${id}`, "删除片段失败");
}
