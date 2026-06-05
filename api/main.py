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
    """Executa o grafo de 2 nós (Entregável 2 — ponto de partida).

    Prova que FastAPI + LangGraph estão conversando. Será substituído pelo
    `POST /api/pipeline/run` real quando os agentes existirem.
    """
    final_state = graph.invoke({"query": req.query})
    return {
        "search_terms": final_state.get("search_terms", []),
        "sources": final_state.get("sources", []),
        "trace": [str(m) for m in final_state.get("messages", [])],
    }
