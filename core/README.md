# `core/` — Configuração e serviços compartilhados

Código que vários módulos precisam e que não pertence a um agente
específico. Não está na estrutura "sugerida" do CLAUDE.md, mas evita
duplicação (config e LLM apareceriam em todo agente).

| Arquivo | O quê |
|---|---|
| `config.py` | `settings` tipado (pydantic-settings) lido do `.env` uma vez. |
| `llm.py` | `get_llm()` — abstrai o provider de LLM via `LLM_PROVIDER`. |

## Abstração de LLM — por quê

O provider ainda não foi fixado (ux.md §7.7). Todos os agentes chamam
`get_llm()`; trocar Anthropic↔OpenAI é **uma variável de ambiente**, sem
tocar em nenhum agente. A escolha é explícita (um `if` por provider) de
propósito — para o time enxergar o que cada um exige.
