# `scraping/` — Coleta de dados públicos (Entregável 1)

Scrapers das fontes do CLAUDE.md (Distrito, StartSe, NeoFeed, …). Coletamos
**apenas informação pública e rastreável** (restrição do projeto).

## Estratégia de ferramentas (ux.md §7.3)

| Ferramenta | Quando |
|---|---|
| **BeautifulSoup** | HTML estático simples (começar por aqui — dica do CLAUDE.md). |
| **Playwright** | Sites com JavaScript (Distrito, StartSe, páginas de carreiras). |
| **trafilatura** | Extrair o texto principal de blogs/notícias (remove boilerplate). |
| **Firecrawl** | Extração limpa pronta para chunking no RAG. |
| **Scrapy** | Crawling em escala (Semana 4, se o volume exigir). |

O Scraper Agent roda **assíncrono** (`asyncio`) com **rate limiting por
domínio** para evitar bloqueios. Toda chamada externa tem tratamento de
erro explícito.

## O que aprendi
> _(preencher: contextos de browser do Playwright, trafilatura vs boilerplate…)_
