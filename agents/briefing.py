"""Briefing Agent — nona e última estação do pipeline.

Junta tudo que as estações anteriores produziram sobre cada startup —
identidade, classificação de maturidade de IA, validação de evidências e a
stack NVIDIA recomendada (com citações) — num RELATÓRIO EXECUTIVO em markdown,
pronto para o Gerente de Startups & VCs usar na abordagem comercial.

Por que DETERMINÍSTICO (sem LLM) e não gerado por modelo:
  - O briefing é o ARTEFATO FINAL e precisa ser FIEL: cada número, rótulo e
    citação tem de bater com o que o pipeline apurou. Gerar o relatório por LLM
    abriria espaço para alucinação justo no produto entregue — risco que não se
    justifica aqui. Montamos o markdown a partir dos dados estruturados.
  - Sinalizar SEMPRE o nível de confiança é exigência do projeto (CLAUDE.md):
    o briefing consolida os três sinais (evidência textual, validação de
    fontes, fit NVIDIA) num só lugar.
  Uma camada de NARRATIVA via LLM (resumo executivo em prosa por cima dos
  fatos) é o aprimoramento natural seguinte — análogo à versão LLM do
  Recommendation Agent.
"""
from loguru import logger
from pydantic import BaseModel

from agents.state import RadarState


class Briefing(BaseModel):
    """Relatório executivo final de uma startup."""

    name: str
    label: str
    markdown: str


def _fmt(valor) -> str:
    """Formata um campo opcional para exibição (— quando ausente)."""
    if not valor:
        return "—"
    if isinstance(valor, list):
        return ", ".join(valor)
    return str(valor)


def _render_briefing(rec: dict, validated: dict | None,
                     fit: dict | None = None) -> str:
    """Monta o markdown do briefing a partir dos dados estruturados.

    `rec` é um StartupRecommendation serializado; `validated` é o
    ValidatedStartup correspondente (ou None); `fit` é o FitScore (ou None).
    """
    name = rec["name"]
    linhas: list[str] = [f"# Briefing executivo — {name}", ""]

    # Fit Score com o Inception em destaque, logo no topo (o diferencial).
    if fit is not None:
        linhas += [
            f"**Fit Score Inception: {fit['score']}/100** "
            f"(prioridade {fit['tier']})",
            "",
        ]

    # --- Identidade + classificação (vêm do validated_startups) ---
    if validated is not None:
        startup = validated["classified"]["startup"]
        classified = validated["classified"]
        linhas += [
            f"**Setor:** {_fmt(startup.get('sector'))} · "
            f"**Estágio:** {_fmt(startup.get('stage'))} · "
            f"**Funding:** {_fmt(startup.get('funding'))}",
            "",
            _fmt(startup.get("description")),
            "",
            "## Classificação de maturidade de IA",
            f"**{classified['label']}** "
            f"(confiança da evidência: {classified['confidence']})",
            "",
            classified.get("rationale", ""),
            "",
            "## Validação de evidências",
            f"Confiança das fontes: **{validated['validation_confidence']}**",
            f"Ressalvas: {_fmt(validated.get('issues')) or 'nenhuma'}",
            "",
        ]

    # --- Stack NVIDIA recomendada (vem do recommendation) ---
    linhas.append(
        f"## Stack NVIDIA recomendada (confiança geral: "
        f"{rec['overall_confidence']})"
    )
    if rec["technologies"]:
        for t in rec["technologies"]:
            linhas += [
                f"- **{t['tech']}** — confiança {t['confidence']}",
                f"  {t.get('summary', '')}",
                f"  _Como ajuda a crescer:_ {t.get('growth', '')}",
            ]
            if t.get("matched_signals"):
                linhas.append(f"  Sinais: {', '.join(t['matched_signals'])}")
            if t.get("snippet"):
                linhas.append(f"  > {t['snippet']}")
            linhas.append(f"  Fonte: {t['url']}")
    else:
        linhas.append("_Nenhuma tecnologia NVIDIA com fit suficiente identificada._")
    for nota in rec.get("notes", []):
        linhas.append(f"- _Nota: {nota}_")
    linhas.append("")

    # --- Sinal de confiança consolidado (exigência do projeto) ---
    label = rec["label"]
    val_conf = validated["validation_confidence"] if validated else "indisponível"
    linhas += [
        "## Sinal de confiança",
        f"Diagnóstico **{label}** · evidências **{val_conf}** · "
        f"fit NVIDIA **{rec['overall_confidence']}**.",
    ]

    return "\n".join(linhas)


def briefing_node(state: RadarState) -> dict:
    """Nó 9 do grafo: gera o relatório executivo final por startup."""
    recomendacoes = state.get("recommendations", [])
    validadas = state.get("validated_startups", [])
    # Junta o validated (identidade/classificação) e o fit score à
    # recomendação, ambos keyed por nome.
    val_por_nome = {
        v["classified"]["startup"]["name"]: v for v in validadas
    }
    fit_por_nome = {f["name"]: f for f in state.get("fit_scores", [])}

    briefings: list[Briefing] = []
    for rec in recomendacoes:
        validated = val_por_nome.get(rec["name"])
        fit = fit_por_nome.get(rec["name"])
        markdown = _render_briefing(rec, validated, fit)
        briefings.append(Briefing(name=rec["name"], label=rec["label"], markdown=markdown))

    logger.info("briefing: {} relatórios gerados", len(briefings))
    return {
        "briefings": [b.model_dump() for b in briefings],
        "messages": [
            ("ai", f"[briefing] {len(briefings)} relatórios executivos gerados")
        ],
    }
