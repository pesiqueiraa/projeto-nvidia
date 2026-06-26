"""Testes do Briefing Agent — offline e determinísticos (puro template)."""
from agents.briefing import _render_briefing, briefing_node


def _validated(name, label="AI-native", **startup_fields):
    startup = {
        "name": name, "description": "assistente jurídico com LLM próprio",
        "sector": "legaltech", "stage": "seed", "funding": "R$ 2M",
        "tech_stack": ["Python"], "ai_signals": ["LLM próprio"],
        "extraction_basis": "content",
    }
    startup.update(startup_fields)
    return {
        "classified": {
            "startup": startup, "label": label,
            "rationale": "usa LLM próprio como núcleo", "confidence": "high",
        },
        "validation_confidence": "high", "issues": [],
    }


def _rec(name, label="AI-native", techs=None, overall="medium", notes=None):
    return {
        "name": name, "label": label,
        "technologies": techs if techs is not None else [{
            "tech": "NeMo Guardrails", "url": "https://nv/guardrails",
            "relevance_score": 0.402, "confidence": "medium",
            "snippet": "rails de segurança para LLMs",
        }],
        "overall_confidence": overall, "notes": notes or [],
    }


def test_briefing_inclui_secoes_e_dados():
    md = _render_briefing(_rec("ChatJurix"), _validated("ChatJurix"))
    assert "# Briefing executivo — ChatJurix" in md
    assert "## Classificação de maturidade de IA" in md
    assert "**AI-native**" in md
    assert "legaltech" in md
    assert "## Stack NVIDIA recomendada" in md
    assert "## Sinal de confiança" in md


def test_briefing_traz_citacao_da_tecnologia():
    md = _render_briefing(_rec("ChatJurix"), _validated("ChatJurix"))
    assert "NeMo Guardrails" in md
    assert "https://nv/guardrails" in md           # citação (proveniência)
    assert "rails de segurança para LLMs" in md    # snippet


def test_briefing_sem_tecnologias_avisa():
    md = _render_briefing(_rec("Vazia", techs=[]), _validated("Vazia"))
    assert "Nenhuma tecnologia NVIDIA com fit suficiente" in md


def test_briefing_inclui_notas_da_recomendacao():
    rec = _rec("Padaria", label="Non-AI", overall="low",
               notes=["Non-AI: recomendação especulativa"])
    md = _render_briefing(rec, _validated("Padaria", label="Non-AI"))
    assert "Non-AI: recomendação especulativa" in md


def test_briefing_sem_validated_nao_quebra():
    # recomendação sem validated correspondente -> ainda gera o relatório
    md = _render_briefing(_rec("Fantasma"), None)
    assert "# Briefing executivo — Fantasma" in md
    assert "indisponível" in md  # sinal de confiança marca a validação ausente


def test_briefing_node_gera_um_relatorio_por_recomendacao():
    state = {
        "validated_startups": [_validated("ChatJurix"), _validated("Aegro")],
        "recommendations": [_rec("ChatJurix"), _rec("Aegro")],
    }
    out = briefing_node(state)
    assert len(out["briefings"]) == 2
    nomes = {b["name"] for b in out["briefings"]}
    assert nomes == {"ChatJurix", "Aegro"}
    assert all("markdown" in b and b["markdown"] for b in out["briefings"])
    assert "2 relatórios" in out["messages"][0][1]


def test_briefing_node_sem_recomendacoes_nao_quebra():
    out = briefing_node({"validated_startups": [], "recommendations": []})
    assert out["briefings"] == []
