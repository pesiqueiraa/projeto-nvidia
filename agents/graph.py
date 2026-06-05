"""Grafo LangGraph mínimo — exemplo didático de 2 nós.

CLAUDE.md (Entregável 2) pede explicitamente: "Comece com um grafo simples
de 2 nós antes de implementar todos os agentes. Entenda o conceito de
State, Node e Edge."

Este arquivo é esse ponto de partida. Os dois nós abaixo NÃO chamam LLM
ainda — eles só demonstram o fluxo State -> Node -> Edge. O Search Planner
real (com LLM) entra na Semana 1 substituindo o stub `plan_node`.

Fluxo:
    START -> plan -> echo -> END
"""
from langgraph.graph import END, START, StateGraph

from agents.state import RadarState


def plan_node(state: RadarState) -> dict:
    """Nó 1 (stub do Search Planner).

    Recebe a `query` e devolve termos de busca + fontes. Por enquanto é uma
    regra fixa; será trocado por uma chamada de LLM (`core.llm.get_llm`).
    Um nó SEMPRE retorna um dict com as chaves do estado que quer atualizar.
    """
    query = state.get("query", "")
    return {
        "search_terms": [t.strip() for t in query.split() if t.strip()],
        "sources": ["distrito.me", "neofeed.com.br"],
        "messages": [("ai", f"[plan] query recebida: {query!r}")],
    }


def echo_node(state: RadarState) -> dict:
    """Nó 2: apenas confirma o que o nó anterior produziu.

    Demonstra que o estado atualizado pelo `plan_node` já está visível aqui.
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

    builder.add_node("plan", plan_node)
    builder.add_node("echo", echo_node)

    builder.add_edge(START, "plan")
    builder.add_edge("plan", "echo")
    builder.add_edge("echo", END)

    return builder.compile()


# Grafo compilado pronto para importar (ex.: pela API).
graph = build_graph()


if __name__ == "__main__":
    # Execução manual para aprender: `uv run python -m agents.graph`
    resultado = graph.invoke({"query": "startups de IA generativa no Brasil"})
    print("Estado final:")
    for chave, valor in resultado.items():
        print(f"  {chave}: {valor}")
