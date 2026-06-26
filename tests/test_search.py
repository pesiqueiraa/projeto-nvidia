"""Testes da busca do site oficial — offline (HTML do DDG salvo, sem rede)."""
from pathlib import Path

import pytest

from scraping import search
from scraping.search import _decode_href, search_official_site

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def patch_search(monkeypatch):
    html = (FIXTURES / "ddg_results.html").read_text(encoding="utf-8")
    monkeypatch.setattr(search, "_fetch_search_html", lambda *a, **k: html)


def test_decode_href_resolve_redirect_do_ddg():
    href = "//duckduckgo.com/l/?uddg=https%3A%2F%2Fsalvy.com.br&rut=x"
    assert _decode_href(href) == "https://salvy.com.br"


def test_decode_href_passa_url_direta():
    assert _decode_href("https://salvy.com.br") == "https://salvy.com.br"


def test_busca_pula_ruido_e_retorna_site_oficial(patch_search):
    # primeiro resultado é LinkedIn (ruído), depois Crunchbase; o oficial é o do
    # meio (salvy.com.br) — a heurística deve pular os agregadores.
    assert search_official_site("Salvy") == "https://salvy.com.br"


def test_busca_nome_vazio_retorna_none():
    assert search_official_site("   ") is None


def test_busca_falha_de_rede_retorna_none(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("rede caiu")

    monkeypatch.setattr(search, "_fetch_search_html", boom)
    assert search_official_site("Salvy") is None


def test_busca_sem_resultado_limpo_retorna_none(monkeypatch):
    # só ruído -> nenhum candidato sobra
    html = (
        '<a class="result__a" href="https://www.linkedin.com/company/x">x</a>'
        '<a class="result__a" href="https://en.wikipedia.org/wiki/x">x</a>'
    )
    monkeypatch.setattr(search, "_fetch_search_html", lambda *a, **k: html)
    assert search_official_site("x") is None
