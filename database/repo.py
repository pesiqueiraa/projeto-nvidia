"""Camada de persistência das startups qualificadas (Postgres/Supabase).

Fecha a lacuna entre GERAR (o pipeline) e USAR (as páginas Qualificadas/
Analytics): depois de cada execução, as startups classificadas + fit score são
gravadas aqui, e as telas as leem de volta. Sem isso, o resultado do pipeline
viveria só durante a requisição e se perderia.

Decisões de design:
  - `psycopg` direto (sem ORM): expõe o SQL de verdade, alinhado ao objetivo
    didático do projeto (CLAUDE.md). As queries ficam à mostra.
  - UPSERT por `name` (chave natural): re-rodar a mesma busca ATUALIZA a startup
    em vez de duplicar — a lista Qualificadas acumula sem lixo.
  - Persistência RESILIENTE: `persist_pipeline_result` nunca propaga erro de
    banco — o usuário recebe o resultado do pipeline mesmo se a gravação falhar
    (tratamento de erro explícito — CLAUDE.md).
"""
from pathlib import Path

import psycopg
from loguru import logger
from psycopg.rows import dict_row
from psycopg.types.json import Json

from core.config import settings
from core.sectors import bucket_sectors

SCHEMA_PATH = Path(__file__).parent / "schema.sql"
# Confiança categórica (high/medium/low) -> numérico 0..1 para a coluna.
_CONF_NUM = {"high": 1.0, "medium": 0.6, "low": 0.2}


def get_conn() -> psycopg.Connection:
    """Abre uma conexão com o banco configurado em DATABASE_URL."""
    return psycopg.connect(settings.database_url)


def apply_schema() -> None:
    """Aplica o schema.sql (idempotente — tudo é CREATE IF NOT EXISTS)."""
    sql = SCHEMA_PATH.read_text(encoding="utf-8")
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql)
        conn.commit()
    logger.info("repo: schema aplicado em {}", settings.database_url.split("@")[-1])


def rows_from_state(state: dict) -> list[dict]:
    """Converte o estado final do grafo nas linhas da tabela `startups`.

    Junta a classificação (label, confiança, identidade) ao fit score, por nome.
    Função PURA — testável sem banco.
    """
    fit_por_nome = {f["name"]: f for f in state.get("fit_scores", [])}
    rec_por_nome = {r["name"]: r for r in state.get("recommendations", [])}
    brief_por_nome = {b["name"]: b for b in state.get("briefings", [])}
    linhas: list[dict] = []
    for c in state.get("classified_startups", []):
        s = c["startup"]
        fit = fit_por_nome.get(s["name"])
        rec = rec_por_nome.get(s["name"])
        brief = brief_por_nome.get(s["name"])
        linhas.append({
            "name": s["name"],
            "sector": s.get("sector"),
            "stage": s.get("stage"),
            "funding": s.get("funding"),
            "classification": c["label"],
            "confidence": _CONF_NUM.get(c["confidence"], 0.2),
            "fit_score": fit["score"] if fit else None,
            # Detalhe para o dropdown da página Qualificadas:
            "description": s.get("description"),
            "recommendations": rec,                       # rec completo (produtos + fit)
            "briefing": brief["markdown"] if brief else None,
        })
    return linhas


def save_run(query: str) -> int:
    """Registra a execução em pipeline_runs e devolve o id."""
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO pipeline_runs (query, status, completed_at) "
            "VALUES (%s, 'done', now()) RETURNING id",
            (query,),
        )
        run_id = cur.fetchone()[0]
        conn.commit()
        return run_id


def save_startups(linhas: list[dict]) -> int:
    """UPSERT das startups por nome. Retorna quantas foram gravadas."""
    if not linhas:
        return 0
    # `recommendations` é JSONB: o adapter Json() serializa o dict/lista Python.
    # Mantém `rows_from_state` puro (sem psycopg) — o wrap mora só aqui.
    params = [{**l, "recommendations": Json(l.get("recommendations"))} for l in linhas]
    with get_conn() as conn, conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO startups
                (name, sector, stage, funding, classification, confidence,
                 fit_score, description, recommendations, briefing)
            VALUES
                (%(name)s, %(sector)s, %(stage)s, %(funding)s,
                 %(classification)s, %(confidence)s, %(fit_score)s,
                 %(description)s, %(recommendations)s, %(briefing)s)
            ON CONFLICT (name) DO UPDATE SET
                sector          = EXCLUDED.sector,
                stage           = EXCLUDED.stage,
                funding         = EXCLUDED.funding,
                classification  = EXCLUDED.classification,
                confidence      = EXCLUDED.confidence,
                fit_score       = EXCLUDED.fit_score,
                description     = EXCLUDED.description,
                recommendations = EXCLUDED.recommendations,
                briefing        = EXCLUDED.briefing
            """,
            params,
        )
        conn.commit()
        return len(linhas)


def persist_pipeline_result(state: dict) -> int:
    """Salva execução + startups. RESILIENTE: erro de banco vira log + 0, nunca
    derruba o endpoint que chamou o pipeline."""
    try:
        save_run(state.get("query", ""))
        return save_startups(rows_from_state(state))
    except Exception:
        logger.exception("repo: persistência falhou (resultado não foi gravado)")
        return 0


def list_startups(limit: int = 200) -> list[dict]:
    """Lista as startups acumuladas, das de maior fit para as menores."""
    with get_conn() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT name, sector, stage, funding, classification,
                   confidence, fit_score, created_at
            FROM startups
            ORDER BY fit_score DESC NULLS LAST, created_at DESC
            LIMIT %s
            """,
            (limit,),
        )
        return cur.fetchall()


def get_startup(name: str) -> dict | None:
    """Detalhe de UMA startup (dropdown da página Qualificadas): além dos campos
    da lista, traz descrição, produtos NVIDIA recomendados e o briefing. `None`
    se não existir. O JSONB `recommendations` volta já desserializado em dict."""
    with get_conn() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT name, sector, stage, funding, classification, confidence,
                   fit_score, description, recommendations, briefing, created_at
            FROM startups
            WHERE name = %s
            """,
            (name,),
        )
        return cur.fetchone()


def analytics() -> dict:
    """Agregados do ecossistema para a página Analytics — tudo via SQL (GROUP
    BY/AVG/CASE), expondo a mecânica do banco em vez de agregar em Python."""
    with get_conn() as conn, conn.cursor(row_factory=dict_row) as cur:
        # KPIs base
        cur.execute(
            "SELECT count(*)::int AS total, round(avg(fit_score))::int AS avg_fit "
            "FROM startups"
        )
        base = cur.fetchone()

        # Distribuição por maturidade de IA
        cur.execute(
            "SELECT classification, count(*)::int AS count FROM startups "
            "GROUP BY classification ORDER BY count DESC"
        )
        by_classification = cur.fetchall()

        # Top setores — o banco CONTA por string crua (texto livre do Extractor),
        # e o resultado é dobrado numa TAXONOMIA fixa em Python (core/sectors.py):
        # cada setor cru cai num bucket concreto e conhecido (ou "Outros") em vez
        # de cada string virar um setor próprio (o que trazia '—' e jargões soltos
        # como "agtech"). O DB conta; a taxonomia mora num lugar só.
        cur.execute("SELECT sector, count(*)::int AS count FROM startups GROUP BY sector")
        by_sector = bucket_sectors(cur.fetchall())

        # Distribuição por faixa de Fit Score (os mesmos cortes do fit_score)
        cur.execute(
            """
            SELECT CASE WHEN fit_score >= 70 THEN 'alto'
                        WHEN fit_score >= 40 THEN 'médio'
                        ELSE 'baixo' END AS tier,
                   count(*)::int AS count
            FROM startups WHERE fit_score IS NOT NULL
            GROUP BY tier
            """
        )
        by_tier = cur.fetchall()

    return {
        "total": base["total"],
        "avg_fit": base["avg_fit"],
        "by_classification": by_classification,
        "by_sector": by_sector,
        "by_tier": by_tier,
    }
