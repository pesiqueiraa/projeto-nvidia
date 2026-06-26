import { useState } from "react";
import {
  confClass,
  labelClass,
  PipelineResult,
  runPipeline,
  tierClass,
} from "../api";

// Página Pipeline (ux.md §6.5): o gestor digita uma consulta, dispara o
// pipeline multi-agente no backend (POST /api/pipeline/run) e vê as startups
// qualificadas com o Fit Score, a stack NVIDIA recomendada e a confiança.

export default function Pipeline() {
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

  // Junta o retrato classificado e o fit score à recomendação, por nome.
  const porNome = new Map(result?.classified_startups.map((c) => [c.startup.name, c]));
  const fitPorNome = new Map(result?.fit_scores.map((f) => [f.name, f]));

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
          {loading ? "Executando…" : "Executar pipeline"}
        </button>
      </div>

      <p className="hint">
        Executa os 9 agentes de verdade (busca → coleta → classificação → RAG
        NVIDIA → recomendação → briefing). Pode levar alguns segundos e depende
        das fontes públicas no ar.
      </p>

      {error && <div className="alert">Erro: {error}</div>}

      {result && result.recommendations.length === 0 && (
        <div className="placeholder">
          Nenhuma startup qualificada para “{result.query}”. Veja o trace abaixo
          para entender o que cada agente fez.
        </div>
      )}

      {result?.recommendations.map((rec) => {
        const c = porNome.get(rec.name);
        const fit = fitPorNome.get(rec.name);
        return (
          <div className="card" key={rec.name}>
            <div className="card-head">
              <h2>{rec.name}</h2>
              <span className={`badge ${labelClass(rec.label)}`}>{rec.label}</span>
              {fit && (
                <span className={`badge fit ${tierClass(fit.tier)}`}>
                  Fit {fit.score}/100
                </span>
              )}
            </div>

            {c && (
              <div className="meta">
                {c.startup.sector ?? "—"} · {c.startup.stage ?? "—"} ·{" "}
                {c.startup.funding ?? "—"}
              </div>
            )}
            {c?.startup.description && <p className="desc">{c.startup.description}</p>}
            {c?.rationale && <p className="rationale">{c.rationale}</p>}

            <div className="section-lbl">
              Stack NVIDIA recomendada
              <span className={`badge ${confClass(rec.overall_confidence)}`}>
                fit {rec.overall_confidence}
              </span>
            </div>

            {rec.technologies.length === 0 && (
              <div className="muted">Nenhuma tecnologia com fit suficiente.</div>
            )}
            {rec.technologies.map((t) => (
              <div className="tech" key={t.tech}>
                <div className="tech-head">
                  <a href={t.url} target="_blank" rel="noreferrer" className="tech-name">
                    {t.tech}
                  </a>
                  <span className={`badge ${confClass(t.confidence)}`}>
                    {t.confidence} · {t.relevance_score.toFixed(3)}
                  </span>
                </div>
                <div className="snippet">{t.snippet}</div>
              </div>
            ))}

            {rec.notes.map((n) => (
              <div className="note" key={n}>
                ⚠ {n}
              </div>
            ))}
          </div>
        );
      })}

      {result && (
        <details className="trace">
          <summary>Trace do grafo ({result.trace.length} passos)</summary>
          {result.trace.map((m, i) => (
            <div className="trace-line" key={i}>
              {m}
            </div>
          ))}
        </details>
      )}
    </div>
  );
}
