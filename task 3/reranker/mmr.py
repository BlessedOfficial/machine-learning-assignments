"""Maximal Marginal Relevance (MMR) selection."""

import numpy as np


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))


def mmr_select(
    query_vec: np.ndarray,
    doc_vecs: np.ndarray,
    *,
    top_k: int,
    lambda_mult: float = 0.7,
) -> list[int]:
    """Return indices of docs selected by MMR."""
    if len(doc_vecs) == 0:
        return []

    q = query_vec / (np.linalg.norm(query_vec) + 1e-9)
    docs = doc_vecs / (np.linalg.norm(doc_vecs, axis=1, keepdims=True) + 1e-9)
    relevance = docs @ q

    selected: list[int] = []
    remaining = set(range(len(docs)))

    while remaining and len(selected) < top_k:
        best_idx = None
        best_score = -np.inf
        for idx in remaining:
            if not selected:
                mmr_score = relevance[idx]
            else:
                max_sim = max(_cosine(docs[idx], docs[s]) for s in selected)
                mmr_score = lambda_mult * relevance[idx] - (1 - lambda_mult) * max_sim
            if mmr_score > best_score:
                best_score = mmr_score
                best_idx = idx
        if best_idx is None:
            break
        selected.append(best_idx)
        remaining.remove(best_idx)

    return selected
