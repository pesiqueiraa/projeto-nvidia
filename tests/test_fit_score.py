"""Testes do Fit Score Agent — offline e determinísticos (puro regras)."""
from agents.fit_score import (
    TIER_ALTO,
    TIER_MEDIO,
    _compute,
    _tier,
    fit_score_node,
)


def test_tier_segue_os_cortes():
    assert _tier(TIER_ALTO) == "alto"
    assert _tier(TIER_MEDIO) == "médio"
    assert _tier(TIER_MEDIO - 1) == "baixo"


def test_ai_native_com_bom_fit_e_alta_confianca_pontua_alto():
    fs = _compute("Top", "AI-native", "high", "high", best_fit=0.60)
    # maturidade 1.0, fit 1.0, evidência 1.0 -> 100
    assert fs.score == 100
    assert fs.tier == "alto"


def test_non_ai_pontua_baixo():
    fs = _compute("Padaria", "Non-AI", "high", "high", best_fit=0.0)
    # maturidade 0.1*0.4=0.04, fit 0, evidência 1.0*0.25=0.25 -> 29
    assert fs.score < TIER_MEDIO
    assert fs.tier == "baixo"


def test_confianca_baixa_reduz_o_score():
    alto = _compute("A", "AI-native", "high", "high", best_fit=0.60)
    baixo = _compute("B", "AI-native", "low", "low", best_fit=0.60)
    assert baixo.score < alto.score  # mesma maturidade/fit, evidência tempera


def test_fit_normaliza_no_cap():
    # best_fit acima do FIT_CAP não passa de 1.0 (não estoura o componente)
    fs = _compute("X", "AI-enabled", "high", "high", best_fit=0.95)
    assert fs.breakdown["nvidia_fit"] == 1.0


def test_breakdown_e_rationale_presentes():
    fs = _compute("X", "AI-native", "medium", "high", best_fit=0.30)
    assert set(fs.breakdown) == {"maturity", "nvidia_fit", "evidence"}
    assert "Maturidade" in fs.rationale and "fit NVIDIA" in fs.rationale


# --- nó do grafo ----------------------------------------------------------

def _validated(name, label, class_conf="high", val_conf="high"):
    return {
        "classified": {
            "startup": {"name": name, "extraction_basis": "content"},
            "label": label, "rationale": "x", "confidence": class_conf,
        },
        "validation_confidence": val_conf, "issues": [],
    }


def _rec(name, label, best_fit):
    return {
        "name": name, "label": label, "overall_confidence": "medium", "notes": [],
        "technologies": [{
            "tech": "NIM", "url": "https://x/nim", "relevance_score": best_fit,
            "confidence": "medium", "snippet": "...",
        }],
    }


def test_node_rankeia_por_score_desc():
    state = {
        "validated_startups": [
            _validated("Fraca", "Non-AI"),
            _validated("Forte", "AI-native"),
        ],
        "recommendations": [
            _rec("Fraca", "Non-AI", 0.0),
            _rec("Forte", "AI-native", 0.6),
        ],
    }
    out = fit_score_node(state)
    nomes = [s["name"] for s in out["fit_scores"]]
    assert nomes == ["Forte", "Fraca"]              # ordenado por prioridade
    assert out["fit_scores"][0]["score"] > out["fit_scores"][1]["score"]


def test_node_startup_sem_recomendacao_usa_fit_zero():
    state = {
        "validated_startups": [_validated("SemRec", "AI-enabled")],
        "recommendations": [],  # sem recomendação correspondente
    }
    out = fit_score_node(state)
    fs = out["fit_scores"][0]
    assert fs["breakdown"]["nvidia_fit"] == 0.0


def test_node_sem_startups_nao_quebra():
    out = fit_score_node({"validated_startups": [], "recommendations": []})
    assert out["fit_scores"] == []
