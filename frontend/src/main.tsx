import React from "react";
import ReactDOM from "react-dom/client";
import { AlertTriangle, Database, FileText, Sparkles } from "lucide-react";
import "./styles.css";

type AnalysisResponse = {
  topic: string;
  target_user: string;
  core_pain: string;
  emotion_buttons: string[];
  hook: string;
  structure: string[];
  expression_skills: string[];
  reusable_template: string;
  suitable_scenarios: string[];
  risk_warnings: Array<{ level: string; message: string; suggestion?: string }>;
  confidence: number;
};

type GenerateResponse = {
  topic_direction: string;
  hooks: string[];
  script: string;
  shot_suggestions: string[];
  titles: string[];
  comment_guides: string[];
  risk_warnings: Array<{ level: string; message: string; suggestion?: string }>;
};

const apiBase = import.meta.env.VITE_API_BASE_URL ?? "";

function App() {
  const [sourceText, setSourceText] = React.useState(
    "如果你总觉得护肤没效果，先别急着换产品，可能是你的使用顺序错了。"
  );
  const [industry, setIndustry] = React.useState("美妆");
  const [audience, setAudience] = React.useState("25-35岁女性");
  const [purpose, setPurpose] = React.useState("引流");
  const [style, setStyle] = React.useState("犀利/共情/专业");
  const [analysis, setAnalysis] = React.useState<AnalysisResponse | null>(null);
  const [generation, setGeneration] = React.useState<GenerateResponse | null>(null);
  const [loading, setLoading] = React.useState<string | null>(null);

  async function analyze() {
    setLoading("analysis");
    const response = await fetch(`${apiBase}/api/copy/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ source_text: sourceText, industry, audience, purpose, style })
    });
    setAnalysis(await response.json());
    setLoading(null);
  }

  async function generate() {
    setLoading("generation");
    const response = await fetch(`${apiBase}/api/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        industry,
        audience,
        purpose,
        style,
        product_name: "核心产品",
        reference_text: sourceText,
        version_count: 3
      })
    });
    setGeneration(await response.json());
    setLoading(null);
  }

  return (
    <main className="shell">
      <aside className="sidebar">
        <div className="brand">
          <Sparkles size={22} />
          <span>RagAgent</span>
        </div>
        <nav>
          <a className="active"><FileText size={18} /> 文案工作台</a>
          <a><Database size={18} /> 知识库</a>
          <a><AlertTriangle size={18} /> 合规评审</a>
        </nav>
      </aside>

      <section className="workspace">
        <header>
          <div>
            <h1>文案拆解与生成工作台</h1>
            <p>输入样本文案，提取结构、钩子、风险点，并生成可替换版本。</p>
          </div>
          <div className="status">Local</div>
        </header>

        <div className="grid">
          <section className="panel input-panel">
            <h2>输入</h2>
            <textarea value={sourceText} onChange={(event) => setSourceText(event.target.value)} />
            <div className="fields">
              <label>行业<input value={industry} onChange={(event) => setIndustry(event.target.value)} /></label>
              <label>人群<input value={audience} onChange={(event) => setAudience(event.target.value)} /></label>
              <label>目的<input value={purpose} onChange={(event) => setPurpose(event.target.value)} /></label>
              <label>风格<input value={style} onChange={(event) => setStyle(event.target.value)} /></label>
            </div>
            <div className="actions">
              <button onClick={analyze} disabled={loading !== null}>拆解文案</button>
              <button className="secondary" onClick={generate} disabled={loading !== null}>生成版本</button>
            </div>
          </section>

          <section className="panel">
            <h2>拆解结果</h2>
            {analysis ? (
              <div className="result">
                <strong>{analysis.topic}</strong>
                <p>{analysis.core_pain}</p>
                <ul>{analysis.structure.map((item) => <li key={item}>{item}</li>)}</ul>
                <div className="chips">{analysis.emotion_buttons.map((item) => <span key={item}>{item}</span>)}</div>
                <small>置信度 {(analysis.confidence * 100).toFixed(0)}%</small>
              </div>
            ) : <p className="empty">等待拆解结果</p>}
          </section>

          <section className="panel wide">
            <h2>生成结果</h2>
            {generation ? (
              <div className="result">
                <strong>{generation.topic_direction}</strong>
                <p>{generation.script}</p>
                <div className="columns">
                  <div><b>标题</b>{generation.titles.map((item) => <span key={item}>{item}</span>)}</div>
                  <div><b>钩子</b>{generation.hooks.map((item) => <span key={item}>{item}</span>)}</div>
                  <div><b>分镜</b>{generation.shot_suggestions.map((item) => <span key={item}>{item}</span>)}</div>
                </div>
              </div>
            ) : <p className="empty">等待生成结果</p>}
          </section>
        </div>
      </section>
    </main>
  );
}

ReactDOM.createRoot(document.getElementById("root")!).render(<App />);
