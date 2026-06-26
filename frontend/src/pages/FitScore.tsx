import { useState } from "react";
import { FitScoreItem, labelClass, PipelineResult, runPipeline, tierClass } from "../api";

// Página Score de Fit (ux.md §6.5 — o DIFERENCIAL): roda o pipeline e mostra as
// startups RANKEADAS pelo Fit Score com o Inception (0–100), com o breakdown
// dos três eixos que compõem a nota. É a fila de abordagem do gestor.

function Bar({ label, value }: { label: string; value: number }) {
  return (
    <div className="bar-row">
      <span className="bar-lbl">{label}</span>
      <div className="bar-track">
        <div className="bar-fill" style={{ width: `${Math.round(value * 100)}%` }} />
      </div>
      <span className="bar-val">{value.toFixed(2)}</span>
    </div>
  );
}

function Row({ item, rank }: { item: FitScoreItem; rank: number }) {
  return (
    <div className="rank-row">
      <div className="rank-num">#{rank}</div>
      <div className="rank-main">
        <div className="rank-head">
          <strong>{item.name}</strong>
          <span className={`badge ${labelClass(item.label)}`}>{item.label}</span>
        </div>
        <div className="bars">
          <Bar label="Maturidade" value={item.breakdown.maturity} />
          <Bar label="Fit NVIDIA" value={item.breakdown.nvidia_fit} />
          <Bar label="Evidências" value={item.breakdown.evidence} />
        </div>
      </div>
      <div className={`score-big ${tierClass(item.tier)}`}>
        {item.score}
        <span className="score-tier">{item.tier}</span>
      </div>
    </div>
  );
}

export default function FitScore() {
  const [query, setQuery] = useState("startups de IA jurídica no Brasil");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<PipelineResult | null>(null);

  async function run() {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      setResult(await runPipeline(query));
    } catch (e) {
      setError(e instanceof Error ? e.message : "falha ao executar o pipeline");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="page">
      <div className="pipeline-form">
        <input
          className="pipeline-input"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && !loading && run()}
          placeholder="Descreva as startups que você procura…"
        />
        <button className="btn-primary" onClick={run} disabled={loading}>
          {loading ? "Calculando…" : "Rankear por fit"}
        </button>
      </div>
      <p className="hint">
        Fit Score = 40% maturidade de IA + 35% fit com a stack NVIDIA (rerank) +
        25% confiança das evidências. Ordenado por prioridade de abordagem.
      </p>

      {error && <div className="alert">Erro: {error}</div>}

      {result && result.fit_scores.length === 0 && (
        <div className="placeholder">
          Nenhuma startup pontuada para “{result.query}”.
        </div>
      )}

      {result?.fit_scores.map((item, i) => (
        <Row item={item} rank={i + 1} key={item.name} />
      ))}
    </div>
  );
}
