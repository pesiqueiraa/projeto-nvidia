// Camada de acesso ao backend + tipos compartilhados entre as páginas.
// Espelha o payload de POST /api/pipeline/run (api/main.py).

export interface TechRec {
  tech: string;
  url: string;
  relevance_score: number;
  confidence: string;
  snippet: string;
}
export interface Recommendation {
  name: string;
  label: string;
  technologies: TechRec[];
  overall_confidence: string;
  notes: string[];
}
export interface StartupInner {
  name: string;
  description: string | null;
  sector: string | null;
  stage: string | null;
  funding: string | null;
}
export interface Classified {
  startup: StartupInner;
  label: string;
  rationale: string;
  confidence: string;
}
export interface FitScoreItem {
  name: string;
  label: string;
  score: number;
  tier: string;
  breakdown: { maturity: number; nvidia_fit: number; evidence: number };
  rationale: string;
}
export interface PipelineResult {
  query: string;
  classified_startups: Classified[];
  recommendations: Recommendation[];
  fit_scores: FitScoreItem[];
  briefings: { name: string; label: string; markdown: string }[];
  trace: string[];
}

// Startup persistida no banco (página Qualificadas).
export interface StartupRow {
  name: string;
  sector: string | null;
  stage: string | null;
  funding: string | null;
  classification: string;
  confidence: number;
  fit_score: number | null;
  created_at: string;
}

export async function listStartups(): Promise<StartupRow[]> {
  const resp = await fetch("/api/startups");
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  return (await resp.json()).startups;
}

// Agregados do ecossistema (página Analytics).
export interface Analytics {
  total: number;
  avg_fit: number | null;
  by_classification: { classification: string; count: number }[];
  by_sector: { sector: string; count: number }[];
  by_tier: { tier: string; count: number }[];
}

export async function getAnalytics(): Promise<Analytics> {
  const resp = await fetch("/api/analytics");
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  return resp.json();
}

export async function runPipeline(query: string): Promise<PipelineResult> {
  const resp = await fetch("/api/pipeline/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query }),
  });
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  return resp.json();
}

// --- Cores semânticas (ux.md §2.2), reusadas pelas páginas ---
export function labelClass(label: string): string {
  if (label === "AI-native") return "badge-green";
  if (label === "AI-enabled") return "badge-amber";
  return "badge-dim";
}
export function confClass(conf: string): string {
  if (conf === "high") return "badge-green";
  if (conf === "medium") return "badge-amber";
  return "badge-red";
}
export function tierClass(tier: string): string {
  if (tier === "alto") return "badge-green";
  if (tier === "médio") return "badge-amber";
  return "badge-red";
}
