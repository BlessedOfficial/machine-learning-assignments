"""Rerank retrieval candidates and log scores before vs after."""

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from config import (
    LOG_RERANK_SCORES,
    MMR_LAMBDA,
    RERANKER_MODE,
    RERANKER_MODEL,
    RERANK_LOG_PATH,
    RERANKER_LLM_MODEL,
    RETRIEVAL_TOP_K,
)
from embeddings.client import EmbeddingClient
from reranker.client import RerankerClient
from reranker.llm_reranker import LLMReranker
from reranker.mmr import mmr_select


@dataclass
class RerankScoreLog:
    chunk_id: str
    rank_before: int
    score_before: float
    rank_after: int | None = None
    score_after: float | None = None


@dataclass
class RerankResult:
    hits: list[dict]
    mode: str
    query: str
    candidate_count: int
    top_k: int
    score_log: list[RerankScoreLog] = field(default_factory=list)


def _snapshot_scores(candidates: list[dict]) -> dict[str, tuple[int, float]]:
    return {
        hit["chunk_id"]: (rank, float(hit.get("score", 0.0)))
        for rank, hit in enumerate(candidates, start=1)
    }


def _build_score_log(
    before: dict[str, tuple[int, float]],
    after: list[dict],
) -> list[RerankScoreLog]:
    after_map = {
        hit["chunk_id"]: (rank, float(hit.get("rerank_score", hit.get("score", 0.0))))
        for rank, hit in enumerate(after, start=1)
    }

    logs: list[RerankScoreLog] = []
    for chunk_id, (rank_before, score_before) in sorted(
        before.items(), key=lambda item: item[1][0]
    ):
        rank_after, score_after = after_map.get(chunk_id, (None, None))
        logs.append(
            RerankScoreLog(
                chunk_id=chunk_id,
                rank_before=rank_before,
                score_before=score_before,
                rank_after=rank_after,
                score_after=score_after,
            )
        )
    return logs


def _cross_encoder_rerank(
    query: str, candidates: list[dict], top_k: int
) -> list[dict]:
    reranker = RerankerClient(model_name=RERANKER_MODEL)
    ranked = reranker.rerank(query, candidates, top_k=top_k)
    for hit in ranked:
        hit["score"] = hit["rerank_score"]
        hit["reranker"] = "cross_encoder"
    return ranked


def _llm_rerank(query: str, candidates: list[dict], top_k: int) -> list[dict]:
    reranker = LLMReranker(model=RERANKER_LLM_MODEL)
    ranked = reranker.rerank(query, candidates, top_k=top_k)
    for hit in ranked:
        hit["score"] = hit["rerank_score"]
        hit["reranker"] = "llm"
    return ranked


def _mmr_rerank(
    query: str,
    candidates: list[dict],
    top_k: int,
    embedding_client: EmbeddingClient | None = None,
) -> list[dict]:
    client = embedding_client or EmbeddingClient()
    query_vec = client.embed_query(query)
    doc_texts = [c["text"] for c in candidates]
    doc_vecs = client.embed(doc_texts)

    selected_indices = mmr_select(
        query_vec,
        doc_vecs,
        top_k=min(top_k, len(candidates)),
        lambda_mult=MMR_LAMBDA,
    )

    ranked: list[dict] = []
    for rank, idx in enumerate(selected_indices, start=1):
        hit = {**candidates[idx]}
        # MMR relevance component for logging (query-doc cosine)
        q = query_vec / (np.linalg.norm(query_vec) + 1e-9)
        d = doc_vecs[idx] / (np.linalg.norm(doc_vecs[idx]) + 1e-9)
        mmr_score = float(np.dot(q, d))
        hit["rerank_score"] = mmr_score
        hit["score"] = mmr_score
        hit["reranker"] = "mmr"
        ranked.append(hit)
    return ranked


def rerank_candidates(
    query: str,
    candidates: list[dict],
    top_k: int | None = None,
    mode: str | None = None,
) -> RerankResult:
    if not candidates:
        return RerankResult(
            hits=[],
            mode=mode or RERANKER_MODE,
            query=query,
            candidate_count=0,
            top_k=top_k or RETRIEVAL_TOP_K,
        )

    final_k = min(top_k or RETRIEVAL_TOP_K, len(candidates))
    rerank_mode = (mode or RERANKER_MODE).lower()
    before = _snapshot_scores(candidates)

    if rerank_mode == "none":
        after = candidates[:final_k]
        for hit in after:
            hit["reranker"] = "none"
    elif rerank_mode == "cross_encoder":
        after = _cross_encoder_rerank(query, candidates, top_k=final_k)
    elif rerank_mode == "llm":
        after = _llm_rerank(query, candidates, top_k=final_k)
    elif rerank_mode == "mmr":
        after = _mmr_rerank(query, candidates, top_k=final_k)
    else:
        raise ValueError(
            f"Unknown RERANKER_MODE={rerank_mode!r}. "
            "Use cross_encoder, llm, mmr, or none."
        )

    score_log = _build_score_log(before, after)
    return RerankResult(
        hits=after,
        mode=rerank_mode,
        query=query,
        candidate_count=len(candidates),
        top_k=final_k,
        score_log=score_log,
    )


def log_rerank_result(result: RerankResult, *, print_table: bool | None = None) -> None:
    should_print = LOG_RERANK_SCORES if print_table is None else print_table
    if not should_print and not RERANK_LOG_PATH:
        return

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "query": result.query,
        "mode": result.mode,
        "candidate_count": result.candidate_count,
        "top_k": result.top_k,
        "scores": [asdict(entry) for entry in result.score_log],
    }

    if RERANK_LOG_PATH:
        log_path = Path(RERANK_LOG_PATH)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload) + "\n")

    if should_print:
        print(
            f"\nRerank ({result.mode}): {result.candidate_count} candidates -> "
            f"top {result.top_k}\n"
        )
        print(
            f"{'chunk_id':<42} | {'rank_before':>11} | {'score_before':>12} | "
            f"{'rank_after':>10} | {'score_after':>11}"
        )
        print("-" * 96)
        for entry in result.score_log:
            rank_after = str(entry.rank_after) if entry.rank_after is not None else "-"
            score_after = (
                f"{entry.score_after:.4f}"
                if entry.score_after is not None
                else "-"
            )
            print(
                f"{entry.chunk_id:<42} | {entry.rank_before:>11} | "
                f"{entry.score_before:>12.4f} | {rank_after:>10} | {score_after:>11}"
            )
        print()
