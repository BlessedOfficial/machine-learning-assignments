from config import (
    RETRIEVAL_CANDIDATE_K,
    RETRIEVAL_MIN_SCORE,
    RETRIEVAL_TOP_K,
    RRF_K,
    USE_HYBRID_RETRIEVAL,
    USE_RERANKER,
)
from rag.hybrid import reciprocal_rank_fusion
from rag.rerank_pipeline import RerankResult, log_rerank_result, rerank_candidates
from rag.sparse_index import get_sparse_retriever
from vector_store.chroma_client import ChromaVectorStore

_store: ChromaVectorStore | None = None


def get_vector_store() -> ChromaVectorStore:
    global _store
    if _store is None:
        _store = ChromaVectorStore()
    return _store


def retrieve_dense(
    question: str,
    k: int,
    min_score: float | None = None,
) -> list[dict]:
    threshold = min_score if min_score is not None else RETRIEVAL_MIN_SCORE
    hits = get_vector_store().search(question, k=k)
    if threshold <= 0:
        return hits
    return [hit for hit in hits if hit["score"] >= threshold]


def retrieve_sparse(question: str, k: int) -> list[dict]:
    return get_sparse_retriever().search(question, k=k)


def retrieve_hybrid(
    question: str,
    k: int | None = None,
    candidate_k: int | None = None,
) -> list[dict]:
    final_k = k if k is not None else RETRIEVAL_TOP_K
    pool_k = candidate_k if candidate_k is not None else RETRIEVAL_CANDIDATE_K

    dense_hits = get_vector_store().search(question, k=pool_k)
    sparse_hits = retrieve_sparse(question, k=pool_k)

    if not dense_hits and not sparse_hits:
        return []
    if not sparse_hits:
        return dense_hits[:final_k]
    if not dense_hits:
        return sparse_hits[:final_k]

    return reciprocal_rank_fusion(
        [dense_hits, sparse_hits],
        rrf_k=RRF_K,
        top_k=final_k,
    )


def retrieve_candidates(
    question: str,
    candidate_k: int | None = None,
    hybrid: bool | None = None,
) -> list[dict]:
    """Fetch fused hybrid candidates before reranking."""
    pool_k = candidate_k if candidate_k is not None else RETRIEVAL_CANDIDATE_K
    use_hybrid = USE_HYBRID_RETRIEVAL if hybrid is None else hybrid

    if use_hybrid:
        return retrieve_hybrid(question, k=pool_k, candidate_k=pool_k)
    return retrieve_dense(question, k=pool_k, min_score=0)


def retrieve_with_rerank(
    question: str,
    k: int | None = None,
    candidate_k: int | None = None,
    hybrid: bool | None = None,
    rerank: bool | None = None,
    rerank_mode: str | None = None,
) -> tuple[list[dict], RerankResult | None]:
    do_rerank = USE_RERANKER if rerank is None else rerank
    top_k = k if k is not None else RETRIEVAL_TOP_K

    if do_rerank:
        candidates = retrieve_candidates(
            question, candidate_k=candidate_k, hybrid=hybrid
        )
        result = rerank_candidates(
            question, candidates, top_k=top_k, mode=rerank_mode
        )
        log_rerank_result(result)
        return result.hits, result

    hits = retrieve(question, k=top_k, hybrid=hybrid, rerank=False)
    return hits, None


def retrieve(
    question: str,
    k: int | None = None,
    min_score: float | None = None,
    hybrid: bool | None = None,
    rerank: bool | None = None,
) -> list[dict]:
    do_rerank = USE_RERANKER if rerank is None else rerank
    if do_rerank:
        hits, _ = retrieve_with_rerank(
            question, k=k, hybrid=hybrid, rerank=True
        )
        return hits

    use_hybrid = USE_HYBRID_RETRIEVAL if hybrid is None else hybrid
    top_k = k if k is not None else RETRIEVAL_TOP_K

    if use_hybrid:
        return retrieve_hybrid(question, k=top_k)

    return retrieve_dense(question, k=top_k, min_score=min_score)


def format_context(hits: list[dict]) -> str:
    if not hits:
        return ""

    parts: list[str] = []
    for index, hit in enumerate(hits, start=1):
        metadata = hit.get("metadata") or {}
        source_file = metadata.get("source_file") or "unknown"
        policy_id = metadata.get("policy_id") or ""
        section = metadata.get("section") or ""
        page = metadata.get("page") or ""
        url = metadata.get("url") or ""
        chunk_id = hit["chunk_id"]

        citation_line = (
            f"[{index}] Citation ID: `{chunk_id}`"
        )
        if policy_id:
            citation_line += f" | Policy: {policy_id}"
        if section:
            citation_line += f" | {section}"
        if page:
            citation_line += f" | page {page}"
        citation_line += f"\n    File: {source_file}"
        if url:
            citation_line += f" | URL: {url}"
        sources = hit.get("retrieval_sources")
        if sources:
            citation_line += f"\n    Matched via: {', '.join(sources)}"

        parts.append(f"{citation_line}\n{hit['text']}")
    return "Retrieved AI.Inc internal excerpts:\n\n" + "\n\n".join(parts)


def format_citations(hits: list[dict]) -> list[dict]:
    """Structured citation objects for UI or logging."""
    citations: list[dict] = []
    for index, hit in enumerate(hits, start=1):
        metadata = hit.get("metadata") or {}
        citations.append(
            {
                "index": index,
                "chunk_id": hit.get("chunk_id"),
                "source_file": metadata.get("source_file"),
                "policy_id": metadata.get("policy_id"),
                "section": metadata.get("section"),
                "page": metadata.get("page"),
                "url": metadata.get("url"),
                "score": hit.get("score"),
                "retrieval_sources": hit.get("retrieval_sources"),
            }
        )
    return citations


def build_rag_user_message(question: str, hits: list[dict]) -> str:
    context = format_context(hits)
    if not context:
        return (
            f"Employee question: {question}\n\n"
            "No internal excerpts were retrieved. "
            "Do not invent facts. State that you don't have enough information "
            "or use the formal out-of-scope decline."
        )

    allowed_ids = ", ".join(f"`{hit['chunk_id']}`" for hit in hits)
    return (
        f"{context}\n\n"
        f"Allowed citation IDs: {allowed_ids}\n\n"
        f"Employee question: {question}\n\n"
        "Answer using ONLY the excerpts above.\n"
        "- Cite every factual claim with the chunk Citation ID in backticks "
        "(e.g. [`pto-and-leave-policy#loc-001`]).\n"
        "- Optionally end with **Sources:** listing chunk IDs used.\n"
        "- If a part of the question is not covered, say explicitly: "
        "\"I don't have enough information on <topic> in the retrieved excerpts.\"\n"
        "- Do NOT state any fact without a chunk ID citation unless noting missing info."
    )