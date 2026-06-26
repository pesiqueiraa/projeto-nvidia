# tests/test_search_planner.py
"""Testes do Search Planner Agent — sempre com LLM falso (patch_get_llm)."""
from agents.search_planner import SOURCE_CATALOG, search_planner_node


def test_search_planner_node_returns_llm_plan(patch_get_llm, fixed_search_plan):
    resultado = search_planner_node({"query": "fintechs de IA"})

    assert resultado["search_terms"] == fixed_search_plan.search_terms
    assert resultado["sources"] == fixed_search_plan.sources
    assert len(resultado["messages"]) == 1


def test_search_planner_node_filters_sources_outside_catalog(patch_get_llm, fixed_search_plan):
    # Mistura uma fonte válida com uma fora do catálogo na resposta do LLM falso.
    # `fixed_search_plan` é o mesmo objeto que o FakeLLM devolve (mutação é vista
    # no `.invoke()`, já que `patch_get_llm` guarda a referência, não uma cópia).
    fixed_search_plan.sources = ["wow.ac", "site-fora-do-catalogo.com"]

    resultado = search_planner_node({"query": "qualquer coisa"})

    assert resultado["sources"] == ["wow.ac"]
    assert "site-fora-do-catalogo.com" not in resultado["sources"]
    assert "wow.ac" in SOURCE_CATALOG  # catálogo real (registry) contém a fonte válida
