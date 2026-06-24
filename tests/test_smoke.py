"""Testes de fumaça da fundação.

Validam que as peças centrais carregam e conversam, sem depender de chaves
de API nem de bancos no ar (o LLM é falso via `patch_get_llm`).
Rode com: `uv run pytest`
"""
from fastapi.testclient import TestClient

from agents.graph import graph
from api.main import app

client = TestClient(app)


def test_health_ok():
    """O backend sobe e responde no /health."""
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_graph_runs_two_nodes(patch_get_llm, fixed_search_plan):
    """O grafo de 2 nós executa: search_planner (LLM falso) -> echo."""
    final = graph.invoke({"query": "fintechs de IA"})
    # search_planner_node devolve o que o LLM falso produziu
    assert final["search_terms"] == fixed_search_plan.search_terms
    assert final["sources"] == fixed_search_plan.sources
    # os dois nós deixaram rastro em messages (reducer add_messages)
    assert len(final["messages"]) == 2


def test_demo_plan_endpoint(patch_get_llm, fixed_search_plan):
    """O endpoint de demo executa o grafo via HTTP, com LLM falso."""
    resp = client.post("/api/demo/plan", json={"query": "fintechs de IA"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["search_terms"] == fixed_search_plan.search_terms
    assert body["sources"] == fixed_search_plan.sources
