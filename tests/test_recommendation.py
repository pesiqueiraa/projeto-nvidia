"""Testes do Recommendation Agent — offline e determinísticos (puro regras)."""
from agents.recommendation import (
    SCORE_HIGH,
    SCORE_MEDIUM,
    _recomendar,
    _tier,
    recommendation_node,
)


def _chunk(tech, rerank_score, text="trecho sobre a tecnologia", url=None):
    return {
        "tech": tech, "url": url or f"https://x/{tech}", "text": text,
        "chunk_index": 0, "vector_score": 0.3, "rerank_score": rerank_score,
    }


# --- regras puras ---------------------------------------------------------

def test_tier_segue_as_faixas():
    assert _tier(SCORE_HIGH) == "high"
    assert _tier(SCORE_MEDIUM) == "medium"
    assert _tier(SCORE_MEDIUM - 0.01) == "low"


def test_recomendar_ordena_por_relevancia_e_corta_top_k():
    chunks = [
        _chunk("A", 0.10), _chunk("B", 0.80), _chunk("C", 0.50), _chunk("D", 0.30),
    ]
    rec = _recomendar("Acme", "AI-native", chunks)
    techs = [t.tech for t in rec.technologies]
    assert techs == ["B", "C", "D"]          # top 3 por score, em ordem
    assert rec.overall_confidence == "high"  # melhor tech (B=0.80) é high


def test_recomendar_agrupa_por_tech_pelo_melhor_score():
    # mesma tech em dois chunks -> fica o maior rerank_score
    chunks = [_chunk("NIM", 0.20), _chunk("NIM", 0.70)]
    rec = _recomendar("Acme", "AI-native", chunks)
    assert len(rec.technologies) == 1
    assert rec.technologies[0].relevance_score == 0.70
    assert rec.technologies[0].confidence == "high"


def test_recomendar_non_ai_rebaixa_confianca_e_sinaliza():
    chunks = [_chunk("NIM", 0.90)]  # score alto, mas a startup é Non-AI
    rec = _recomendar("Padaria", "Non-AI", chunks)
    assert rec.overall_confidence == "low"           # rebaixado apesar do 0.90
    assert any("Non-AI" in n for n in rec.notes)
    assert rec.technologies[0].confidence == "high"  # a tech em si segue alta


def test_recomendar_sem_chunks_retorna_vazio_com_nota():
    rec = _recomendar("Acme", "AI-native", [])
    assert rec.technologies == []
    assert rec.overall_confidence == "low"
    assert rec.notes and "sem contexto" in rec.notes[0]


def test_recomendacao_carrega_citacao():
    rec = _recomendar("Acme", "AI-enabled", [_chunk("Triton", 0.60, url="https://nv/triton")])
    assert rec.technologies[0].url == "https://nv/triton"


# --- nó do grafo ----------------------------------------------------------

def _validated(name, label):
    return {
        "classified": {
            "startup": {"name": name, "extraction_basis": "content"},
            "label": label, "rationale": "x", "confidence": "high",
        },
        "validation_confidence": "high", "issues": [],
    }


def test_node_junta_label_do_validated_com_contexto_do_rag():
    state = {
        "validated_startups": [_validated("Aegro", "AI-native")],
        "rag_contexts": [{"name": "Aegro", "query": "...", "chunks": [_chunk("NeMo", 0.6)]}],
    }
    out = recommendation_node(state)
    rec = out["recommendations"][0]
    assert rec["name"] == "Aegro"
    assert rec["label"] == "AI-native"           # veio do validated_startups
    assert rec["technologies"][0]["tech"] == "NeMo"
    assert "1/1" in out["messages"][0][1]


def test_node_label_desconhecido_assume_non_ai():
    # contexto RAG sem startup correspondente no validated -> Non-AI conservador
    state = {
        "validated_startups": [],
        "rag_contexts": [{"name": "Fantasma", "query": "...", "chunks": [_chunk("NIM", 0.9)]}],
    }
    out = recommendation_node(state)
    rec = out["recommendations"][0]
    assert rec["label"] == "Non-AI"
    assert rec["overall_confidence"] == "low"


def test_node_sem_contextos_nao_quebra():
    out = recommendation_node({"validated_startups": [], "rag_contexts": []})
    assert out["recommendations"] == []
