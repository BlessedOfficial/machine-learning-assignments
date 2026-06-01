"""Detailed hybrid retrieval for pipeline console logging."""

from __future__ import annotations

from dataclasses import dataclass, field

from config import (
    RETRIEVAL_CANDIDATE_K,
    RETRIEVAL_TOP_K,
    RRF_K,
    USE_HYBRID_RETRIEVAL,
    USE_RERANKER,
)
from rag.hybrid import reciprocal_rank_fusion
from rag.rerank_pipeline import RerankResult, RerankScoreLog, rerank_candidates
from rag.retriever import get_vector_store, retrieve_sparse


@dataclass
class ScoredChunk:
    rank: int
    chunk_id: str
    score: float


@dataclass
class RetrievalDiagnostics:
    query: str
    candidate_k: int
    top_k: int
    dense: list[ScoredChunk] = field(default_factory=list)
    sparse: list[ScoredChunk] = field(default_factory=list)
    fused: list[ScoredChunk] = field(default_factory=list)
    rerank_mode: str | None = None
    rerank_log: list[RerankScoreLog] = field(default_factory=list)
    final_chunk_ids: list[str] = field(default_factory=list)


def _to_scored(hits: list[dict]) -> list[ScoredChunk]:
    return [
        ScoredChunk(
            rank=index,
            chunk_id=hit["chunk_id"],
            score=float(hit.get("score", 0.0)),
        )
        for index, hit in enumerate(hits, start=1)
    ]


def retrieve_with_diagnostics(
    question: str,
    *,
    top_k: int | None = None,
    candidate_k: int | None = None,
    hybrid: bool | None = None,
    rerank: bool | None = None,
) -> tuple[list[dict], RetrievalDiagnostics]:
    pool_k = candidate_k if candidate_k is not None else RETRIEVAL_CANDIDATE_K
    final_k = top_k if top_k is not None else RETRIEVAL_TOP_K
    use_hybrid = USE_HYBRID_RETRIEVAL if hybrid is None else hybrid
    do_rerank = USE_RERANKER if rerank is None else rerank

    dense_hits = get_vector_store().search(question, k=pool_k)
    sparse_hits = retrieve_sparse(question, k=pool_k) if use_hybrid else []

    if use_hybrid and dense_hits and sparse_hits:
        fused_hits = reciprocal_rank_fusion(
            [dense_hits, sparse_hits],
            rrf_k=RRF_K,
            top_k=pool_k,
        )
    elif dense_hits:
        fused_hits = dense_hits[:pool_k]
    elif sparse_hits:
        fused_hits = sparse_hits[:pool_k]
    else:
        fused_hits = []

    diagnostics = RetrievalDiagnostics(
        query=question,
        candidate_k=pool_k,
        top_k=final_k,
        dense=_to_scored(dense_hits[:pool_k]),
        sparse=_to_scored(sparse_hits[:pool_k]),
        fused=_to_scored(fused_hits),
    )

    if not fused_hits:
        return [], diagnostics

    if do_rerank:
        rerank_result = rerank_candidates(question, fused_hits, top_k=final_k)
        diagnostics.rerank_mode = rerank_result.mode
        diagnostics.rerank_log = rerank_result.score_log
        final_hits = rerank_result.hits
    else:
        final_hits = fused_hits[:final_k]

    diagnostics.final_chunk_ids = [hit["chunk_id"] for hit in final_hits]
    return final_hits, diagnostics
