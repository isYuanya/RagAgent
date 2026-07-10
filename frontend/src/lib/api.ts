import type {
  Analysis,
  AnalysisSummary,
  AssetListResponse,
  CopyAsset,
  KnowledgeCollection,
  KnowledgeCollectionCreate,
  FragmentExtractionBatchResponse,
  FragmentExtractionResult,
  KnowledgeFragment,
  KnowledgeFragmentCreate,
  KnowledgeTemplate,
  KnowledgeTemplateCreate,
  FragmentFilters,
  DraftCreate,
  DraftDetail,
  DraftApprovalResponse,
  DraftItemCreate,
  DraftItemReorder,
  DraftItemUpdate,
  DraftListResponse,
  DraftStatus,
  DraftSummary,
  DraftUpdate,
  DraftVideoExportListResponse,
  DraftVideoExportRecord,
  DraftVersionDetail,
  DraftVersionSummary,
  AcceptRecommendationRequest,
  AcceptRecommendationResponse,
  AcceptCompositionRequest,
  AcceptCompositionResponse,
  AcceptDiagnosticRewriteRequest,
  AcceptDiagnosticRewriteResponse,
  AutoCompositionRequest,
  CopyDiagnosisRequest,
  ConfirmCompositionRequest,
  ConfirmMaterialsRequest,
  ConfirmRewriteRequest,
  SmartCompositionBriefPrefillResponse,
  SmartCompositionOptions,
  SmartCompositionRunCreate,
  SmartCompositionRunDetail,
  SmartCompositionRunListResponse,
  SmartCompositionRunSummary,
  NextSentenceRecommendationRequest,
  ListResponse,
  RawCopySummary,
  SystemStatusResponse,
  TaskResponse
} from "./types";

export const apiBase =
  import.meta.env.VITE_API_BASE_URL ?? "";

async function parseJson(response: Response) {
  try {
    return await response.json();
  } catch {
    return null;
  }
}

// ---- Diagnostics ----

const diagnosticsBase = `${apiBase}/api/diagnostics`;

export function createCopyDiagnosis(
  body: CopyDiagnosisRequest
): Promise<TaskResponse> {
  return writeJson(
    `${diagnosticsBase}/copy`,
    "POST",
    body,
    "创建文案诊断任务失败"
  );
}

export function acceptDiagnosticRewrite(
  body: AcceptDiagnosticRewriteRequest
): Promise<AcceptDiagnosticRewriteResponse> {
  return writeJson(
    `${diagnosticsBase}/accepted-rewrite`,
    "POST",
    body,
    "采纳诊断改写失败"
  );
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

// ---- Draft workbench ----

const draftsBase = `${apiBase}/api/drafts`;

export async function fetchDrafts(
  status: DraftStatus | "all" = "draft"
): Promise<DraftSummary[]> {
  if (status === "all") {
    const groups = await Promise.all([
      fetchDrafts("draft"),
      fetchDrafts("ready"),
      fetchDrafts("archived")
    ]);
    return groups.flat();
  }

  const params = new URLSearchParams({ page: "1", page_size: "100" });
  params.set("status", status);
  const response = await fetch(`${draftsBase}?${params}`);
  if (!response.ok) throw new Error("加载草稿失败");
  const payload = (await response.json()) as DraftListResponse;
  return payload.items;
}

export function createDraft(body: DraftCreate): Promise<DraftDetail> {
  return writeJson(`${draftsBase}`, "POST", body, "创建草稿失败");
}

export async function fetchDraft(id: string): Promise<DraftDetail> {
  const response = await fetch(`${draftsBase}/${id}`);
  if (!response.ok) throw new Error("加载草稿详情失败");
  return (await response.json()) as DraftDetail;
}

export function updateDraft(
  id: string,
  body: DraftUpdate
): Promise<DraftDetail> {
  return writeJson(`${draftsBase}/${id}`, "PATCH", body, "保存草稿失败");
}

export function archiveDraft(id: string): Promise<void> {
  return deleteResource(`${draftsBase}/${id}`, "归档草稿失败");
}

export function approveDraft(id: string): Promise<DraftApprovalResponse> {
  return writeJson(`${draftsBase}/${id}/approve`, "POST", {}, "审批通过失败");
}

export function createDraftVideoExport(id: string): Promise<TaskResponse> {
  return writeJson(
    `${draftsBase}/${id}/video-exports`,
    "POST",
    {},
    "创建视频 JSON 任务失败"
  );
}

export async function fetchDraftVideoExports(
  id: string
): Promise<DraftVideoExportRecord[]> {
  const response = await fetch(`${draftsBase}/${id}/video-exports?page=1&page_size=20`);
  if (!response.ok) throw new Error("加载视频 JSON 历史失败");
  const payload = (await response.json()) as DraftVideoExportListResponse;
  return payload.items;
}

export function addDraftItem(
  draftId: string,
  body: DraftItemCreate
): Promise<DraftDetail> {
  return writeJson(`${draftsBase}/${draftId}/items`, "POST", body, "添加片段失败");
}

export function updateDraftItem(
  draftId: string,
  itemId: string,
  body: DraftItemUpdate
): Promise<DraftDetail> {
  return writeJson(
    `${draftsBase}/${draftId}/items/${itemId}`,
    "PATCH",
    body,
    "保存草稿段落失败"
  );
}

export function deleteDraftItem(draftId: string, itemId: string): Promise<void> {
  return deleteResource(
    `${draftsBase}/${draftId}/items/${itemId}`,
    "删除草稿段落失败"
  );
}

export function reorderDraftItems(
  draftId: string,
  items: DraftItemReorder[]
): Promise<DraftDetail> {
  return writeJson(
    `${draftsBase}/${draftId}/items/reorder`,
    "PATCH",
    { items },
    "调整草稿顺序失败"
  );
}

export function createDraftVersion(
  draftId: string,
  label?: string
): Promise<DraftVersionDetail> {
  return writeJson(
    `${draftsBase}/${draftId}/versions`,
    "POST",
    { label: label?.trim() || null, metadata: {} },
    "保存版本失败"
  );
}

export async function fetchDraftVersions(
  draftId: string
): Promise<DraftVersionSummary[]> {
  const response = await fetch(`${draftsBase}/${draftId}/versions`);
  if (!response.ok) throw new Error("加载版本失败");
  return (await response.json()) as DraftVersionSummary[];
}

export async function fetchDraftVersion(
  draftId: string,
  versionId: string
): Promise<DraftVersionDetail> {
  const response = await fetch(`${draftsBase}/${draftId}/versions/${versionId}`);
  if (!response.ok) throw new Error("加载版本详情失败");
  return (await response.json()) as DraftVersionDetail;
}

// ---- Recommendations ----

const recommendationsBase = `${apiBase}/api/recommendations`;

export function createNextSentenceRecommendation(
  body: NextSentenceRecommendationRequest
): Promise<TaskResponse> {
  return writeJson(
    `${recommendationsBase}/next-sentence`,
    "POST",
    body,
    "创建下一句推荐任务失败"
  );
}

export function acceptRecommendation(
  body: AcceptRecommendationRequest
): Promise<AcceptRecommendationResponse> {
  return writeJson(
    `${recommendationsBase}/accepted`,
    "POST",
    body,
    "采纳推荐失败"
  );
}

// ---- Auto compositions ----

const compositionsBase = `${apiBase}/api/compositions`;
const assistantBase = `${apiBase}/api/assistant`;

export async function fetchSmartCompositionOptions(): Promise<SmartCompositionOptions> {
  const response = await fetch(`${assistantBase}/options`);
  if (!response.ok) throw new Error("加载智能组稿选项失败");
  return (await response.json()) as SmartCompositionOptions;
}

export function prefillSmartCompositionBrief(
  text: string
): Promise<SmartCompositionBriefPrefillResponse> {
  return writeJson(
    `${assistantBase}/brief-prefill`,
    "POST",
    { text },
    "解析组稿需求失败"
  );
}

export function createSmartCompositionRun(
  body: SmartCompositionRunCreate
): Promise<SmartCompositionRunDetail> {
  return writeJson(`${assistantBase}/runs`, "POST", body, "启动智能组稿失败");
}

export async function fetchSmartCompositionRuns(): Promise<SmartCompositionRunSummary[]> {
  const response = await fetch(`${assistantBase}/runs?page=1&page_size=30`);
  if (!response.ok) throw new Error("加载智能组稿历史失败");
  const payload = (await response.json()) as SmartCompositionRunListResponse;
  return payload.items;
}

export async function fetchSmartCompositionRun(
  id: string
): Promise<SmartCompositionRunDetail> {
  const response = await fetch(`${assistantBase}/runs/${id}`);
  if (!response.ok) throw new Error("加载智能组稿详情失败");
  return (await response.json()) as SmartCompositionRunDetail;
}

export function confirmSmartCompositionMaterials(
  runId: string,
  body: ConfirmMaterialsRequest
): Promise<SmartCompositionRunDetail> {
  return writeJson(
    `${assistantBase}/runs/${runId}/confirm-materials`,
    "POST",
    body,
    "确认素材失败"
  );
}

export function confirmSmartCompositionCandidate(
  runId: string,
  body: ConfirmCompositionRequest
): Promise<SmartCompositionRunDetail> {
  return writeJson(
    `${assistantBase}/runs/${runId}/confirm-composition`,
    "POST",
    body,
    "确认组稿失败"
  );
}

export function confirmSmartCompositionRewrite(
  runId: string,
  body: ConfirmRewriteRequest
): Promise<SmartCompositionRunDetail> {
  return writeJson(
    `${assistantBase}/runs/${runId}/confirm-rewrite`,
    "POST",
    body,
    "确认改写失败"
  );
}

export function createAutoComposition(
  body: AutoCompositionRequest
): Promise<TaskResponse> {
  return writeJson(
    `${compositionsBase}/auto-draft`,
    "POST",
    body,
    "创建自动组稿任务失败"
  );
}

export function acceptComposition(
  body: AcceptCompositionRequest
): Promise<AcceptCompositionResponse> {
  return writeJson(
    `${compositionsBase}/accepted`,
    "POST",
    body,
    "采纳自动组稿失败"
  );
}
