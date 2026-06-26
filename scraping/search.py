"""Busca web do site oficial de uma startup (seam trocável nos testes).

Várias fontes (wow.ac, openstartups.net, anjosdobrasil.net) descobrem apenas o
NOME da startup, sem link. Sem o site oficial não há conteúdo para o Extractor
qualificar. Este módulo fecha essa lacuna: dado um nome, faz uma busca web e
devolve a URL mais provável do site oficial — o "Grupo B" de enriquecimento que
o latitud já entregava de graça.

Decisões de design:
  - DuckDuckGo HTML (`html.duckduckgo.com`): endpoint de busca SEM chave de API,
    adequado ao volume pequeno do projeto (poucas startups por fonte). Mantém o
    sistema funcional sem depender de uma SERP API paga.
  - Costura (seam): a chamada de rede fica isolada em `_fetch_search_html`, que
    os testes trocam por um HTML salvo — sem rede, igual ao `fetch_static`.
  - HEURÍSTICA conservadora: descarta agregadores/redes sociais/notícias
    (LinkedIn, Crunchbase, Wikipedia, portais) e fica com o primeiro resultado
    "limpo". É um sinal cru — o Extractor confirma/normaliza depois. Errar o
    site é tratado como "sem conteúdo" (degrada para o caminho metadata), nunca
    derruba o pipeline.
"""
from urllib.parse import parse_qs, unquote, urlencode, urlparse

from bs4 import BeautifulSoup
from loguru import logger

from scraping.fetch import fetch_dynamic

DDG_URL = "https://html.duckduckgo.com/html/"
# Hosts que NÃO são o site oficial da startup — agregadores, redes, notícias.
_NOISE_HOSTS = (
    "duckduckgo", "google", "bing", "linkedin", "facebook", "instagram",
    "twitter", "x.com", "youtube", "crunchbase", "wikipedia", "glassdoor",
    "reclameaqui", "medium", "github", "gov.br", "globo.com", "uol.com",
    "exame.com", "startse", "abstartups", "play.google", "apps.apple",
    "startupintros", "distrito.me", "cnpj", "econodata", "apontador",
    "pitchbook", "owler", "zoominfo", "tracxn", "f6s", "dealroom",
)


def _fetch_search_html(query: str) -> str:
    """Faz a busca num NAVEGADOR real (scrapling) e devolve o HTML cru.

    Por que navegador e não HTTP puro: o DDG serve uma página "anomaly"
    (anti-bot) para requests simples — o fetcher dinâmico (patchright) passa.
    Costura (seam): trocada por HTML salvo nos testes.
    """
    url = f"{DDG_URL}?{urlencode({'q': query})}"
    return fetch_dynamic(url).html_content


def _decode_href(href: str) -> str:
    """Resolve o redirect do DDG (//duckduckgo.com/l/?uddg=<url>) -> URL real."""
    if "uddg=" in href:
        qs = parse_qs(urlparse(href).query)
        if "uddg" in qs:
            return unquote(qs["uddg"][0])
    return href


def search_official_site(name: str, hint: str | None = None) -> str | None:
    """Devolve a URL provável do site oficial da startup, ou None.

    `hint` (ex.: o setor) ajuda a desambiguar nomes comuns. Qualquer falha de
    rede/parsing vira None — o enricher trata como "sem conteúdo".
    """
    if not name.strip():
        return None

    query = " ".join(p for p in (name, hint, "startup") if p)
    try:
        html = _fetch_search_html(query)
    except Exception as e:  # rede/timeout/HTTP — degrada para None
        logger.warning("search: falha ao buscar '{}': {}", name, e)
        return None

    soup = BeautifulSoup(html, "html.parser")
    for a in soup.select("a.result__a"):
        url = _decode_href(a.get("href", ""))
        host = urlparse(url).netloc.lower()
        if not host or any(ruido in host for ruido in _NOISE_HOSTS):
            continue
        logger.info("search: '{}' -> {}", name, url)
        return url
    return None
