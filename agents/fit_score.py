"""Fit Score Agent — o DIFERENCIAL do NVISION (Entregável 6).

Transforma todo o diagnóstico do pipeline num único número acionável: o **Fit
Score com o Inception** (0–100) de cada startup, para o gestor PRIORIZAR quem
abordar primeiro. Não é mais um rótulo — é um ranking objetivo.

Por que baseado em REGRAS (sem LLM):
  - Um score de priorização precisa ser TRANSPARENTE e AUDITÁVEL: o gestor tem
    de poder justificar por que a startup A vem antes da B. Pesos explícitos e
    um breakdown por componente entregam isso; um LLM seria uma caixa-preta.
  - Determinístico e testável offline (mesma filosofia do evidence_validator e
    do recommendation — CLAUDE.md "regras explícitas primeiro").

A fórmula combina três eixos que o Inception valoriza, cada um normalizado em
0..1 e ponderado:
  1. MATURIDADE de IA (40%) — Inception é sobre startups AI-native.
  2. FIT com a stack NVIDIA (35%) — força do melhor match (rerank do Cohere).
  3. CONFIANÇA das evidências (25%) — tempera o score: diagnóstico frágil não
     deve inflar a prioridade (sinalizar incerteza — CLAUDE.md).
"""
from typing import Literal

from loguru import logger
from pydantic import BaseModel

from agents.state import RadarState

Tier = Literal["alto", "médio", "baixo"]

# --- Mapas e pesos das regras (a "constituição" do score, explícita) ---
# "Abrir o fit": o Non-AI não é mais quase zerado (0.1 -> 0.30). O fit por
# produto (catalog) já modula a maturidade por produto, então aqui a maturidade
# pesa MENOS e o fit NVIDIA pesa MAIS — evita penalizar duas vezes e deixa um
# bom fit de produto carregar a prioridade mesmo sem ser AI-native.
MATURITY_MAP = {"AI-native": 1.0, "AI-enabled": 0.65, "Non-AI": 0.30}
CONF_MAP = {"high": 1.0, "medium": 0.6, "low": 0.2}

W_MATURITY = 0.30
W_FIT = 0.45
W_EVIDENCE = 0.25

# Cortes de faixa para leitura rápida (cor na interface).
TIER_ALTO = 70
TIER_MEDIO = 40


class FitScore(BaseModel):
    """O Fit Score de uma startup, com o breakdown que o justifica."""

    name: str
    label: str
    score: int           # 0..100
    tier: Tier
    breakdown: dict       # contribuição de cada eixo (0..1), para auditoria
    rationale: str


def _tier(score: int) -> Tier:
    if score >= TIER_ALTO:
        return "alto"
    if score >= TIER_MEDIO:
        return "médio"
    return "baixo"


def _compute(name: str, label: str, class_conf: str, val_conf: str,
             best_fit: float) -> FitScore:
    """Aplica a fórmula a UMA startup. Cada eixo é explícito e auditável.

    `best_fit`: melhor fit produto×empresa do catálogo, em 0..1 (já é o fit de
    produto normalizado — não há mais cap de rerank a aplicar aqui)."""
    maturity = MATURITY_MAP.get(label, 0.3)
    fit = max(0.0, min(best_fit, 1.0))
    # Evidência = média da confiança da classificação e da validação de fontes.
    evidence = (CONF_MAP.get(class_conf, 0.2) + CONF_MAP.get(val_conf, 0.2)) / 2

    score01 = W_MATURITY * maturity + W_FIT * fit + W_EVIDENCE * evidence
    score = round(score01 * 100)

    return FitScore(
        name=name,
        label=label,
        score=score,
        tier=_tier(score),
        breakdown={
            "maturity": round(maturity, 2),
            "nvidia_fit": round(fit, 2),
            "evidence": round(evidence, 2),
        },
        rationale=(
            f"Maturidade {label} ({maturity:.2f}) · fit NVIDIA {fit:.2f} "
            f"(melhor produto {round(fit * 100)}/100) · evidências {evidence:.2f} "
            f"(classif. {class_conf} / validação {val_conf})"
        ),
    )


def fit_score_node(state: RadarState) -> dict:
    """Nó do grafo: calcula o Fit Score de cada startup e as RANKEIA."""
    validadas = state.get("validated_startups", [])
    recs_por_nome = {r["name"]: r for r in state.get("recommendations", [])}

    scores: list[FitScore] = []
    for v in validadas:
        startup = v["classified"]["startup"]
        name = startup["name"]
        label = v["classified"]["label"]
        class_conf = v["classified"]["confidence"]
        val_conf = v["validation_confidence"]

        rec = recs_por_nome.get(name)
        # Melhor fit produto×empresa (0..100 no catálogo) -> normaliza para 0..1.
        best_fit = (
            max((t["fit"] for t in rec["technologies"]), default=0) / 100
            if rec else 0.0
        )
        scores.append(_compute(name, label, class_conf, val_conf, best_fit))

    # Ordena por score desc: o topo é a fila de abordagem do gestor.
    scores.sort(key=lambda s: s.score, reverse=True)

    logger.info("fit_score: {} startups pontuadas e rankeadas", len(scores))
    return {
        "fit_scores": [s.model_dump() for s in scores],
        "messages": [
            ("ai", f"[fit_score] {len(scores)} startups pontuadas (0–100) e rankeadas")
        ],
    }
