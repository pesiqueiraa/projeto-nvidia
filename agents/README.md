# `agents/` — Orquestração multi-agente (LangGraph)

Cada agente do NVISION vive aqui, um conceito por arquivo. A orquestração
usa **LangGraph** (Entregável 2).

## Arquivos atuais (fundação / Semana 1)

| Arquivo | O quê |
|---|---|
| `state.py` | `RadarState` — o estado tipado que trafega entre os nós. |
| `graph.py` | Grafo mínimo de **2 nós** (`plan` → `echo`), ponto de partida didático. |

## Por que começar com 2 nós?

O CLAUDE.md pede explicitamente: entender `State`, `Node` e `Edge` antes de
montar os 8 agentes. O grafo atual não chama LLM — ele só demonstra o fluxo
`START → plan → echo → END` e como um nó atualiza o estado para o próximo ler.

Rode isolado para ver o estado evoluir:

```bash
uv run python -m agents.graph
```

## Próximos agentes (roadmap ux.md)

`search_planner` → `scraper` → `extractor` → `classifier` →
`evidence_validator` → `nvidia_rag` → `recommendation` → `briefing`,
com uma transição **condicional** em `evidence_validator` (reprocessa se a
confiança for baixa).

## O que aprendi
> _(preencher conforme implementamos — exigência do CLAUDE.md)_
