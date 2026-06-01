"""Reciprocal rank fusion for dense + sparse retrieval."""


def reciprocal_rank_fusion(
    result_lists: list[list[dict]],
    *,
    rrf_k: int = 60,
    top_k: int = 5,
) -> list[dict]:
    scores: dict[str, float] = {}
    docs: dict[str, dict] = {}
    sources: dict[str, set[str]] = {}

    for list_index, results in enumerate(result_lists):
        source = "dense" if list_index == 0 else "bm25"
        for rank, hit in enumerate(results, start=1):
            chunk_id = hit["chunk_id"]
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (rrf_k + rank)
            if chunk_id not in docs:
                docs[chunk_id] = hit
            sources.setdefault(chunk_id, set()).add(source)

    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)[:top_k]
    fused: list[dict] = []
    for chunk_id, rrf_score in ranked:
        hit = {**docs[chunk_id], "score": rrf_score, "rrf_score": rrf_score}
        hit["retrieval_sources"] = sorted(sources.get(chunk_id, set()))
        fused.append(hit)
    return fused
