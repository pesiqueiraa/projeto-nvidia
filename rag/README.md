# `rag/` — RAG NVIDIA com reranking (Entregável 3)

Base de conhecimento sobre tecnologias NVIDIA (NIM, NeMo, Triton, RAPIDS…)
com recuperação híbrida e **citações de fonte**.

## Pipelines (ux.md §7.4)

**Ingestão:** documentos NVIDIA → trafilatura → chunking (512 tokens,
overlap 64) → embeddings → **Qdrant**.

**Consulta:** busca vetorial (Qdrant) + busca lexical (**BM25**) →
fusão **RRF** → **Cohere Rerank v3** → top-K com citações → LLM.

## Dica de aprendizado (CLAUDE.md)

Implemente **primeiro sem reranking**, meça a qualidade, **depois** adicione
o Cohere Rerank e compare. É o que consolida por que o reranking importa.

## O que aprendi
> _(preencher: chunking semântico, RRF, antes/depois do reranking…)_
