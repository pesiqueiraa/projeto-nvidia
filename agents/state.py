"""Estado compartilhado do grafo multi-agente (RadarState).

No LangGraph o `State` é o objeto que TRAFEGA entre os nós. Cada nó recebe
o estado atual e devolve um dicionário com as chaves que quer atualizar —
o LangGraph faz o merge. Usar `TypedDict` mantém isso explícito e tipado.

Para a Semana 1 o estado é mínimo. Ele cresce a cada entregável:
  - Semana 2: + startups extraídas, classificação, confiança
  - Semana 3: + chunks RAG, recomendações, briefing
"""
from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages


class RadarState(TypedDict, total=False):
    """Estado que percorre o grafo de agentes.

    `total=False` => todas as chaves são opcionais; cada nó preenche só o
    que lhe cabe, como num pipeline.
    """

    # Consulta original do gestor (entrada do Search Planner)
    query: str

    # Saída do Search Planner: termos de busca + fontes priorizadas
    search_terms: list[str]
    sources: list[str]

    # Saída do Scraper: startups cruas descobertas nas fontes (cada item é um
    # RawStartup serializado com .model_dump()). Ainda NÃO estruturadas — o
    # Extractor Agent enriquece depois (setor, funding, stack, sinais de IA).
    raw_startups: list[dict]

    # Saída do Extractor: startups já ESTRUTURADAS (cada item é um
    # StructuredStartup serializado com .model_dump()) — produto, setor,
    # estágio, funding, stack e os sinais de IA que o Classifier vai usar.
    extracted_startups: list[dict]

    # Saída do Classifier: startups ROTULADAS como AI-native / AI-enabled /
    # Non-AI (cada item é um ClassifiedStartup serializado, que aninha o
    # StructuredStartup + label, justificativa e confiança da evidência).
    classified_startups: list[dict]

    # `add_messages` é um reducer do LangGraph: em vez de sobrescrever,
    # ACUMULA mensagens. Útil para depurar o raciocínio dos agentes.
    messages: Annotated[list, add_messages]
