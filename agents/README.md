# `agents/` — Orquestração multi-agente (LangGraph)

Cada agente do NVISION vive aqui, um conceito por arquivo. A orquestração
usa **LangGraph** (Entregável 2).

## Arquivos atuais

| Arquivo | O quê |
|---|---|
| `state.py` | `RadarState` — o estado tipado que trafega entre os nós. |
| `search_planner.py` | Primeiro agente real: LLM com saída estruturada (`SearchPlan`), escolhe termos de busca e fontes dentre o catálogo fixo. |
| `graph.py` | Grafo de **2 nós** (`search_planner` → `echo`). `echo` ainda é placeholder até o Scraper Agent existir. |

## Próximos agentes (roadmap ux.md)

`search_planner` → `scraper` → `extractor` → `classifier` →
`evidence_validator` → `nvidia_rag` → `recommendation` → `briefing`,
com uma transição **condicional** em `evidence_validator` (reprocessa se a
confiança for baixa).

## O que aprendi

- `with_structured_output` força o LLM a devolver algo compatível com um
  schema Pydantic, eliminando parsing manual de texto livre.
- Testar código que chama LLM sem gastar dinheiro/rede: o nó recebe o LLM
  via uma referência de módulo (`get_llm`) que pode ser trocada por um
  `FakeLLM` nos testes via `monkeypatch` — sem mudar a assinatura da função
  nem arriscar conflito com a injeção automática de `config` do LangGraph.
