"""Testes de fumaça da fundação.

Validam que as peças centrais carregam e conversam, sem depender de chaves
de API nem de bancos no ar. Rode com: `uv run pytest`
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


def test_graph_runs_two_nodes():
    """O grafo de 2 nós executa e popula o estado (State -> Node -> Edge)."""
    final = graph.invoke({"query": "visão computacional agro"})
    # plan_node quebra a query em termos
    assert final["search_terms"] == ["visão", "computacional", "agro"]
    # os dois nós deixaram rastro em messages (reducer add_messages)
    assert len(final["messages"]) == 2


def test_demo_plan_endpoint():
    """O endpoint de demo executa o grafo via HTTP."""
    resp = client.post("/api/demo/plan", json={"query": "fintech IA"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["search_terms"] == ["fintech", "IA"]
    assert "distrito.me" in body["sources"]
