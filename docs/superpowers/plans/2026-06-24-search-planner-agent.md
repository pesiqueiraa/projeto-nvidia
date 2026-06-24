# Search Planner Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Substituir o stub `plan_node` por um Search Planner Agent real, que usa um LLM com saída estruturada para gerar termos de busca e escolher fontes dentre um catálogo fixo de 14 portais brasileiros de startups.

**Architecture:** Novo módulo `agents/search_planner.py` define o nó (`search_planner_node`), o schema de saída (`SearchPlan`, Pydantic) e o catálogo de fontes (`SOURCE_CATALOG`). `agents/graph.py` troca o nó `plan` (stub) por `search_planner` (real) e mantém `echo` como segunda estação temporária. Todos os testes usam um LLM falso injetado via `monkeypatch`, sem chamada de rede nem chave de API.

**Tech Stack:** LangGraph (`StateGraph`), LangChain core (`with_structured_output`, `SystemMessage`/`HumanMessage`), Pydantic v2, loguru, pytest + monkeypatch.

## Global Constraints

- Python 3.12 fixo, gerenciado via `uv` (`uv run pytest`, `uv run python -m ...`).
- Nenhuma dependência nova: `langchain-core`, `pydantic`, `loguru` já estão em `pyproject.toml`.
- Testes não podem depender de chave de API real nem de rede (invariante já documentada em `tests/test_smoke.py`).
- Um conceito por arquivo em `agents/` (padrão já estabelecido: `state.py`, `graph.py`).
- Tratamento de erro explícito — nunca descartar silenciosamente uma fonte inválida sem logar.

---

### Task 1: Search Planner Agent — schema, catálogo e nó

**Files:**
- Create: `agents/search_planner.py`
- Create: `tests/conftest.py`
- Create: `tests/test_search_planner.py`

**Interfaces:**
- Produces: `agents.search_planner.SOURCE_CATALOG: list[str]` — catálogo fixo de 14 domínios.
- Produces: `agents.search_planner.SearchPlan` — Pydantic `BaseModel` com campos `search_terms: list[str]`, `sources: list[str]`, `reasoning: str`.
- Produces: `agents.search_planner.search_planner_node(state: RadarState) -> dict` — nó do grafo (assinatura de 1 argumento, compatível com LangGraph). Devolve `{"search_terms": ..., "sources": ..., "messages": [...]}`.
- Consumes: `agents.state.RadarState` (já existe, sem alteração). `core.llm.get_llm` (já existe).

- [ ] **Step 1: Criar `tests/conftest.py` com o LLM falso e fixtures compartilhadas**

```python
"""Fixtures compartilhadas dos testes. Um LLM falso (`FakeLLM`) substitui o
LLM real nos testes — sem chamada de rede, sem chave de API, resultado
sempre determinístico."""
import pytest

from agents.search_planner import SearchPlan


class FakeStructuredLLM:
    """Devolve sempre o mesmo SearchPlan, imitando `.invoke()` de um LLM real."""

    def __init__(self, fixed_plan: SearchPlan):
        self._fixed_plan = fixed_plan

    def invoke(self, prompt):
        return self._fixed_plan


class FakeLLM:
    """Imita a interface mínima de um BaseChatModel: `.with_structured_output(schema)`."""

    def __init__(self, fixed_plan: SearchPlan):
        self._fixed_plan = fixed_plan

    def with_structured_output(self, schema):
        return FakeStructuredLLM(self._fixed_plan)


@pytest.fixture
def fixed_search_plan() -> SearchPlan:
    return SearchPlan(
        search_terms=["fintech", "ia generativa", "open finance"],
        sources=["distrito.me", "startse.com"],
        reasoning="consulta menciona fintechs de IA, priorizando portais gerais",
    )


@pytest.fixture
def fake_llm(fixed_search_plan: SearchPlan) -> FakeLLM:
    return FakeLLM(fixed_search_plan)


@pytest.fixture
def patch_get_llm(monkeypatch, fake_llm: FakeLLM) -> FakeLLM:
    """Troca `agents.search_planner.get_llm` pelo FakeLLM durante o teste."""
    monkeypatch.setattr("agents.search_planner.get_llm", lambda: fake_llm)
    return fake_llm
```

- [ ] **Step 2: Escrever os testes que falham (módulo `agents.search_planner` ainda não existe)**

```python
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
    fixed_search_plan.sources = ["distrito.me", "site-fora-do-catalogo.com"]

    resultado = search_planner_node({"query": "qualquer coisa"})

    assert resultado["sources"] == ["distrito.me"]
    assert "site-fora-do-catalogo.com" not in resultado["sources"]
    assert "distrito.me" in SOURCE_CATALOG  # catálogo real contém a fonte válida usada no teste
```

- [ ] **Step 3: Rodar os testes e confirmar que falham**

Run: `uv run pytest tests/test_search_planner.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'agents.search_planner'`

- [ ] **Step 4: Implementar `agents/search_planner.py`**

```python
"""Search Planner Agent — primeira estação real do grafo (substitui o stub
`plan_node`). Recebe a `query` do gestor, chama um LLM com saída estruturada
e devolve termos de busca expandidos + fontes priorizadas dentre o catálogo
fixo (Grupo A — ver artefatos/backend.md §5).

Saída estruturada via `with_structured_output`: o LLM é forçado a devolver
algo que já bate com o schema `SearchPlan`, em vez de texto livre que
precisaria de parsing manual.
"""
from langchain_core.messages import HumanMessage, SystemMessage
from loguru import logger
from pydantic import BaseModel

from agents.state import RadarState
from core.llm import get_llm

# Grupo A do catálogo de fontes (artefatos/backend.md §5): portais/agregadores
# fixos, conhecidos de antemão. O Grupo B (sites/blogs oficiais de startups,
# páginas de carreiras, perfis de founders) só existe depois que uma startup
# específica já foi identificada — entra num agente futuro (evidence_validator
# ou extractor).
SOURCE_CATALOG = [
    "startse.com",
    "distrito.me",
    "latitud.com",
    "cubo.network",
    "acestartups.com.br",
    "endeavor.org.br",
    "abstartups.com.br",
    "bossainvest.com",
    "anjosdobrasil.net",
    "darwinstartups.com",
    "liga.ventures",
    "wow.ac",
    "inovativabrasil.com.br",
    "openstartups.net",
]

SYSTEM_PROMPT = """Você é o Search Planner do NVISION, um radar que mapeia \
startups brasileiras AI-native para o programa NVIDIA Inception.

Dada a consulta de um gestor, devolva:
1. `search_terms`: de 3 a 8 termos de busca em português, específicos \
(setor, tecnologia, estágio da startup), que ajudem a encontrar startups \
relevantes para a consulta.
2. `sources`: o subconjunto do catálogo abaixo mais relevante para essa \
consulta (pode ser todo o catálogo, se fizer sentido).
3. `reasoning`: uma frase explicando por que escolheu esses termos e fontes.

Catálogo de fontes permitido (escolha somente entre estas, exatamente como \
escritas):
{catalog}
"""


class SearchPlan(BaseModel):
    """Saída estruturada do LLM — schema que o `with_structured_output` força."""

    search_terms: list[str]
    sources: list[str]
    reasoning: str


def search_planner_node(state: RadarState) -> dict:
    """Nó 1 real do grafo: substitui o stub `plan_node`.

    Assinatura de 1 argumento (compatível com a convenção de nó do
    LangGraph). Chama `get_llm()` em tempo de execução (não no import), o
    que permite trocar essa referência por um LLM falso nos testes via
    `monkeypatch.setattr("agents.search_planner.get_llm", ...)`.
    """
    query = state.get("query", "")

    llm = get_llm()
    structured_llm = llm.with_structured_output(SearchPlan)

    prompt = [
        SystemMessage(content=SYSTEM_PROMPT.format(catalog="\n".join(SOURCE_CATALOG))),
        HumanMessage(content=query),
    ]
    plan: SearchPlan = structured_llm.invoke(prompt)

    fontes_validas = [s for s in plan.sources if s in SOURCE_CATALOG]
    fontes_invalidas = [s for s in plan.sources if s not in SOURCE_CATALOG]
    if fontes_invalidas:
        logger.warning(
            "search_planner sugeriu fontes fora do catálogo, descartando: {}",
            fontes_invalidas,
        )

    return {
        "search_terms": plan.search_terms,
        "sources": fontes_validas,
        "messages": [
            (
                "ai",
                f"[search_planner] {plan.reasoning} | termos: {plan.search_terms} | "
                f"fontes: {fontes_validas}",
            )
        ],
    }
```

- [ ] **Step 5: Rodar os testes e confirmar que passam**

Run: `uv run pytest tests/test_search_planner.py -v`
Expected: PASS (2 testes)

- [ ] **Step 6: Commit**

```bash
git add agents/search_planner.py tests/conftest.py tests/test_search_planner.py
git commit -m "feat: add Search Planner Agent with structured LLM output"
```

---

### Task 2: Encaixar o Search Planner no grafo e atualizar os testes de fumaça existentes

**Files:**
- Modify: `agents/graph.py` (todo o arquivo — remove `plan_node`, importa `search_planner_node`)
- Modify: `tests/test_smoke.py` (`test_graph_runs_two_nodes`, `test_demo_plan_endpoint`)

**Interfaces:**
- Consumes: `agents.search_planner.search_planner_node` (Task 1), `tests/conftest.py` fixtures `patch_get_llm`/`fixed_search_plan` (Task 1).
- Produces: `agents.graph.graph` continua exportado igual hoje (mesmo nome, mesmo `.invoke()`), agora com `search_planner` como primeiro nó em vez de `plan`.

- [ ] **Step 1: Atualizar `tests/test_smoke.py` para esperar o comportamento real (ainda vai falhar, pois `graph.py` não foi alterado)**

```python
"""Testes de fumaça da fundação.

Validam que as peças centrais carregam e conversam, sem depender de chaves
de API nem de bancos no ar (o LLM é falso via `patch_get_llm`).
Rode com: `uv run pytest`
"""
from fastapi.testclient import TestClient

from agents.graph import graph
from api.main import app

client = TestClient(app)


def test_health_ok():
    """O backend sobe e responde no /health."""
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_graph_runs_two_nodes(patch_get_llm, fixed_search_plan):
    """O grafo de 2 nós executa: search_planner (LLM falso) -> echo."""
    final = graph.invoke({"query": "fintechs de IA"})
    # search_planner_node devolve o que o LLM falso produziu
    assert final["search_terms"] == fixed_search_plan.search_terms
    assert final["sources"] == fixed_search_plan.sources
    # os dois nós deixaram rastro em messages (reducer add_messages)
    assert len(final["messages"]) == 2


def test_demo_plan_endpoint(patch_get_llm, fixed_search_plan):
    """O endpoint de demo executa o grafo via HTTP, com LLM falso."""
    resp = client.post("/api/demo/plan", json={"query": "fintechs de IA"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["search_terms"] == fixed_search_plan.search_terms
    assert body["sources"] == fixed_search_plan.sources
```

- [ ] **Step 2: Rodar os testes e confirmar que falham**

Run: `uv run pytest tests/test_smoke.py -v`
Expected: FAIL nas asserções de `search_terms`/`sources` (o `graph.py` ainda roda o stub `plan_node`, que devolve valores diferentes do `fixed_search_plan`)

- [ ] **Step 3: Reescrever `agents/graph.py` para usar o `search_planner_node` real**

```python
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
```

- [ ] **Step 4: Rodar os testes e confirmar que passam**

Run: `uv run pytest tests/test_smoke.py -v`
Expected: PASS (3 testes)

- [ ] **Step 5: Rodar a suíte completa pra garantir que nada quebrou**

Run: `uv run pytest -v`
Expected: PASS (todos os testes — `test_health_ok`, `test_graph_runs_two_nodes`, `test_demo_plan_endpoint`, `test_search_planner_node_returns_llm_plan`, `test_search_planner_node_filters_sources_outside_catalog`)

- [ ] **Step 6: Commit**

```bash
git add agents/graph.py tests/test_smoke.py
git commit -m "feat: wire Search Planner Agent into the graph, replacing the plan_node stub"
```

---

### Task 3: Atualizar a documentação do módulo

**Files:**
- Modify: `agents/README.md`
- Modify: `artefatos/backend.md` (linha do `search_planner` na tabela §3 — marcar como implementado)

- [ ] **Step 1: Atualizar `agents/README.md`**

Substituir a seção "Arquivos atuais" e "Por que começar com 2 nós?" para refletir que `search_planner.py` agora é real, mantendo a tabela de arquivos:

```markdown
## Arquivos atuais

| Arquivo | O quê |
|---|---|
| `state.py` | `RadarState` — o estado tipado que trafega entre os nós. |
| `search_planner.py` | Primeiro agente real: LLM com saída estruturada (`SearchPlan`), escolhe termos de busca e fontes dentre o catálogo fixo. |
| `graph.py` | Grafo de **2 nós** (`search_planner` → `echo`). `echo` ainda é placeholder até o Scraper Agent existir. |

## O que aprendi

- `with_structured_output` força o LLM a devolver algo compatível com um
  schema Pydantic, eliminando parsing manual de texto livre.
- Testar código que chama LLM sem gastar dinheiro/rede: o nó recebe o LLM
  via uma referência de módulo (`get_llm`) que pode ser trocada por um
  `FakeLLM` nos testes via `monkeypatch` — sem mudar a assinatura da função
  nem arriscar conflito com a injeção automática de `config` do LangGraph.
```

- [ ] **Step 2: Atualizar a linha do `search_planner` em `artefatos/backend.md` §3**

Trocar `🔧 design aprovado, a implementar` por `✅ implementado` na tabela de agentes.

- [ ] **Step 3: Commit**

```bash
git add agents/README.md artefatos/backend.md
git commit -m "docs: update agents/README and backend.md after Search Planner implementation"
```

> Nota: `artefatos/backend.md` está no `.gitignore`, então `git add` desse arquivo não terá efeito no commit — é esperado, o arquivo continua só local. O commit real cobre apenas `agents/README.md`.
