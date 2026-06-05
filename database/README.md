# `database/` — Dados estruturados (PostgreSQL)

Schema relacional das startups e do funil. O `schema.sql` é aplicado
automaticamente na primeira subida do Postgres via docker-compose.

## Tabelas (ux.md §7.6)

| Tabela | O quê |
|---|---|
| `startups` | Perfil + classificação + confiança + fit_score. |
| `pipeline_stages` | Funil de qualificação (Kanban). |
| `evolution_signals` | Sinais de evolução monitorados. |
| `pipeline_runs` | Cada execução de pipeline disparada. |
| `pipeline_logs` | Log por agente que alimenta o live log do frontend. |

Recriar o schema do zero (apaga os dados):

```bash
docker compose down -v && docker compose up -d
```
