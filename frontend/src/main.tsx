import React from "react";
import ReactDOM from "react-dom/client";
import { AlertTriangle, CheckCircle2, Database, FileUp, ListChecks, Save } from "lucide-react";
import "./styles.css";

type RiskWarning = { level: string; message: string; suggestion?: string | null };

type Analysis = {
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

type CopyAsset = {
  id: string;
  source_text: string;
  source_url?: string | null;
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

type AssetListResponse = { items: CopyAsset[]; total: number; page: number; page_size: number };
type ImportResponse = {
  imported_count: number;
  failed_count: number;
  assets: CopyAsset[];
  errors: Array<{ row_number: number; message: string }>;
};

const apiBase = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8002";

const emptyAnalysis: Analysis = {
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

function App() {
  const [assets, setAssets] = React.useState<CopyAsset[]>([]);
  const [selectedId, setSelectedId] = React.useState<string | null>(null);
  const [draft, setDraft] = React.useState<Analysis>(emptyAnalysis);
  const [status, setStatus] = React.useState("pending_review");
  const [loading, setLoading] = React.useState<string | null>(null);
  const [message, setMessage] = React.useState<string | null>(null);
  const [errors, setErrors] = React.useState<ImportResponse["errors"]>([]);

  const selected = assets.find((asset) => asset.id === selectedId) ?? null;

  React.useEffect(() => {
    void loadAssets();
  }, []);

  React.useEffect(() => {
    if (!selected) return;
    setDraft(selected.reviewed_analysis ?? selected.auto_analysis ?? emptyAnalysis);
    setStatus(selected.status);
  }, [selectedId]);

  async function loadAssets() {
    const response = await fetch(`${apiBase}/api/copy/assets?page=1&page_size=100`);
    if (!response.ok) return;
    const payload = (await response.json()) as AssetListResponse;
    setAssets(payload.items);
    setSelectedId((current) => current ?? payload.items[0]?.id ?? null);
  }

  async function uploadCsv(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    setLoading("import");
    setMessage(null);
    setErrors([]);

    try {
      const csvText = await file.text();
      const response = await fetch(`${apiBase}/api/copy/import`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ csv_text: csvText })
      });
      const payload = await response.json();
      if (!response.ok) {
        setMessage(payload.detail ?? "导入失败");
        return;
      }

      const result = payload as ImportResponse;
      setErrors(result.errors);
      setMessage(`导入 ${result.imported_count} 条，失败 ${result.failed_count} 条`);
      await loadAssets();
      setSelectedId(result.assets[0]?.id ?? selectedId);
    } finally {
      setLoading(null);
      event.target.value = "";
    }
  }

  async function saveReview() {
    if (!selected) return;
    setLoading("review");
    setMessage(null);
    try {
      const response = await fetch(`${apiBase}/api/copy/assets/${selected.id}/review`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status, reviewed_analysis: draft })
      });
      const payload = await response.json();
      if (!response.ok) {
        setMessage(payload.detail ?? "保存失败");
        return;
      }
      setAssets((current) => current.map((asset) => (asset.id === selected.id ? payload : asset)));
      setMessage("审核结果已保存");
    } finally {
      setLoading(null);
    }
  }

  return (
    <main className="shell">
      <aside className="sidebar">
        <div className="brand">
          <Database size={22} />
          <span>RagAgent</span>
        </div>
        <nav>
          <a className="active"><ListChecks size={18} /> 文案资产</a>
          <a><FileUp size={18} /> CSV 导入</a>
          <a><AlertTriangle size={18} /> 风险校正</a>
        </nav>
      </aside>

      <section className="workspace">
        <header>
          <div>
            <h1>文案资产审核工作台</h1>
            <p>批量导入样本文案，校正拆解结果，再沉淀为可检索的文案资产。</p>
          </div>
          <div className="status">Internal v1</div>
        </header>

        <div className="asset-layout">
          <section className="panel asset-list-panel">
            <div className="panel-heading">
              <h2>导入与待审</h2>
              <label className="upload-button">
                <FileUp size={16} />
                <span>{loading === "import" ? "导入中" : "上传 CSV"}</span>
                <input type="file" accept=".csv,text/csv" onChange={uploadCsv} disabled={loading !== null} />
              </label>
            </div>

            {message ? <div className="notice">{message}</div> : null}
            {errors.length > 0 ? (
              <div className="error-list">
                {errors.map((error) => (
                  <div key={`${error.row_number}-${error.message}`}>
                    第 {error.row_number} 行：{error.message}
                  </div>
                ))}
              </div>
            ) : null}

            <div className="asset-list" role="list">
              {assets.length === 0 ? (
                <p className="empty">还没有文案资产。上传包含 source_text 表头的 CSV 开始。</p>
              ) : (
                assets.map((asset) => (
                  <button
                    type="button"
                    key={asset.id}
                    className={asset.id === selectedId ? "asset-row active" : "asset-row"}
                    onClick={() => setSelectedId(asset.id)}
                  >
                    <span>{asset.auto_analysis?.topic ?? asset.source_text.slice(0, 24)}</span>
                    <small>{asset.platform ?? "未标平台"} / {asset.industry ?? "未标行业"}</small>
                    <StatusBadge status={asset.status} />
                  </button>
                ))
              )}
            </div>
          </section>

          <section className="panel review-panel">
            {selected ? (
              <>
                <div className="panel-heading">
                  <h2>校正拆解</h2>
                  <button className="icon-button" type="button" onClick={saveReview} disabled={loading !== null}>
                    <Save size={16} />
                    <span>{loading === "review" ? "保存中" : "保存审核"}</span>
                  </button>
                </div>

                <div className="source-block">
                  <b>原文</b>
                  <p>{selected.source_text}</p>
                  <div className="meta-line">
                    <span>{selected.platform ?? "未标平台"}</span>
                    <span>{selected.audience ?? "未标人群"}</span>
                    <span>{formatMetrics(selected.metrics)}</span>
                  </div>
                </div>

                <div className="review-grid">
                  <TextField label="主题" value={draft.topic} onChange={(value) => updateDraft("topic", value)} />
                  <TextField label="目标用户" value={draft.target_user} onChange={(value) => updateDraft("target_user", value)} />
                  <TextField label="核心痛点" value={draft.core_pain} onChange={(value) => updateDraft("core_pain", value)} />
                  <TextField label="开头钩子" value={draft.hook} onChange={(value) => updateDraft("hook", value)} />
                  <ListField label="情绪按钮" value={draft.emotion_buttons} onChange={(value) => updateDraft("emotion_buttons", value)} />
                  <ListField label="内容结构" value={draft.structure} onChange={(value) => updateDraft("structure", value)} />
                  <ListField label="表达技巧" value={draft.expression_skills} onChange={(value) => updateDraft("expression_skills", value)} />
                  <ListField label="适用场景" value={draft.suitable_scenarios} onChange={(value) => updateDraft("suitable_scenarios", value)} />
                </div>

                <label className="full-field">
                  可复用模板
                  <textarea
                    value={draft.reusable_template}
                    onChange={(event) => updateDraft("reusable_template", event.target.value)}
                  />
                </label>

                <div className="review-footer">
                  <label>
                    置信度
                    <input
                      type="number"
                      min="0"
                      max="1"
                      step="0.01"
                      value={draft.confidence}
                      onChange={(event) => updateDraft("confidence", Number(event.target.value))}
                    />
                  </label>
                  <label>
                    审核状态
                    <select value={status} onChange={(event) => setStatus(event.target.value)}>
                      <option value="pending_review">待审核</option>
                      <option value="approved">已确认</option>
                      <option value="rejected">已拒绝</option>
                    </select>
                  </label>
                </div>
              </>
            ) : (
              <p className="empty">选择一条导入记录后进行校正。</p>
            )}
          </section>
        </div>
      </section>
    </main>
  );

  function updateDraft<K extends keyof Analysis>(key: K, value: Analysis[K]) {
    setDraft((current) => ({ ...current, [key]: value }));
  }
}

function TextField(props: { label: string; value: string; onChange: (value: string) => void }) {
  return (
    <label>
      {props.label}
      <input value={props.value} onChange={(event) => props.onChange(event.target.value)} />
    </label>
  );
}

function ListField(props: { label: string; value: string[]; onChange: (value: string[]) => void }) {
  return (
    <label>
      {props.label}
      <textarea
        className="compact-textarea"
        value={props.value.join("\n")}
        onChange={(event) => props.onChange(splitLines(event.target.value))}
      />
    </label>
  );
}

function StatusBadge({ status }: { status: string }) {
  if (status === "approved") {
    return <span className="badge approved"><CheckCircle2 size={14} /> 已确认</span>;
  }
  if (status === "rejected") {
    return <span className="badge rejected"><AlertTriangle size={14} /> 已拒绝</span>;
  }
  return <span className="badge">待审核</span>;
}

function splitLines(value: string) {
  return value.split(/\r?\n/).map((item) => item.trim()).filter(Boolean);
}

function formatMetrics(metrics: Record<string, number>) {
  const parts = Object.entries(metrics).map(([key, value]) => `${key} ${value}`);
  return parts.length > 0 ? parts.join(" / ") : "无指标";
}

ReactDOM.createRoot(document.getElementById("root")!).render(<App />);
