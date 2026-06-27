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
    # best_fit já é o fit de produto normalizado (0..1). 1.0 = fit cheio.
    fs = _compute("Top", "AI-native", "high", "high", best_fit=1.0)
    # maturidade 1.0, fit 1.0, evidência 1.0 -> 100
    assert fs.score == 100
    assert fs.tier == "alto"


def test_non_ai_sem_fit_pontua_baixo():
    fs = _compute("Padaria", "Non-AI", "high", "high", best_fit=0.0)
    # maturidade 0.30*0.30=0.09, fit 0, evidência 1.0*0.25=0.25 -> 34
    assert fs.score < TIER_MEDIO
    assert fs.tier == "baixo"


def test_abrir_o_fit_non_ai_com_bom_produto_sobe():
    # "Abrir o fit": um Non-AI data-heavy com ótimo fit de produto não fica no chão.
    sem_fit = _compute("A", "Non-AI", "high", "high", best_fit=0.0)
    com_fit = _compute("B", "Non-AI", "high", "high", best_fit=0.8)
    assert com_fit.score > sem_fit.score
    assert com_fit.score >= TIER_MEDIO  # passa de 'baixo' graças ao produto


def test_confianca_baixa_reduz_o_score():
    alto = _compute("A", "AI-native", "high", "high", best_fit=1.0)
    baixo = _compute("B", "AI-native", "low", "low", best_fit=1.0)
    assert baixo.score < alto.score  # mesma maturidade/fit, evidência tempera


def test_fit_normaliza_no_teto():
    # best_fit acima de 1.0 é clampado (não estoura o componente)
    fs = _compute("X", "AI-enabled", "high", "high", best_fit=1.5)
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


def _rec(name, label, best_fit_100):
    # best_fit_100: fit de produto em 0..100 (como o catálogo entrega).
    return {
        "name": name, "label": label, "overall_confidence": "medium", "notes": [],
        "technologies": [{
            "tech": "NIM", "url": "https://x/nim", "summary": "...",
            "fit": best_fit_100, "confidence": "medium", "matched_signals": [],
            "relevance_score": 0.0, "growth": "...", "snippet": "",
        }],
    }


def test_node_rankeia_por_score_desc():
    state = {
        "validated_startups": [
            _validated("Fraca", "Non-AI"),
            _validated("Forte", "AI-native"),
        ],
        "recommendations": [
            _rec("Fraca", "Non-AI", 0),
            _rec("Forte", "AI-native", 60),
        ],
    }
    out = fit_score_node(state)
    nomes = [s["name"] for s in out["fit_scores"]]
    assert nomes == ["Forte", "Fraca"]              # ordenado por prioridade
    assert out["fit_scores"][0]["score"] > out["fit_scores"][1]["score"]


def test_node_usa_o_melhor_fit_de_produto():
    state = {
        "validated_startups": [_validated("Multi", "AI-native")],
        "recommendations": [{
            "name": "Multi", "label": "AI-native", "overall_confidence": "high",
            "notes": [],
            "technologies": [
                {"tech": "A", "fit": 30, "confidence": "low", "url": "u",
                 "summary": "", "matched_signals": [], "relevance_score": 0,
                 "growth": "", "snippet": ""},
                {"tech": "B", "fit": 80, "confidence": "high", "url": "u",
                 "summary": "", "matched_signals": [], "relevance_score": 0,
                 "growth": "", "snippet": ""},
            ],
        }],
    }
    out = fit_score_node(state)
    assert out["fit_scores"][0]["breakdown"]["nvidia_fit"] == 0.8  # max(30,80)/100


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
