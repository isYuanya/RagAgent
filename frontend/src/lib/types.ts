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
  metrics: Record<string, number>;
  status: string;
  auto_analysis?: Analysis | null;
  reviewed_analysis?: Analysis | null;
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
