"""Testes do Enricher Agent — offline.

Troca `agents.enricher.fetch_static` por uma função que devolve a fixture
parseada; o trafilatura roda de verdade sobre esse HTML (extração é
determinística). Sem rede.
"""
from pathlib import Path

import pytest
from scrapling import Selector

from agents.enricher import enricher_node

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def patch_enricher_fetch(monkeypatch):
    html = (FIXTURES / "startup_page.html").read_text(encoding="utf-8")
    monkeypatch.setattr("agents.enricher.fetch_static", lambda *a, **k: Selector(html))


def test_enricher_preenche_content_de_quem_tem_url(patch_enricher_fetch):
    state = {"raw_startups": [
        {"name": "Salvy", "source": "latitud.com",
         "source_url": "https://www.latitud.com/portfolio",
         "detail_url": "https://salvy.com.br"},
    ]}
    out = enricher_node(state)
    salvy = out["raw_startups"][0]

    assert salvy["content"] is not None
    # conteúdo principal presente; trafilatura tirou o boilerplate do rodapé
    assert "telefonia móvel para empresas" in salvy["content"]
    assert "Todos os direitos reservados" not in salvy["content"]


def test_enricher_ignora_quem_nao_tem_url(patch_enricher_fetch):
    state = {"raw_startups": [
        {"name": "Aegro", "source": "wow.ac",
         "source_url": "https://www.wow.ac/portfolio"},  # sem detail_url
    ]}
    out = enricher_node(state)

    assert out["raw_startups"][0].get("content") is None
    assert "0/0" in out["messages"][0][1]


def test_enricher_nao_muta_o_estado_original(patch_enricher_fetch):
    original = {"name": "Salvy", "source": "latitud.com",
                "source_url": "https://www.latitud.com/portfolio",
                "detail_url": "https://salvy.com.br"}
    enricher_node({"raw_startups": [original]})

    # o dict original do estado não foi alterado (cópia rasa no nó)
    assert "content" not in original
