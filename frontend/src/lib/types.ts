export type RiskWarning = {
  level: string;
  message: string;
  suggestion?: string | null;
};

export type Analysis = {
  topic: string;
  target_user: string;
  core_pain: string;
  emotion_buttons: string[];
  hook: string;
  structure: string[];
  expression_skills: string[];
  reusable_template: string;
  suitable_scenarios: string[];
  risk_warnings: RiskWarning[];
  confidence: number;
};

export type CopyAsset = {
  id: string;
  source_text: string;
  source_url?: string | null;
  author_name?: string | null;
  author_url?: string | null;
  author_follower_count?: number | null;
  platform?: string | null;
  industry?: string | null;
  audience?: string | null;
  purpose?: string | null;
  style?: string | null;
  structure_type?: string | null;
  content_type?: string | null;
  metrics: Record<string, number>;
  status: string;
  auto_analysis?: Analysis | null;
  reviewed_analysis?: Analysis | null;
  storage_backend?: string;
  collection_ids?: string[];
};

export type AssetListResponse = {
  items: CopyAsset[];
  total: number;
  page: number;
  page_size: number;
};

export type TaskProgress = {
  phase: string;
  model?: string | null;
  current_row: number;
  total_rows: number;
  processed_count: number;
  success_count: number;
  failed_count: number;
  percent: number;
  current_message?: string | null;
  errors: Array<{
    row_number?: number;
    message?: string;
    current_video?: Record<string, unknown>;
  }>;
};

export type TaskResponse = {
  task_id: string;
  status: string;
  result?: Record<string, unknown> | null;
  error?: string | null;
  progress?: TaskProgress | null;
};

export type ReviewStatus = "pending_review" | "approved" | "rejected";

export type ServiceHealthStatus = "ok" | "degraded" | "down";

export type DependencyStatus = {
  name: string;
  required: boolean;
  status: ServiceHealthStatus;
  latency_ms?: number | null;
  endpoint?: string | null;
  message: string;
};

export type SystemStatusResponse = {
  status: ServiceHealthStatus;
  services: DependencyStatus[];
};

// ---- Knowledge base ----

export type ListResponse<T> = {
  items: T[];
  total: number;
  page: number;
  page_size: number;
};

export type KnowledgeStatsResponse = {
  collections: number;
  raw_copies: number;
  analyses: number;
  templates: number;
  fragments: number;
};

// ---- Keyword rankings ----

export type KeywordIndustryStatus = "active" | "inactive";

export type KeywordIndustryCreate = {
  name: string;
  description?: string | null;
  status?: KeywordIndustryStatus;
};

export type KeywordIndustry = {
  id: string;
  name: string;
  description?: string | null;
  status: KeywordIndustryStatus;
  keyword_count: number;
  video_count: number;
  last_updated_at?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
};

export type KeywordGroupCreate = {
  industry_id: string;
  keyword: string;
};

export type KeywordGroup = {
  id: string;
  industry_id: string;
  keyword: string;
  video_count: number;
  last_updated_at?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
};

export type KeywordVideo = {
  id: string;
  keyword_id: string;
  rank: number;
  source_text: string;
  source_url?: string | null;
  author_name?: string | null;
  author_url?: string | null;
  author_follower_count?: number | null;
  platform?: string | null;
  industry?: string | null;
  audience?: string | null;
  purpose?: string | null;
  style?: string | null;
  likes: number;
  comments: number;
  favorites: number;
  shares: number;
  hot_score: number;
  created_at?: string | null;
  updated_at?: string | null;
};

export type KeywordVideoImportRequest = {
  industry_id: string;
  keyword: string;
  csv_text: string;
};

export type KeywordCrawlerRequest = {
  keyword: string;
  min_likes: number;
  max_videos: number;
  industry_id?: string | null;
};

export type KeywordVideoImportResponse = {
  industry_id: string;
  keyword_id: string;
  keyword: string;
  created_count: number;
  updated_count: number;
  failed_count: number;
  video_count: number;
  errors: Array<{ row_number: number; message: string }>;
};

export type KnowledgeCollection = {
  id: string;
  name: string;
  description?: string | null;
  metadata: Record<string, unknown>;
};

export type KnowledgeCollectionCreate = {
  name: string;
  description?: string | null;
  metadata?: Record<string, unknown>;
};

export type SourceReference = {
  source_type: "raw_copy" | "analysis";
  source_id: string;
  source_display?: string | null;
};

export type RawCopySummary = CopyAsset & {
  collection_ids: string[];
  collections: KnowledgeCollection[];
};

export type AnalysisSummary = {
  id: string;
  raw_copy_id: string;
  auto_analysis?: Analysis | null;
  reviewed_analysis?: Analysis | null;
  status: string;
};

export type KnowledgeTemplate = {
  id: string;
  title: string;
  content: string;
  structure: string[];
  suitable_scenarios: string[];
  source?: SourceReference | null;
  metadata: Record<string, unknown>;
};

export type KnowledgeTemplateCreate = Omit<KnowledgeTemplate, "id">;

export type FragmentQuality = "unknown" | "low" | "medium" | "high";
export type FragmentRiskLevel = "low" | "medium" | "high";

export type KnowledgeFragment = {
  id: string;
  source_copy_id: string;
  analysis_id?: string | null;
  sequence_order: number;
  previous_fragment?: string | null;
  next_fragment?: string | null;
  before_context?: string | null;
  after_context?: string | null;
  fragment_text: string;
  fragment_role: string;
  position: string;
  industry?: string | null;
  platform?: string | null;
  purpose?: string | null;
  audience?: string | null;
  source_quality: FragmentQuality;
  risk_level: FragmentRiskLevel;
  status: ReviewStatus;
  confidence: number;
  metadata: Record<string, unknown>;
};

export type KnowledgeFragmentCreate = Omit<KnowledgeFragment, "id">;

export type FragmentFilters = {
  source_copy_id?: string;
  fragment_role?: string;
  position?: string;
  industry?: string;
  status?: ReviewStatus;
  platform?: string;
  purpose?: string;
  audience?: string;
  risk_level?: FragmentRiskLevel;
  q?: string;
};

export type FragmentExtractionResult = {
  source_copy_id: string;
  status: "created" | "skipped" | "failed";
  fragment_count: number;
  message?: string | null;
};

export type FragmentExtractionBatchResponse = {
  items: FragmentExtractionResult[];
  processed_count: number;
  created_count: number;
  failed_count: number;
};

export type BulkOperationResponse = {
  matched_count: number;
  deleted_count: number;
  archived_count?: number;
  skipped_count: number;
  failed_count: number;
  item_ids: string[];
  errors: Array<{ id?: string; error?: string }>;
};

export type RawCopyBulkDeleteRequest = {
  confirm: boolean;
  collection_id?: string | null;
  status?: ReviewStatus | null;
  industry?: string | null;
  platform?: string | null;
  raw_copy_ids?: string[] | null;
};

export type FragmentBulkDeleteRequest = FragmentFilters & {
  confirm: boolean;
  fragment_ids?: string[] | null;
};

export type DraftStatus = "draft" | "ready" | "archived";

export type DraftItem = {
  id: string;
  draft_id: string;
  source_fragment_id?: string | null;
  source_copy_id?: string | null;
  order_index: number;
  original_fragment_text?: string | null;
  edited_text: string;
  role?: string | null;
  position?: string | null;
  metadata: Record<string, unknown>;
};

export type DraftSummary = {
  id: string;
  title: string;
  goal?: string | null;
  audience?: string | null;
  platform?: string | null;
  purpose?: string | null;
  status: DraftStatus;
  current_text: string;
  item_count: number;
  metadata: Record<string, unknown>;
};

export type DraftDetail = DraftSummary & {
  items: DraftItem[];
};

export type DraftListResponse = ListResponse<DraftSummary>;

export type DraftCreate = {
  title: string;
  goal?: string | null;
  audience?: string | null;
  platform?: string | null;
  purpose?: string | null;
  metadata?: Record<string, unknown>;
};

export type DraftUpdate = Partial<DraftCreate> & {
  status?: DraftStatus;
};

export type DraftItemCreate = {
  source_fragment_id?: string | null;
  edited_text?: string | null;
  role?: string | null;
  position?: string | null;
  order_index?: number | null;
  metadata?: Record<string, unknown>;
};

export type DraftItemUpdate = {
  edited_text?: string | null;
  role?: string | null;
  position?: string | null;
  metadata?: Record<string, unknown> | null;
};

export type DraftItemReorder = {
  item_id: string;
  order_index: number;
};

export type DraftVersionSummary = {
  id: string;
  draft_id: string;
  version_number: number;
  label?: string | null;
  current_text: string;
  item_count: number;
  metadata: Record<string, unknown>;
};

export type DraftItemSnapshot = Omit<DraftItem, "draft_id">;

export type DraftVersionDetail = DraftVersionSummary & {
  items: DraftItemSnapshot[];
};

export type DraftApprovalResponse = {
  draft: DraftDetail;
  raw_copy: CopyAsset;
  fragment_extraction: FragmentExtractionResult;
};

export type DraftVideoExportPayload = {
  title: string;
  title_break: string;
  description: string;
  script: string;
  tts_script: string;
  hashtags: string[];
};

export type DraftVideoExportRecord = {
  id: string;
  draft_id: string;
  status: string;
  result: DraftVideoExportPayload;
  model?: string | null;
  error?: string | null;
  metadata: Record<string, unknown>;
  created_at?: string | null;
  updated_at?: string | null;
};

export type DraftVideoExportListResponse = ListResponse<DraftVideoExportRecord>;

export type ReferenceFragmentSummary = {
  id: string;
  text: string;
  role?: string | null;
  position?: string | null;
  source_copy_id?: string | null;
  source_display?: string | null;
};

export type RecommendationCandidate = {
  candidate_id: string;
  text: string;
  function: string;
  reason: string;
  tone: string;
  suggested_order_index: number;
  risk_warnings: RiskWarning[];
  reference_fragment_ids: string[];
  reference_fragments: ReferenceFragmentSummary[];
};

export type NextSentenceRecommendationResult = {
  draft_id: string;
  current_text: string;
  next_function: string;
  model?: string | null;
  candidates: RecommendationCandidate[];
  reference_fragments: ReferenceFragmentSummary[];
};

export type NextSentenceRecommendationRequest = {
  draft_id: string;
  candidate_count?: number;
  cursor_item_id?: string | null;
  q?: string | null;
  metadata?: Record<string, unknown>;
};

export type AcceptRecommendationRequest = {
  draft_id: string;
  task_id: string;
  candidate_id: string;
  order_index?: number | null;
  metadata?: Record<string, unknown>;
};

export type AcceptedRecommendationItem = {
  id: string;
  draft_id: string;
  task_id: string;
  candidate_id: string;
  inserted_draft_item_id: string;
  candidate_text: string;
  function?: string | null;
  tone?: string | null;
  reason?: string | null;
  model?: string | null;
  reference_fragment_ids: string[];
  metadata: Record<string, unknown>;
};

export type AcceptRecommendationResponse = {
  accepted: AcceptedRecommendationItem;
  draft: DraftDetail;
};

export type AutoCompositionBrief = {
  product: string;
  audience: string;
  platform: string;
  purpose: string;
  style: string;
  key_selling_points: string[];
  constraints?: string | null;
  target_length?: string | null;
  metadata?: Record<string, unknown>;
};

export type SmartCompositionBrief = AutoCompositionBrief & {
  collection_ids?: string[];
  extra_notes?: string | null;
};

export type SmartCompositionMode = "auto" | "guided";
export type SmartCompositionStatus =
  | "pending"
  | "running"
  | "waiting_for_user"
  | "finished"
  | "failed";
export type SmartCompositionStepStatus =
  | "pending"
  | "running"
  | "completed"
  | "waiting_for_user"
  | "failed";

export type SmartCompositionOption = {
  value: string;
  label: string;
  description?: string | null;
};

export type SmartCompositionOptions = {
  collections: KnowledgeCollection[];
  platforms: SmartCompositionOption[];
  purposes: SmartCompositionOption[];
  audiences: SmartCompositionOption[];
  styles: SmartCompositionOption[];
};

export type SmartCompositionStep = {
  step_id: string;
  label: string;
  order: number;
  percent: number;
  status: SmartCompositionStepStatus;
  model?: string | null;
  message?: string | null;
  reason?: string | null;
  metadata: Record<string, unknown>;
};

export type SmartCompositionSelection = {
  selected_id: string;
  method: "llm_judge" | "rule_fallback" | "user";
  score_signals: Record<string, number | string>;
  judge_model?: string | null;
  reason?: string | null;
  fallback_reason?: string | null;
};

export type SmartCompositionResult = {
  composition?: AutoCompositionResult | null;
  diagnosis?: CopyDiagnosisResult | null;
  selected_candidate?: CompositionCandidate | null;
  selected_rewrite?: RewriteCandidate | null;
  composition_selection?: SmartCompositionSelection | null;
  rewrite_selection?: SmartCompositionSelection | null;
  materials: ReferenceFragmentSummary[];
  draft?: DraftDetail | null;
  initial_version?: DraftVersionDetail | null;
  final_version?: DraftVersionDetail | null;
};

export type SmartCompositionRunSummary = {
  id: string;
  mode: SmartCompositionMode;
  status: SmartCompositionStatus;
  brief: SmartCompositionBrief;
  draft_id?: string | null;
  initial_version_id?: string | null;
  final_version_id?: string | null;
  selected_candidate_id?: string | null;
  selected_rewrite_id?: string | null;
  error?: string | null;
  created_at: string;
  updated_at: string;
};

export type SmartCompositionRunDetail = SmartCompositionRunSummary & {
  timeline: SmartCompositionStep[];
  collection_ids: string[];
  material_ids: string[];
  result: SmartCompositionResult;
  metadata: Record<string, unknown>;
};

export type SmartCompositionRunCreate = {
  mode: SmartCompositionMode;
  brief: SmartCompositionBrief;
  metadata?: Record<string, unknown>;
};

export type ConfirmMaterialsRequest = {
  material_ids: string[];
};

export type ConfirmCompositionRequest = {
  candidate_id: string;
};

export type ConfirmRewriteRequest = {
  rewrite_candidate_id: string;
};

export type SmartCompositionRunListResponse =
  ListResponse<SmartCompositionRunSummary>;

export type SmartCompositionBriefPrefillResponse = {
  brief: SmartCompositionBrief;
  confidence: number;
  notes: string[];
  model?: string | null;
};

export type AutoCompositionRequest = {
  brief: AutoCompositionBrief;
};

export type CompositionItemCandidate = {
  role: "hook" | "pain_point" | "solution" | "proof" | "cta";
  position: string;
  text: string;
  quote_mode: "direct" | "adapted" | "original";
  reference_fragment_ids: string[];
  source_copy_id?: string | null;
  reason: string;
};

export type CompositionCandidate = {
  candidate_id: string;
  title: string;
  strategy: string;
  items: CompositionItemCandidate[];
  reference_fragment_ids: string[];
};

export type AutoCompositionResult = {
  brief: AutoCompositionBrief;
  model?: string | null;
  fallback_reason?: string | null;
  candidates: CompositionCandidate[];
  reference_fragments: ReferenceFragmentSummary[];
};

export type AcceptCompositionRequest = {
  task_id: string;
  candidate_id: string;
  metadata?: Record<string, unknown>;
};

export type AcceptedCompositionItem = {
  id: string;
  task_id: string;
  candidate_id: string;
  draft_id: string;
  brief: AutoCompositionBrief;
  candidate_title: string;
  model?: string | null;
  reference_fragment_ids: string[];
  metadata: Record<string, unknown>;
};

export type AcceptCompositionResponse = {
  accepted: AcceptedCompositionItem;
  draft: DraftDetail;
};

export type DiagnosticLevel = "weak" | "fair" | "strong" | "risk" | "high_risk";
export type RewriteMode = "conservative" | "conversion" | "compliance_safe";

export type DiagnosticSource = {
  source_type: "text" | "draft";
  text: string;
  draft_id?: string | null;
  platform?: string | null;
  audience?: string | null;
  purpose?: string | null;
  style?: string | null;
  industry?: string | null;
};

export type DimensionFinding = {
  dimension: string;
  level: DiagnosticLevel;
  reason: string;
  suggestion: string;
};

export type SentenceIssue = {
  text: string;
  dimension: string;
  level: DiagnosticLevel;
  reason: string;
  suggestion: string;
  replacement: string;
};

export type RewriteCandidate = {
  candidate_id: string;
  mode: RewriteMode;
  title: string;
  text: string;
  reason: string;
};

export type CopyDiagnosisRequest = {
  text?: string | null;
  draft_id?: string | null;
  platform?: string | null;
  audience?: string | null;
  purpose?: string | null;
  style?: string | null;
  industry?: string | null;
  constraints?: string[];
  rewrite_modes?: RewriteMode[];
  metadata?: Record<string, unknown>;
};

export type CopyDiagnosisResult = {
  source: DiagnosticSource;
  summary: string;
  overall_level: DiagnosticLevel;
  dimensions: DimensionFinding[];
  sentence_issues: SentenceIssue[];
  rewrite_candidates: RewriteCandidate[];
  risk_warnings: RiskWarning[];
  model?: string | null;
};

export type AcceptDiagnosticRewriteRequest = {
  draft_id: string;
  task_id: string;
  candidate_id: string;
  label?: string | null;
  metadata?: Record<string, unknown>;
};

export type AcceptedDiagnosticRewrite = {
  draft_id: string;
  task_id: string;
  candidate_id: string;
  rewrite_text: string;
  model?: string | null;
  metadata: Record<string, unknown>;
};

export type AcceptDiagnosticRewriteResponse = {
  accepted: AcceptedDiagnosticRewrite;
  draft: DraftDetail;
  version: DraftVersionDetail;
};

export const emptyAnalysis: Analysis = {
  topic: "",
  target_user: "",
  core_pain: "",
  emotion_buttons: [],
  hook: "",
  structure: [],
  expression_skills: [],
  reusable_template: "",
  suitable_scenarios: [],
  risk_warnings: [],
  confidence: 0.7
};
