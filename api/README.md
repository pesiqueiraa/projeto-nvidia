# `api/` — Backend FastAPI

Expõe os endpoints REST e (futuramente) o WebSocket do live log.

Rodar em desenvolvimento:

```bash
uv run uvicorn api.main:app --reload
# Docs interativas: http://localhost:8000/docs
```

## Endpoints atuais (fundação)

| Método | Rota | O quê |
|---|---|---|
| GET | `/health` | Liveness + provider de LLM ativo. |
| POST | `/api/demo/plan` | Executa o grafo de 2 nós (prova FastAPI ↔ LangGraph). |

## Endpoints planejados (ux.md §7.2)

`POST /api/pipeline/run`, `WS /api/pipeline/{id}/stream`,
`GET /api/startups`, `GET /api/startups/{id}/fit`, `GET /api/analytics`,
`GET /api/sinais`, `POST /api/qualificadas/{id}/advance`, …
