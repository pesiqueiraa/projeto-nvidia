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
