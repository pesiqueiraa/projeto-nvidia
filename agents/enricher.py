"""Enricher Agent — terceira estação do grafo.

O Scraper *descobre* startups (nome + às vezes um link); o Enricher *coleta o
conteúdo* de cada uma. Para toda startup, garante um `detail_url` (descobrindo o
site oficial via BUSCA WEB quando a fonte só deu o nome), visita a página e
extrai o TEXTO PRINCIPAL com o trafilatura (remove menu/rodapé/anúncio — só o
conteúdo). É essa matéria-prima que o Extractor e o Classifier vão usar.

Decisões de design:
  - DESCOBERTA do site oficial: fontes como wow.ac/openstartups só dão o nome.
    Sem site, não há conteúdo para qualificar. `search_official_site` (DuckDuckGo)
    resolve o nome para a URL provável; o link descoberto é guardado em
    `detail_url` (vira proveniência depois).
  - `fetch_static` (HTTP puro): o site oficial costuma ser estático e é o
    fetcher mais barato. Se uma página exigir JS, dá para escalar depois.
  - Erro POR STARTUP: um site fora do ar / não encontrado vira `content=None`,
    não derruba os demais (mesma disciplina do Scraper — CLAUDE.md).
  - Naturalmente educado com servidores: cada `detail_url` é um domínio
    diferente (o site da própria startup), então não martelamos ninguém.
"""
import trafilatura
from loguru import logger

from agents.state import RadarState
from scraping.fetch import ScrapeError, fetch_static
from scraping.search import search_official_site


def _extrair_conteudo(url: str) -> str | None:
    """Busca a página e devolve o texto principal, ou None se não der."""
    try:
        html = fetch_static(url).html_content
    except ScrapeError:
        logger.warning("enricher: falha ao buscar {}", url)
        return None
    # trafilatura devolve None quando não acha conteúdo principal aproveitável.
    return trafilatura.extract(html)


def enricher_node(state: RadarState) -> dict:
    """Nó 3 do grafo: garante detail_url (via busca) e coleta o conteúdo."""
    raw_startups = state.get("raw_startups", [])

    enriquecidas = 0
    descobertos = 0
    atualizadas = []
    for rs in raw_startups:
        rs = dict(rs)  # cópia rasa — não muta o dict original do estado
        if not rs.get("content"):
            url = rs.get("detail_url")
            # Fonte só deu o nome? Descobre o site oficial via busca web.
            if not url:
                url = search_official_site(rs.get("name", ""), rs.get("sector"))
                if url:
                    rs["detail_url"] = url  # guarda o site descoberto
                    descobertos += 1
            if url:
                texto = _extrair_conteudo(url)
                if texto:
                    rs["content"] = texto
                    enriquecidas += 1
        atualizadas.append(rs)

    return {
        "raw_startups": atualizadas,
        "messages": [
            (
                "ai",
                f"[enricher] {enriquecidas}/{len(raw_startups)} enriquecidas "
                f"({descobertos} sites descobertos via busca)",
            )
        ],
    }
