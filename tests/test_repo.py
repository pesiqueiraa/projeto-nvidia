"""Testes da persistência — só a lógica PURA (sem banco).

`rows_from_state` mapeia o estado final do grafo para as linhas da tabela
`startups`. As funções que tocam o Postgres (save/list) são validadas
manualmente contra o Supabase, não em testes unitários offline.
"""
from database.repo import rows_from_state


def _state():
    return {
        "query": "fintechs de IA",
        "classified_startups": [
            {"startup": {"name": "ChatJurix", "sector": "legaltech",
                         "stage": "seed", "funding": "R$ 3M"},
             "label": "AI-native", "rationale": "x", "confidence": "high"},
            {"startup": {"name": "LogiBox", "sector": "logtech",
                         "stage": None, "funding": None},
             "label": "Non-AI", "rationale": "x", "confidence": "low"},
        ],
        "fit_scores": [
            {"name": "ChatJurix", "score": 88},
            {"name": "LogiBox", "score": 30},
        ],
    }


def test_rows_from_state_junta_classificacao_e_fit():
    rows = rows_from_state(_state())
    chat = next(r for r in rows if r["name"] == "ChatJurix")

    assert chat["classification"] == "AI-native"
    assert chat["sector"] == "legaltech"
    assert chat["fit_score"] == 88
    assert chat["confidence"] == 1.0  # high -> 1.0


def test_rows_from_state_mapeia_confianca_para_numerico():
    rows = rows_from_state(_state())
    logi = next(r for r in rows if r["name"] == "LogiBox")
    assert logi["confidence"] == 0.2  # low -> 0.2
    assert logi["fit_score"] == 30


def test_rows_from_state_sem_fit_correspondente_fica_none():
    state = {
        "classified_startups": [
            {"startup": {"name": "SemFit", "sector": "x"},
             "label": "Non-AI", "rationale": "y", "confidence": "medium"},
        ],
        "fit_scores": [],  # nenhum fit
    }
    rows = rows_from_state(state)
    assert rows[0]["fit_score"] is None
    assert rows[0]["confidence"] == 0.6  # medium -> 0.6


def test_rows_from_state_vazio():
    assert rows_from_state({}) == []
