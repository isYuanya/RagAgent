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
  KnowledgeStatsResponse,
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
  BulkOperationResponse,
  FragmentBulkDeleteRequest,
  RawCopyBulkDeleteRequest,
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
    "鍒涘缓鏂囨璇婃柇浠诲姟澶辫触"
  );
}

export function acceptDiagnosticRewrite(
  body: AcceptDiagnosticRewriteRequest
): Promise<AcceptDiagnosticRewriteResponse> {
  return writeJson(
    `${diagnosticsBase}/accepted-rewrite`,
    "POST",
    body,
    "閲囩撼璇婃柇鏀瑰啓澶辫触"
  );
}

export async function fetchAssets(): Promise<CopyAsset[]> {
  const response = await fetch(
    `${apiBase}/api/copy/assets?page=1&page_size=100`
  );
  if (!response.ok) throw new Error("鍔犺浇璧勪骇澶辫触");
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
    throw new Error((payload?.detail as string) ?? "瀵煎叆澶辫触");
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
    throw new Error((payload?.detail as string) ?? "瀵煎叆鏂囨湰澶辫触");
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
    throw new Error((payload?.detail as string) ?? "淇濆瓨澶辫触");
  }
  return payload as CopyAsset;
}

export function deleteAsset(assetId: string): Promise<void> {
  return deleteResource(`${apiBase}/api/copy/assets/${assetId}`, "鍒犻櫎寰呭鏂囨澶辫触");
}

export async function fetchSystemStatus(): Promise<SystemStatusResponse> {
  const response = await fetch(`${apiBase}/api/system/status`);
  if (!response.ok) throw new Error("加载服务状态失败");
  return (await response.json()) as SystemStatusResponse;
}

// ---- Knowledge base ----

const knowledgeBase = `${apiBase}/api/knowledge`;
const DEFAULT_PAGE_SIZE = 20;

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

export async function fetchKnowledgeStats(): Promise<KnowledgeStatsResponse> {
  const response = await fetch(`${knowledgeBase}/stats`);
  if (!response.ok) throw new Error("加载知识库统计失败");
  return (await response.json()) as KnowledgeStatsResponse;
}

export async function fetchCollectionsPage(
  page = 1,
  pageSize = DEFAULT_PAGE_SIZE
): Promise<ListResponse<KnowledgeCollection>> {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize)
  });
  const response = await fetch(`${knowledgeBase}/collections?${params}`);
  if (!response.ok) throw new Error("加载集合失败");
  return (await response.json()) as ListResponse<KnowledgeCollection>;
}

export async function fetchCollections(): Promise<KnowledgeCollection[]> {
  const response = await fetch(
    `${knowledgeBase}/collections?page=1&page_size=100`
  );
  if (!response.ok) throw new Error("鍔犺浇闆嗗悎澶辫触");
  const payload = (await response.json()) as ListResponse<KnowledgeCollection>;
  return payload.items;
}

export function createCollection(
  body: KnowledgeCollectionCreate
): Promise<KnowledgeCollection> {
  return writeJson(`${knowledgeBase}/collections`, "POST", body, "鍒涘缓闆嗗悎澶辫触");
}

export function updateCollection(
  id: string,
  body: Partial<KnowledgeCollectionCreate>
): Promise<KnowledgeCollection> {
  return writeJson(
    `${knowledgeBase}/collections/${id}`,
    "PATCH",
    body,
    "鏇存柊闆嗗悎澶辫触"
  );
}

export function deleteCollection(id: string): Promise<void> {
  return deleteResource(`${knowledgeBase}/collections/${id}`, "鍒犻櫎闆嗗悎澶辫触");
}

// raw-copies

export async function fetchRawCopiesPage(
  collectionId?: string,
  page = 1,
  pageSize = DEFAULT_PAGE_SIZE
): Promise<ListResponse<RawCopySummary>> {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize)
  });
  if (collectionId) params.set("collection_id", collectionId);
  const response = await fetch(`${knowledgeBase}/raw-copies?${params}`);
  if (!response.ok) throw new Error("閸旂姾娴囬崢鐔奉潗閺傚洦顢嶆径杈Е");
  return (await response.json()) as ListResponse<RawCopySummary>;
}

export async function fetchRawCopies(
  collectionId?: string
): Promise<RawCopySummary[]> {
  const params = new URLSearchParams({ page: "1", page_size: "100" });
  if (collectionId) params.set("collection_id", collectionId);
  const response = await fetch(`${knowledgeBase}/raw-copies?${params}`);
  if (!response.ok) throw new Error("鍔犺浇鍘熷鏂囨澶辫触");
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
    "鏇存柊鍘熷鏂囨澶辫触"
  );
}

export function deleteRawCopy(id: string): Promise<void> {
  return deleteResource(`${knowledgeBase}/raw-copies/${id}`, "鍒犻櫎鍘熷鏂囨澶辫触");
}

// analyses

export function previewBulkDeleteRawCopies(
  body: RawCopyBulkDeleteRequest
): Promise<BulkOperationResponse> {
  return writeJson(
    `${knowledgeBase}/raw-copies/bulk-delete/preview`,
    "POST",
    body,
    "璁＄畻鍒犻櫎鏁伴噺澶辫触"
  );
}

export function bulkDeleteRawCopies(
  body: RawCopyBulkDeleteRequest
): Promise<BulkOperationResponse> {
  return writeJson(
    `${knowledgeBase}/raw-copies/bulk-delete`,
    "POST",
    body,
    "鎵归噺鍒犻櫎鍘熷鏂囨澶辫触"
  );
}

export async function fetchAnalysesPage(
  page = 1,
  pageSize = DEFAULT_PAGE_SIZE
): Promise<ListResponse<AnalysisSummary>> {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize)
  });
  const response = await fetch(`${knowledgeBase}/analyses?${params}`);
  if (!response.ok) throw new Error("閸旂姾娴囬幏鍡毿掓径杈Е");
  return (await response.json()) as ListResponse<AnalysisSummary>;
}

export async function fetchAnalyses(): Promise<AnalysisSummary[]> {
  const response = await fetch(
    `${knowledgeBase}/analyses?page=1&page_size=100`
  );
  if (!response.ok) throw new Error("鍔犺浇鎷嗚В澶辫触");
  const payload = (await response.json()) as ListResponse<AnalysisSummary>;
  return payload.items;
}

export function deleteAnalysis(id: string): Promise<void> {
  return deleteResource(`${knowledgeBase}/analyses/${id}`, "鍒犻櫎鎷嗚В澶辫触");
}
// templates

export async function fetchTemplatesPage(
  page = 1,
  pageSize = DEFAULT_PAGE_SIZE
): Promise<ListResponse<KnowledgeTemplate>> {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize)
  });
  const response = await fetch(`${knowledgeBase}/templates?${params}`);
  if (!response.ok) throw new Error("加载模板库失败");
  return (await response.json()) as ListResponse<KnowledgeTemplate>;
}

export async function fetchTemplates(): Promise<KnowledgeTemplate[]> {
  const response = await fetch(`${knowledgeBase}/templates?page=1&page_size=100`);
  if (!response.ok) throw new Error("加载模板库失败");
  const payload = (await response.json()) as ListResponse<KnowledgeTemplate>;
  return payload.items;
}

export function createTemplate(
  body: KnowledgeTemplateCreate
): Promise<KnowledgeTemplate> {
  return writeJson(`${knowledgeBase}/templates`, "POST", body, "鍒涘缓妯℃澘澶辫触");
}

export function updateTemplate(
  id: string,
  body: Partial<KnowledgeTemplateCreate>
): Promise<KnowledgeTemplate> {
  return writeJson(`${knowledgeBase}/templates/${id}`, "PATCH", body, "鏇存柊妯℃澘澶辫触");
}

export function deleteTemplate(id: string): Promise<void> {
  return deleteResource(`${knowledgeBase}/templates/${id}`, "鍒犻櫎妯℃澘澶辫触");
}

// fragments

export async function fetchFragmentsPage(
  filters: FragmentFilters = {},
  page = 1,
  pageSize = DEFAULT_PAGE_SIZE
): Promise<ListResponse<KnowledgeFragment>> {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize)
  });
  for (const [key, value] of Object.entries(filters)) {
    if (value) params.set(key, value);
  }
  const response = await fetch(`${knowledgeBase}/fragments?${params}`);
  if (!response.ok) throw new Error("加载片段库失败");
  return (await response.json()) as ListResponse<KnowledgeFragment>;
}

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
  return writeJson(`${knowledgeBase}/fragments`, "POST", body, "鍒涘缓鐗囨澶辫触");
}

export function extractFragmentsForRawCopy(
  sourceCopyId: string
): Promise<FragmentExtractionResult> {
  return writeJson(
    `${knowledgeBase}/fragments/extract/${sourceCopyId}`,
    "POST",
    {},
    "鐢熸垚鐗囨澶辫触"
  );
}

export function extractApprovedFragments(
  limit = 50
): Promise<FragmentExtractionBatchResponse> {
  return writeJson(
    `${knowledgeBase}/fragments/extract-approved?limit=${limit}`,
    "POST",
    {},
    "鎵归噺鐢熸垚鐗囨澶辫触"
  );
}

export function updateFragment(
  id: string,
  body: Partial<KnowledgeFragmentCreate>
): Promise<KnowledgeFragment> {
  return writeJson(`${knowledgeBase}/fragments/${id}`, "PATCH", body, "鏇存柊鐗囨澶辫触");
}

export function deleteFragment(id: string): Promise<void> {
  return deleteResource(`${knowledgeBase}/fragments/${id}`, "鍒犻櫎鐗囨澶辫触");
}

export function previewBulkDeleteFragments(
  body: FragmentBulkDeleteRequest
): Promise<BulkOperationResponse> {
  return writeJson(
    `${knowledgeBase}/fragments/bulk-delete/preview`,
    "POST",
    body,
    "计算删除片段数量失败"
  );
}

export function bulkDeleteFragments(
  body: FragmentBulkDeleteRequest
): Promise<BulkOperationResponse> {
  return writeJson(
    `${knowledgeBase}/fragments/bulk-delete`,
    "POST",
    body,
    "批量删除片段失败"
  );
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
  if (!response.ok) throw new Error("鍔犺浇鑽夌澶辫触");
  const payload = (await response.json()) as DraftListResponse;
  return payload.items;
}

export function createDraft(body: DraftCreate): Promise<DraftDetail> {
  return writeJson(`${draftsBase}`, "POST", body, "鍒涘缓鑽夌澶辫触");
}

export async function fetchDraft(id: string): Promise<DraftDetail> {
  const response = await fetch(`${draftsBase}/${id}`);
  if (!response.ok) throw new Error("鍔犺浇鑽夌璇︽儏澶辫触");
  return (await response.json()) as DraftDetail;
}

export function updateDraft(
  id: string,
  body: DraftUpdate
): Promise<DraftDetail> {
  return writeJson(`${draftsBase}/${id}`, "PATCH", body, "淇濆瓨鑽夌澶辫触");
}

export function archiveDraft(id: string): Promise<void> {
  return deleteResource(`${draftsBase}/${id}`, "褰掓。鑽夌澶辫触");
}

export function approveDraft(id: string): Promise<DraftApprovalResponse> {
  return writeJson(`${draftsBase}/${id}/approve`, "POST", {}, "瀹℃壒閫氳繃澶辫触");
}

export function createDraftVideoExport(id: string): Promise<TaskResponse> {
  return writeJson(
    `${draftsBase}/${id}/video-exports`,
    "POST",
    {},
    "鍒涘缓瑙嗛 JSON 浠诲姟澶辫触"
  );
}

export async function fetchDraftVideoExports(
  id: string
): Promise<DraftVideoExportRecord[]> {
  const response = await fetch(`${draftsBase}/${id}/video-exports?page=1&page_size=20`);
  if (!response.ok) throw new Error("鍔犺浇瑙嗛 JSON 鍘嗗彶澶辫触");
  const payload = (await response.json()) as DraftVideoExportListResponse;
  return payload.items;
}

export function addDraftItem(
  draftId: string,
  body: DraftItemCreate
): Promise<DraftDetail> {
  return writeJson(`${draftsBase}/${draftId}/items`, "POST", body, "娣诲姞鐗囨澶辫触");
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
    "淇濆瓨鑽夌娈佃惤澶辫触"
  );
}

export function deleteDraftItem(draftId: string, itemId: string): Promise<void> {
  return deleteResource(
    `${draftsBase}/${draftId}/items/${itemId}`,
    "鍒犻櫎鑽夌娈佃惤澶辫触"
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
    "璋冩暣鑽夌椤哄簭澶辫触"
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
    "淇濆瓨鐗堟湰澶辫触"
  );
}

export async function fetchDraftVersions(
  draftId: string
): Promise<DraftVersionSummary[]> {
  const response = await fetch(`${draftsBase}/${draftId}/versions`);
  if (!response.ok) throw new Error("鍔犺浇鐗堟湰澶辫触");
  return (await response.json()) as DraftVersionSummary[];
}

export async function fetchDraftVersion(
  draftId: string,
  versionId: string
): Promise<DraftVersionDetail> {
  const response = await fetch(`${draftsBase}/${draftId}/versions/${versionId}`);
  if (!response.ok) throw new Error("鍔犺浇鐗堟湰璇︽儏澶辫触");
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
    "閲囩撼鎺ㄨ崘澶辫触"
  );
}

// ---- Auto compositions ----

const compositionsBase = `${apiBase}/api/compositions`;
const assistantBase = `${apiBase}/api/assistant`;

export async function fetchSmartCompositionOptions(): Promise<SmartCompositionOptions> {
  const response = await fetch(`${assistantBase}/options`);
  if (!response.ok) throw new Error("鍔犺浇鏅鸿兘缁勭閫夐」澶辫触");
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
  return writeJson(`${assistantBase}/runs`, "POST", body, "鍚姩鏅鸿兘缁勭澶辫触");
}

export async function fetchSmartCompositionRuns(): Promise<SmartCompositionRunSummary[]> {
  const response = await fetch(`${assistantBase}/runs?page=1&page_size=30`);
  if (!response.ok) throw new Error("鍔犺浇鏅鸿兘缁勭鍘嗗彶澶辫触");
  const payload = (await response.json()) as SmartCompositionRunListResponse;
  return payload.items;
}

export async function fetchSmartCompositionRun(
  id: string
): Promise<SmartCompositionRunDetail> {
  const response = await fetch(`${assistantBase}/runs/${id}`);
  if (!response.ok) throw new Error("鍔犺浇鏅鸿兘缁勭璇︽儏澶辫触");
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
    "纭绱犳潗澶辫触"
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
    "纭缁勭澶辫触"
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
    "纭鏀瑰啓澶辫触"
  );
}

export function createAutoComposition(
  body: AutoCompositionRequest
): Promise<TaskResponse> {
  return writeJson(
    `${compositionsBase}/auto-draft`,
    "POST",
    body,
    "鍒涘缓鑷姩缁勭浠诲姟澶辫触"
  );
}

export function acceptComposition(
  body: AcceptCompositionRequest
): Promise<AcceptCompositionResponse> {
  return writeJson(
    `${compositionsBase}/accepted`,
    "POST",
    body,
    "閲囩撼鑷姩缁勭澶辫触"
  );
}
