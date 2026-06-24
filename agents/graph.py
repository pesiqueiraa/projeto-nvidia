"""Grafo LangGraph do NVISION.

Primeira estação real do pipeline: `search_planner_node` (LLM, em
agents/search_planner.py) substitui o antigo stub `plan_node`. `echo_node`
continua como segunda estação só pra demonstrar o fluxo State -> Node ->
Edge — será substituído pelo `scraper_node` quando o Scraper Agent for
implementado (próxima rodada).

Fluxo:
    START -> search_planner -> echo -> END
"""
from langgraph.graph import END, START, StateGraph

from agents.search_planner import search_planner_node
from agents.state import RadarState


def echo_node(state: RadarState) -> dict:
    """Nó 2 (placeholder): apenas confirma o que o search_planner produziu.

    Demonstra que o estado atualizado pelo `search_planner_node` já está
    visível aqui. Será substituído pelo `scraper_node` real.
    """
    termos = state.get("search_terms", [])
    return {"messages": [("ai", f"[echo] {len(termos)} termos prontos: {termos}")]}


def build_graph():
    """Monta e compila o grafo. Retorna um objeto invocável.

    StateGraph(RadarState): o estado que percorre o grafo.
    add_node:  registra uma função como nó.
    add_edge:  liga dois nós (aresta incondicional).
    compile(): valida o grafo e devolve algo com `.invoke()`.
    """
    builder = StateGraph(RadarState)

    builder.add_node("search_planner", search_planner_node)
    builder.add_node("echo", echo_node)

    builder.add_edge(START, "search_planner")
    builder.add_edge("search_planner", "echo")
    builder.add_edge("echo", END)

    return builder.compile()


# Grafo compilado pronto para importar (ex.: pela API).
graph = build_graph()


if __name__ == "__main__":
    # Execução manual — exige LLM_PROVIDER + chave configurados no .env.
    resultado = graph.invoke({"query": "startups de IA generativa no Brasil"})
    print("Estado final:")
    for chave, valor in resultado.items():
        print(f"  {chave}: {valor}")
