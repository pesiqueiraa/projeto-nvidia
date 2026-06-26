"""Aplicação FastAPI do NVISION.

Semana 1: apenas o esqueleto — `/health` para validar que o backend sobe e
um endpoint de demonstração que executa o grafo LangGraph de 2 nós. Os
endpoints reais do ux.md (§7.2) entram nas semanas seguintes:

    POST /api/pipeline/run        WS /api/pipeline/{id}/stream
    GET  /api/startups            GET /api/analytics  ...

Rode com:  uv run uvicorn api.main:app --reload
Docs em:   http://localhost:8000/docs
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agents.graph import graph
from core.config import settings
from database import repo

app = FastAPI(
    title="NVISION — NVIDIA Startup AI Radar",
    version="0.1.0",
    description="Plataforma multi-agente de inteligência estratégica para o NVIDIA Inception.",
)

# CORS liberado para o frontend Vite em desenvolvimento (porta 5173).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["infra"])
def health() -> dict:
    """Liveness check. Confirma que o backend está no ar e qual LLM está ativo."""
    return {
        "status": "ok",
        "app_env": settings.app_env,
        "llm_provider": settings.llm_provider,
    }


class PlanRequest(BaseModel):
    query: str


@app.post("/api/demo/plan", tags=["demo"])
def demo_plan(req: PlanRequest) -> dict:
    """Executa o grafo e devolve só o PLANO de busca (search_planner).

    Endpoint leve para inspecionar o que o Search Planner produziu sem precisar
    do payload completo. Para o resultado completo, use `/api/pipeline/run`.
    """
    final_state = graph.invoke({"query": req.query})
    return {
        "search_terms": final_state.get("search_terms", []),
        "sources": final_state.get("sources", []),
        "trace": [str(m) for m in final_state.get("messages", [])],
    }


class PipelineRequest(BaseModel):
    query: str


@app.post("/api/pipeline/run", tags=["pipeline"])
def pipeline_run(req: PipelineRequest) -> dict:
    """Executa o pipeline multi-agente COMPLETO e devolve o resultado.

    Roda os 9 nós (search_planner -> ... -> briefing) e expõe as saídas que
    interessam à interface: as startups classificadas, as recomendações de
    stack NVIDIA e os briefings executivos (markdown), além do trace do grafo.

    Atenção: é uma chamada SÍNCRONA e pode demorar (scraping + LLM + RAG por
    startup). O endpoint com streaming (ux.md §7.2) entra com a interface.
    """
    final_state = graph.invoke({"query": req.query})
    # Persiste o resultado para as páginas Qualificadas/Analytics (resiliente:
    # uma falha de banco não derruba a resposta do pipeline).
    salvas = repo.persist_pipeline_result(final_state)
    return {
        "query": req.query,
        "search_terms": final_state.get("search_terms", []),
        "sources": final_state.get("sources", []),
        "classified_startups": final_state.get("classified_startups", []),
        "recommendations": final_state.get("recommendations", []),
        "fit_scores": final_state.get("fit_scores", []),
        "briefings": final_state.get("briefings", []),
        "persisted": salvas,
        "trace": [str(m) for m in final_state.get("messages", [])],
    }


@app.get("/api/startups", tags=["startups"])
def list_startups(limit: int = 200) -> dict:
    """Lista as startups acumuladas no banco (página Qualificadas).

    Diferente do pipeline (que roda os agentes), aqui só LÊ o que já foi
    qualificado e persistido — rápido e sem custo de LLM.
    """
    return {"startups": repo.list_startups(limit)}
