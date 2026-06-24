"""Enricher Agent — terceira estação do grafo.

O Scraper *descobre* startups (nome + às vezes um link); o Enricher *coleta o
conteúdo* de cada uma. Para toda startup que tenha `detail_url`, visita a
página e extrai o TEXTO PRINCIPAL com o trafilatura (remove menu/rodapé/anúncio
— só o conteúdo). É essa matéria-prima que o Extractor e o Classifier vão usar
para estruturar e decidir AI-native vs. não.

Decisões de design:
  - `fetch_static` (HTTP puro): o site oficial costuma ser estático e é o
    fetcher mais barato. Se uma página exigir JS, dá para escalar depois.
  - Erro POR STARTUP: um site fora do ar vira `content=None`, não derruba os
    demais (mesma disciplina do Scraper — CLAUDE.md).
  - Naturalmente educado com servidores: cada `detail_url` é um domínio
    diferente (o site da própria startup), então não martelamos ninguém.

Startups sem `detail_url` passam intactas (content=None) — cobri-las exigiria
descobrir o site oficial via busca, o que ficou para um passo futuro.
"""
import trafilatura
from loguru import logger

from agents.state import RadarState
from scraping.fetch import ScrapeError, fetch_static


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
    """Nó 3 do grafo: enriquece com conteúdo quem tem detail_url."""
    raw_startups = state.get("raw_startups", [])

    enriquecidas = 0
    atualizadas = []
    for rs in raw_startups:
        rs = dict(rs)  # cópia rasa — não muta o dict original do estado
        url = rs.get("detail_url")
        if url and not rs.get("content"):
            texto = _extrair_conteudo(url)
            if texto:
                rs["content"] = texto
                enriquecidas += 1
        atualizadas.append(rs)

    total_com_url = sum(1 for rs in raw_startups if rs.get("detail_url"))
    return {
        "raw_startups": atualizadas,
        "messages": [
            (
                "ai",
                f"[enricher] {enriquecidas}/{total_com_url} startups com detail_url "
                f"enriquecidas (de {len(raw_startups)} no total)",
            )
        ],
    }
