"""Catálogo estruturado de produtos NVIDIA + motor de fit por regras.

Por que este módulo existe (a virada de chave do Entregável 4):
  A versão antiga media "fit" como a SIMILARIDADE SEMÂNTICA entre o texto da
  empresa e os docs da NVIDIA (o rerank do Cohere). Isso respondia "o texto da
  empresa se parece com o do produto?", não "este produto ajuda a empresa a
  crescer?". E como nenhuma startup se descreve no vocabulário da NVIDIA
  ("Triton", "TensorRT-LLM"), o score era estruturalmente baixo para todas.

  Aqui invertemos: cada produto carrega SINAIS DE NECESSIDADE explícitos (o que
  na empresa indica que ela se beneficiaria) e uma ADEQUAÇÃO POR MATURIDADE. O
  fit produto×empresa vira uma regra transparente e auditável; o sinal semântico
  do RAG entra como UM insumo de apoio, não como o juiz.

Decisão "abrir o fit" (escolha do gestor): a maturidade NÃO zera mais Non-AI de
forma cega. Cada produto declara para quais maturidades ele serve — produtos de
DADO/INFRA (RAPIDS, AI Enterprise) pontuam para empresas data-heavy mesmo sem
serem AI-native, enquanto genAI/treino exigem mais maturidade. É o que reflete
onde a NVIDIA de fato ajuda a crescer.

O LLM NÃO pontua aqui (isso é regra). Ele entra depois, no recommendation_node,
só para ESCREVER o "como ajuda a crescer" sobre os produtos que a regra elegeu.
"""
from typing import Literal

from pydantic import BaseModel

from core.sectors import canonical_sector

Confidence = Literal["high", "medium", "low"]

# --- Pesos do fit por regra (a "constituição" do match, explícita) ---
W_SIGNAL = 0.60   # sinais de necessidade no perfil (o sinal mais forte)
W_SECTOR = 0.20   # o setor da empresa bater com o setor-alvo do produto
W_SEM = 0.20      # relevância semântica do RAG (rerank do Cohere) como apoio
SIGNAL_FULL = 2   # nº de gatilhos para o eixo de sinais saturar em 1.0
SEM_CAP = 0.50    # rerank a partir do qual o eixo semântico vale 1.0

TOP_K = 3         # quantos produtos recomendar por empresa
MIN_FIT = 25      # abaixo disto, não recomenda (evita ruído)

# Faixas de confiança a partir do fit final (0..100).
FIT_HIGH = 60
FIT_MEDIUM = 35


class NvidiaProduct(BaseModel):
    """Um produto NVIDIA com os critérios que indicam fit com uma empresa."""

    tech: str                       # casa com o `tech` do corpus (p/ citação)
    url: str
    summary: str                    # o que o produto faz, em uma linha
    triggers: tuple[str, ...]       # substrings que, no perfil, indicam necessidade
    sectors: tuple[str, ...] = ()   # setores canônicos que reforçam o fit
    # Adequação por maturidade: multiplicador 0..1 do fit conforme o rótulo.
    # Produtos de dado/infra sobem o Non-AI (abrir o fit); genAI/treino o reduzem.
    maturity_fit: dict[str, float] = {}
    growth_thesis: str = ""         # "como ajuda a crescer" (fallback sem LLM)


class ProductFit(BaseModel):
    """Resultado do match de UM produto com UMA empresa (auditável)."""

    tech: str
    url: str
    summary: str
    fit: int                        # 0..100
    confidence: Confidence
    matched_signals: list[str]      # quais gatilhos casaram (transparência)
    semantic_score: float           # melhor rerank do RAG p/ esta tech (0 se ausente)
    growth_thesis: str              # tese template; o LLM pode sobrescrever depois


# Multiplicadores de maturidade reutilizáveis por "família" de produto.
_M_GENAI = {"AI-native": 1.0, "AI-enabled": 0.85, "Non-AI": 0.35}
_M_INFER = {"AI-native": 1.0, "AI-enabled": 0.90, "Non-AI": 0.45}
_M_DATA = {"AI-native": 1.0, "AI-enabled": 1.0, "Non-AI": 0.80}   # abre p/ Non-AI
_M_INFRA = {"AI-native": 0.9, "AI-enabled": 0.9, "Non-AI": 0.70}
_M_VERTICAL = {"AI-native": 1.0, "AI-enabled": 0.9, "Non-AI": 0.60}


CATALOG: list[NvidiaProduct] = [
    NvidiaProduct(
        tech="NVIDIA NIM",
        url="https://www.nvidia.com/en-us/ai-data-science/products/nim-microservices/",
        summary="Microsserviços para servir modelos de IA generativa via API, com deploy rápido.",
        triggers=("llm", "genai", "generativ", "inferência", "inference", "deploy",
                  "microserv", "chatbot", "assistente", "rag", "api de modelo"),
        maturity_fit=_M_GENAI,
        growth_thesis="Acelera o lançamento de features de genAI em produção sem montar infra de serving do zero.",
    ),
    NvidiaProduct(
        tech="NVIDIA NeMo",
        url="https://www.nvidia.com/en-us/ai-data-science/products/nemo/",
        summary="Plataforma para treinar e customizar modelos próprios (LLM, fala, visão).",
        triggers=("treina", "fine-tun", "modelo próprio", "modelo proprio", "nlp",
                  "foundation model", "custom model", "llm", "visão computacional"),
        maturity_fit=_M_GENAI,
        growth_thesis="Permite construir modelos proprietários como diferencial competitivo defensável.",
    ),
    NvidiaProduct(
        tech="NVIDIA API Catalog",
        url="https://build.nvidia.com/",
        summary="Catálogo de modelos prontos para prototipar via API antes de hospedar.",
        triggers=("prototip", "poc", "api", "genai", "llm", "experiment"),
        maturity_fit=_M_GENAI,
        growth_thesis="Reduz o tempo de validação de ideias de IA com modelos prontos para testar.",
    ),
    NvidiaProduct(
        tech="TensorRT-LLM",
        url="https://github.com/NVIDIA/TensorRT-LLM",
        summary="Otimização de inferência de LLMs em GPU (latência e custo).",
        triggers=("latência", "latencia", "throughput", "otimiz", "custo de inferência",
                  "inferência", "inference", "serving", "gpu"),
        maturity_fit=_M_INFER,
        growth_thesis="Corta o custo por inferência e melhora a latência, viabilizando escala com margem.",
    ),
    NvidiaProduct(
        tech="Triton Inference Server",
        url="https://developer.nvidia.com/triton-inference-server",
        summary="Servidor para colocar modelos em produção em escala, com múltiplos frameworks.",
        triggers=("serving", "produção", "producao", "deploy", "escala", "latência",
                  "inferência", "inference", "múltiplos modelos", "mlops"),
        maturity_fit=_M_INFER,
        growth_thesis="Padroniza o deploy de modelos em produção, encurtando o caminho do laboratório ao cliente.",
    ),
    NvidiaProduct(
        tech="NeMo Guardrails",
        url="https://github.com/NVIDIA/NeMo-Guardrails",
        summary="Camada de segurança e conformidade para aplicações com LLM.",
        triggers=("compliance", "guardrail", "moderaç", "regulado", "alucina",
                  "segurança", "seguranca", "jurídic", "juridic", "saúde", "financ"),
        maturity_fit=_M_GENAI,
        growth_thesis="Reduz risco regulatório e de marca ao operar LLMs em setores sensíveis.",
    ),
    NvidiaProduct(
        tech="NVIDIA RAPIDS",
        url="https://rapids.ai/",
        summary="Aceleração de pipelines de dados e ML em GPU (cuDF/cuML) sem reescrever o código.",
        triggers=("dados", "data", "etl", "analytics", "big data", "pandas",
                  "scikit", "tabular", "engenharia de dados", "dataframe",
                  "machine learning", "pipeline de dados"),
        sectors=("Finanças", "Varejo & E-commerce", "Logística"),
        maturity_fit=_M_DATA,
        growth_thesis="Acelera 10–50× pipelines de dados/ML existentes sem reescrever pandas/scikit — ganho mesmo sem ser AI-native.",
    ),
    NvidiaProduct(
        tech="NVIDIA AI Enterprise",
        url="https://www.nvidia.com/en-us/data-center/products/ai-enterprise/",
        summary="Suíte enterprise para rodar IA em produção com suporte e governança.",
        triggers=("enterprise", "produção", "producao", "infra", "mlops",
                  "on-premise", "kubernetes", "escala", "governança"),
        maturity_fit=_M_INFRA,
        growth_thesis="Dá governança e suporte para escalar IA em produção com previsibilidade operacional.",
    ),
    NvidiaProduct(
        tech="NVIDIA Riva",
        url="https://developer.nvidia.com/riva",
        summary="IA de fala: reconhecimento (ASR) e síntese (TTS) de voz em tempo real.",
        triggers=("voz", "fala", "speech", "áudio", "audio", "call center",
                  "transcri", "tts", "asr", "atendimento", "ura"),
        maturity_fit=_M_VERTICAL,
        growth_thesis="Automatiza atendimento e canais de voz com transcrição e síntese de qualidade.",
    ),
    NvidiaProduct(
        tech="NVIDIA Omniverse",
        url="https://www.nvidia.com/en-us/omniverse/",
        summary="Simulação 3D e gêmeos digitais para indústria, construção e design.",
        triggers=("3d", "simulaç", "simulation", "digital twin", "gêmeo digital",
                  "render", "manufatur", "construç", "construc", "cad", "indústria"),
        sectors=("Indústria", "Imobiliário/Construção"),
        maturity_fit=_M_VERTICAL,
        growth_thesis="Permite simular processos/produtos antes do físico, reduzindo custo e tempo de iteração.",
    ),
    NvidiaProduct(
        tech="NVIDIA Isaac",
        url="https://developer.nvidia.com/isaac",
        summary="Plataforma de robótica e automação autônoma (simulação + deploy).",
        triggers=("robô", "robo", "robót", "robot", "autônom", "autonom",
                  "manipula", "drone", "agv", "automação"),
        sectors=("Indústria", "Logística"),
        maturity_fit=_M_VERTICAL,
        growth_thesis="Acelera o desenvolvimento de robôs/automação com simulação realista antes do hardware.",
    ),
    NvidiaProduct(
        tech="NVIDIA Clara",
        url="https://www.nvidia.com/en-us/clara/",
        summary="IA para saúde: imagem médica, genômica e fluxos clínicos.",
        triggers=("saúde", "saude", "médic", "medic", "imagem médica", "genom",
                  "radiolog", "hospital", "diagnóstico", "diagnostico", "clínic"),
        sectors=("Saúde",),
        maturity_fit=_M_VERTICAL,
        growth_thesis="Viabiliza produtos clínicos de IA (imagem/genômica) com ferramentas específicas de saúde.",
    ),
    NvidiaProduct(
        tech="NVIDIA Morpheus",
        url="https://developer.nvidia.com/morpheus-cybersecurity",
        summary="IA para cibersegurança: detecção de fraude, anomalia e ameaças em escala.",
        triggers=("cibersegur", "cybersec", "segurança da informação", "fraude",
                  "fraud", "anomal", "ameaça", "threat", "intrus", "phishing"),
        maturity_fit=_M_VERTICAL,
        growth_thesis="Detecta fraude/ameaças em tempo real sobre grandes volumes, reduzindo perdas.",
    ),
]


def _confidence(fit: int) -> Confidence:
    """Confiança do fit a partir do score final (faixas explícitas)."""
    if fit >= FIT_HIGH:
        return "high"
    if fit >= FIT_MEDIUM:
        return "medium"
    return "low"


def _score_one(produto: NvidiaProduct, profile_text: str, sector_canon: str,
               label: str, semantic: float) -> ProductFit:
    """Aplica a regra de fit de UM produto a UMA empresa (tudo auditável)."""
    matched = [t for t in produto.triggers if t in profile_text]
    signal = min(len(matched) / SIGNAL_FULL, 1.0)
    sector = 1.0 if sector_canon in produto.sectors else 0.0
    sem = min(semantic / SEM_CAP, 1.0) if semantic > 0 else 0.0

    need = W_SIGNAL * signal + W_SECTOR * sector + W_SEM * sem
    mult = produto.maturity_fit.get(label, 0.5)
    fit = round(need * mult * 100)

    return ProductFit(
        tech=produto.tech,
        url=produto.url,
        summary=produto.summary,
        fit=fit,
        confidence=_confidence(fit),
        matched_signals=matched,
        semantic_score=round(semantic, 3),
        growth_thesis=produto.growth_thesis,
    )


def score_products(
    profile_text: str,
    sector: str | None,
    label: str,
    semantic_by_tech: dict[str, float] | None = None,
    top_k: int = TOP_K,
    min_fit: int = MIN_FIT,
) -> list[ProductFit]:
    """Pontua TODO o catálogo contra uma empresa e devolve os melhores fits.

    profile_text: texto livre do perfil (description + sinais de IA + stack...).
    sector: setor cru da empresa (mapeado para o canônico internamente).
    label: maturidade (AI-native / AI-enabled / Non-AI) — modula o fit por produto.
    semantic_by_tech: melhor rerank do RAG por tech (sinal de apoio), opcional.

    Retorna os `top_k` produtos com fit >= `min_fit`, ordenados por fit desc.
    """
    texto = (profile_text or "").lower()
    sector_canon = canonical_sector(sector)
    sem_map = semantic_by_tech or {}

    fits = [
        _score_one(p, texto, sector_canon, label, sem_map.get(p.tech, 0.0))
        for p in CATALOG
    ]
    fits = [f for f in fits if f.fit >= min_fit]
    fits.sort(key=lambda f: f.fit, reverse=True)
    return fits[:top_k]
