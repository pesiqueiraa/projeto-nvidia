"""Grafo LangGraph do NVISION.

Três estações reais já implementadas:
  1. `search_planner_node` (LLM) — query -> termos de busca + fontes.
  2. `scraper_node`        — fontes -> startups cruas descobertas.
  3. `enricher_node`       — para quem tem detail_url, coleta o conteúdo da
                             página (trafilatura) -> matéria-prima do Extractor.

As próximas estações (extractor, classifier, ...) entram nas semanas
seguintes, incluindo a aresta CONDICIONAL no evidence_validator (reprocessa
via scraper quando a confiança for baixa) — ver README §Pipeline.

Fluxo atual:
    START -> search_planner -> scraper -> enricher -> END
"""
from langgraph.graph import END, START, StateGraph

from agents.enricher import enricher_node
from agents.scraper import scraper_node
from agents.search_planner import search_planner_node
from agents.state import RadarState


def build_graph():
    """Monta e compila o grafo. Retorna um objeto invocável.

    StateGraph(RadarState): o estado que percorre o grafo.
    add_node:  registra uma função como nó.
    add_edge:  liga dois nós (aresta incondicional).
    compile(): valida o grafo e devolve algo com `.invoke()`.
    """
    builder = StateGraph(RadarState)

    builder.add_node("search_planner", search_planner_node)
    builder.add_node("scraper", scraper_node)
    builder.add_node("enricher", enricher_node)

    builder.add_edge(START, "search_planner")
    builder.add_edge("search_planner", "scraper")
    builder.add_edge("scraper", "enricher")
    builder.add_edge("enricher", END)

    return builder.compile()


# Grafo compilado pronto para importar (ex.: pela API).
graph = build_graph()


if __name__ == "__main__":
    # Execução manual — exige LLM_PROVIDER + chave no .env (search_planner usa
    # LLM) e acesso à rede (scraper renderiza um site real).
    resultado = graph.invoke({"query": "startups de IA generativa no Brasil"})
    print("Estado final:")
    for chave, valor in resultado.items():
        print(f"  {chave}: {valor}")
