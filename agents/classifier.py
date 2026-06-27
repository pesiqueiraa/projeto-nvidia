"""Startup Classifier Agent — quinta estação do grafo.

O Extractor entrega StructuredStartup (com `ai_signals` — as evidências
textuais de IA). O Classifier lê esse retrato e rotula cada startup em três
categorias, que orientam toda a abordagem comercial do Inception:

  - AI-native : IA é o NÚCLEO do produto — sem IA, ele não existe (modelos
                próprios, IA como diferencial central).
  - AI-enabled: usa IA como FEATURE de apoio, mas o core do negócio é outro.
  - Non-AI    : sem evidência de uso de IA.

Decisões de design (espelham o Extractor, já aprovado):
  - Uma chamada de LLM POR STARTUP: erro isolado por item, contexto focado.
    Batching fica como otimização futura.
  - `extraction_basis == "metadata"` => SEM LLM: startup sem conteúdo coletado
    não tem texto a julgar. Rotula provisoriamente como Non-AI/low — conservador
    (não afirma IA sem evidência) e sinaliza ao evidence_validator/loop de
    re-scrape que deve revisitar.
  - Erro POR STARTUP: uma classificação que falha vira fallback Non-AI/low +
    log, não derruba as demais.

`confidence` aqui mede a FORÇA DA EVIDÊNCIA TEXTUAL para o rótulo. O Evidence
Validator (à frente) é outro eixo: corrobora a confiabilidade das FONTES.
"""
from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage
from loguru import logger
from pydantic import BaseModel

from agents.extractor import StructuredStartup
from agents.state import RadarState
from core.llm import get_llm

# Rótulos que o LLM atribui quando HÁ conteúdo para julgar.
LabelLLM = Literal["AI-native", "AI-enabled", "Non-AI"]
# Rótulos possíveis na SAÍDA do nó: + "Indeterminado" para quando não houve
# conteúdo coletado (metadata) ou a classificação falhou. Honestidade > falso
# Non-AI: "não conseguimos ler o site" não é a mesma coisa que "não usa IA".
Label = Literal["AI-native", "AI-enabled", "Non-AI", "Indeterminado"]
Confidence = Literal["high", "medium", "low"]

SYSTEM_PROMPT = """Você é o Classifier do NVISION. Dado o retrato estruturado \
de uma startup brasileira, classifique a maturidade de IA dela em UMA destas \
categorias:

- "AI-native": IA é o NÚCLEO do produto — sem IA o produto não existiria \
(modelos próprios, IA como diferencial central do negócio).
- "AI-enabled": a startup USA IA como recurso de apoio/feature, mas o core do \
negócio é outro (ex.: um ERP que ganhou um assistente).
- "Non-AI": não há evidência de uso ou desenvolvimento de IA.

Baseie-se SOBRETUDO em `ai_signals` (evidências textuais), apoiado por \
description e tech_stack. Não invente evidência que não esteja no retrato.

Devolva também:
- `rationale`: uma a duas frases justificando o rótulo, citando os sinais que \
você usou.
- `confidence`: força da evidência textual para esse rótulo — "high" (sinais \
claros e diretos), "medium" (sinais indiretos ou parciais), "low" (evidência \
fraca ou ambígua).
"""


class _ClassificationResult(BaseModel):
    """O que o LLM decide. `name`/dados ficam fora: pertencem ao nó."""

    label: LabelLLM
    rationale: str
    confidence: Confidence


class ClassifiedStartup(BaseModel):
    """Startup rotulada — saída do Classifier. Aninha o StructuredStartup que
    entrou, para que recommendation/briefing tenham tudo num objeto só."""

    startup: StructuredStartup
    label: Label
    rationale: str
    confidence: Confidence


def _provisorio(startup: StructuredStartup, rationale: str) -> ClassifiedStartup:
    """Classificação SEM LLM quando não dá para julgar: "Indeterminado"/low.
    Usada quando não há conteúdo (metadata) ou a chamada falhou. Não afirma IA
    sem texto, mas TAMBÉM não afirma Non-AI: só não foi possível determinar."""
    return ClassifiedStartup(
        startup=startup, label="Indeterminado", rationale=rationale, confidence="low"
    )


def _classificar(structured_llm, startup: StructuredStartup) -> _ClassificationResult:
    """Uma chamada de LLM para uma startup. `structured_llm` já vem com
    `with_structured_output(_ClassificationResult)` aplicado."""
    retrato = startup.model_dump_json(indent=2)
    prompt = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"Retrato estruturado da startup:\n{retrato}"),
    ]
    return structured_llm.invoke(prompt)


def classifier_node(state: RadarState) -> dict:
    """Nó 5 do grafo: rotula cada startup estruturada em AI-native/enabled/Non-AI."""
    extracted = state.get("extracted_startups", [])

    classificadas: list[ClassifiedStartup] = []
    contagem: dict[str, int] = {
        "AI-native": 0, "AI-enabled": 0, "Non-AI": 0, "Indeterminado": 0,
    }
    # Instanciado preguiçosamente: startups só-metadata nem tocam o LLM.
    structured_llm = None

    for item in extracted:
        startup = StructuredStartup(**item)

        if startup.extraction_basis == "metadata":
            resultado = _provisorio(
                startup, "sem conteúdo coletado; classificação provisória"
            )
            classificadas.append(resultado)
            contagem[resultado.label] += 1
            continue

        try:
            if structured_llm is None:
                structured_llm = get_llm().with_structured_output(_ClassificationResult)
            r = _classificar(structured_llm, startup)
            resultado = ClassifiedStartup(
                startup=startup,
                label=r.label,
                rationale=r.rationale,
                confidence=r.confidence,
            )
        except Exception:  # uma startup não pode derrubar as outras
            logger.exception("classifier falhou em {}", startup.name)
            resultado = _provisorio(startup, "falha na classificação; rótulo provisório")

        classificadas.append(resultado)
        contagem[resultado.label] += 1

    return {
        "classified_startups": [c.model_dump() for c in classificadas],
        "messages": [
            (
                "ai",
                f"[classifier] {len(classificadas)} classificadas "
                f"({contagem['AI-native']} AI-native, "
                f"{contagem['AI-enabled']} AI-enabled, "
                f"{contagem['Non-AI']} Non-AI, "
                f"{contagem['Indeterminado']} indeterminado)",
            )
        ],
    }
