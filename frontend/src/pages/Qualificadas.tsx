import { useEffect, useState } from "react";
import { labelClass, listStartups, StartupRow } from "../api";

// Página Qualificadas (ux.md §6.5): o FUNIL acumulado. Diferente da Pipeline
// (que roda os agentes), aqui só LEMOS as startups já qualificadas e salvas no
// banco — é o que prova que os resultados estão sendo persistidos e reusados.

function tierFromScore(score: number | null): string {
  if (score === null) return "badge-dim";
  if (score >= 70) return "badge-green";
  if (score >= 40) return "badge-amber";
  return "badge-red";
}

export default function Qualificadas() {
  const [rows, setRows] = useState<StartupRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      setRows(await listStartups());
    } catch (e) {
      setError(e instanceof Error ? e.message : "falha ao carregar");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  return (
    <div className="page">
      <div className="qual-head">
        <p className="hint">
          Startups já qualificadas e persistidas (acumuladas entre execuções do
          pipeline), ordenadas por Fit Score.
        </p>
        <button className="btn-primary" onClick={load} disabled={loading}>
          {loading ? "Atualizando…" : "Atualizar"}
        </button>
      </div>

      {error && <div className="alert">Erro: {error}</div>}

      {rows && rows.length === 0 && (
        <div className="placeholder">
          Nenhuma startup persistida ainda. Rode o pipeline na aba Pipeline para
          popular o funil.
        </div>
      )}

      {rows && rows.length > 0 && (
        <table className="qual-table">
          <thead>
            <tr>
              <th>Startup</th>
              <th>Setor</th>
              <th>Estágio</th>
              <th>Classificação</th>
              <th className="num">Fit</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((s) => (
              <tr key={s.name}>
                <td className="strong">{s.name}</td>
                <td>{s.sector ?? "—"}</td>
                <td>{s.stage ?? "—"}</td>
                <td>
                  <span className={`badge ${labelClass(s.classification)}`}>
                    {s.classification}
                  </span>
                </td>
                <td className="num">
                  <span className={`badge ${tierFromScore(s.fit_score)}`}>
                    {s.fit_score ?? "—"}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
