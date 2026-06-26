"""Recommendation Agent — oitava estação do grafo.

O RAG Agent recuperou, por startup, os trechos da base NVIDIA mais relevantes
ao perfil (já reranqueados). Este nó os transforma em uma RECOMENDAÇÃO de stack:
quais tecnologias NVIDIA fazem sentido, com qual confiança e com citação.

Por que baseado em REGRAS (sem LLM) — CLAUDE.md (Entregável 4):
  "estruture a lógica como regras explícitas (if/else) antes de usar o LLM, e
  compare as duas abordagens". Recomendar a partir do score de rerank é o caso
  perfeito: transparente, determinístico, barato e testável offline. Uma versão
  via LLM (que escreve a justificativa de fit em linguagem natural) fica como o
  próximo passo, para comparação.

As regras, explícitas:
  1. Agrupa os trechos por tecnologia (uma tech pode vir em vários chunks);
     fica o MELHOR rerank_score de cada uma + a citação daquele trecho.
  2. Confiança da tech vem de FAIXAS do rerank_score (a lição do Entregável 3:
     o score absoluto do Cohere é um sinal de confiança calibrado).
  3. Non-AI: a fit com a stack NVIDIA de IA é especulativa — a confiança geral
     é REBAIXADA e uma ressalva é anexada (sinalizar incerteza — CLAUDE.md).
  4. Perfil sem contexto recuperado => recomendação vazia, com o motivo.
"""
from typing import Literal

from loguru import logger
from pydantic import BaseModel, Field

from agents.state import RadarState

Confidence = Literal["high", "medium", "low"]

# Quantas tecnologias recomendar por startup (as de maior relevância).
TOP_K_TECHS = 3
# Faixas de confiança a partir do rerank_score do Cohere (0..1).
SCORE_HIGH = 0.50
SCORE_MEDIUM = 0.15


class TechRecommendation(BaseModel):
    """Uma tecnologia NVIDIA recomendada, com confiança e citação."""

    tech: str
    url: str                 # proveniência -> citação no briefing
    relevance_score: float   # melhor rerank_score do Cohere para esta tech
    confidence: Confidence
    snippet: str             # trecho curto que embasou a recomendação


class StartupRecommendation(BaseModel):
    """Recomendação de stack NVIDIA para UMA startup."""

    name: str
    label: str               # AI-native / AI-enabled / Non-AI (orienta a leitura)
    technologies: list[TechRecommendation] = Field(default_factory=list)
    overall_confidence: Confidence = "low"
    notes: list[str] = Field(default_factory=list)


def _tier(score: float) -> Confidence:
    """Mapeia o rerank_score para um nível de confiança (regra explícita)."""
    if score >= SCORE_HIGH:
        return "high"
    if score >= SCORE_MEDIUM:
        return "medium"
    return "low"


def _melhor_por_tech(chunks: list[dict]) -> dict[str, dict]:
    """Agrupa chunks por tech, guardando o de MAIOR rerank_score de cada uma."""
    melhor: dict[str, dict] = {}
    for c in chunks:
        tech = c["tech"]
        if tech not in melhor or c["rerank_score"] > melhor[tech]["rerank_score"]:
            melhor[tech] = c
    return melhor


def _recomendar(name: str, label: str, chunks: list[dict]) -> StartupRecommendation:
    """Aplica as regras de recomendação a UMA startup."""
    if not chunks:
        return StartupRecommendation(
            name=name, label=label,
            notes=["sem contexto NVIDIA recuperado para esta startup"],
        )

    # Regra 1+2: melhor score por tech -> TechRecommendation com confiança.
    melhores = _melhor_por_tech(chunks)
    techs = [
        TechRecommendation(
            tech=c["tech"],
            url=c["url"],
            relevance_score=c["rerank_score"],
            confidence=_tier(c["rerank_score"]),
            snippet=c["text"][:200].strip(),
        )
        for c in melhores.values()
    ]
    techs.sort(key=lambda t: t.relevance_score, reverse=True)
    techs = techs[:TOP_K_TECHS]

    # Confiança geral = a da melhor tech (lista já ordenada).
    overall: Confidence = techs[0].confidence
    notes: list[str] = []

    # Regra 3: Non-AI -> fit especulativa, rebaixa e sinaliza.
    if label == "Non-AI":
        overall = "low"
        notes.append(
            "startup classificada como Non-AI: recomendação de stack NVIDIA de "
            "IA é especulativa (baixa confiança)"
        )

    return StartupRecommendation(
        name=name, label=label, technologies=techs,
        overall_confidence=overall, notes=notes,
    )


def recommendation_node(state: RadarState) -> dict:
    """Nó 8 do grafo: recomenda a stack NVIDIA por startup (por regras)."""
    rag_contexts = state.get("rag_contexts", [])
    validadas = state.get("validated_startups", [])
    # Junta o rótulo (que mora no validated) ao contexto RAG (keyed por nome).
    label_por_nome = {
        v["classified"]["startup"]["name"]: v["classified"]["label"]
        for v in validadas
    }

    recomendacoes: list[StartupRecommendation] = []
    com_recomendacao = 0
    for ctx in rag_contexts:
        name = ctx["name"]
        label = label_por_nome.get(name, "Non-AI")
        rec = _recomendar(name, label, ctx.get("chunks", []))
        recomendacoes.append(rec)
        if rec.technologies:
            com_recomendacao += 1

    logger.info("recommendation: {} startups recomendadas", com_recomendacao)
    return {
        "recommendations": [r.model_dump() for r in recomendacoes],
        "messages": [
            (
                "ai",
                f"[recommendation] {com_recomendacao}/{len(rag_contexts)} startups "
                f"com stack NVIDIA recomendada (top {TOP_K_TECHS} por startup)",
            )
        ],
    }
