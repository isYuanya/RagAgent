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
  errors: Array<{ row_number?: number; message?: string }>;
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

export type TagCategory =
  | "industry"
  | "emotion"
  | "purpose"
  | "audience"
  | "hook_type"
  | "custom";

export type KnowledgeTag = {
  id: string;
  name: string;
  category: TagCategory;
  description?: string | null;
  source?: SourceReference | null;
  metadata: Record<string, unknown>;
};

export type KnowledgeTagCreate = Omit<KnowledgeTag, "id">;

export type KnowledgeCase = {
  id: string;
  title: string;
  reason: string;
  performance_summary?: string | null;
  source?: SourceReference | null;
  metadata: Record<string, unknown>;
};

export type KnowledgeCaseCreate = Omit<KnowledgeCase, "id">;

export type BlockType =
  | "sensitive_word"
  | "violation"
  | "do_not_copy"
  | "custom";

export type BlockSeverity = "low" | "medium" | "high";

export type KnowledgeBlock = {
  id: string;
  content: string;
  block_type: BlockType;
  reason?: string | null;
  severity: BlockSeverity;
  source?: SourceReference | null;
  metadata: Record<string, unknown>;
};

export type KnowledgeBlockCreate = Omit<KnowledgeBlock, "id">;

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
