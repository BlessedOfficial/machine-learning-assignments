from rank_bm25 import BM25Okapi


class SparseRetriever:
    """BM25 keyword retriever over chunk documents."""

    def __init__(self):
        self.documents: list[dict] = []
        self._bm25 = None
        self._tokenized_corpus: list[list[str]] = []

    def add_documents(self, documents: list[dict]) -> None:
        for doc in documents:
            self.documents.append(
                {
                    "chunk_id": doc.get("chunk_id", f"chunk_{len(self.documents)}"),
                    "text": doc["text"],
                    "metadata": doc.get("metadata", {}),
                }
            )

        self._tokenized_corpus = [doc["text"].lower().split() for doc in self.documents]
        self._bm25 = BM25Okapi(self._tokenized_corpus)

    def search(self, query: str, k: int = 5) -> list[dict]:
        if self._bm25 is None or not self.documents:
            return []

        tokenized_query = query.lower().split()
        scores = self._bm25.get_scores(tokenized_query)

        ranked_indices = sorted(
            range(len(scores)), key=lambda idx: scores[idx], reverse=True
        )[:k]

        results = []
        for idx in ranked_indices:
            doc = self.documents[idx]
            results.append(
                {
                    "chunk_id": doc["chunk_id"],
                    "text": doc["text"],
                    "metadata": doc["metadata"],
                    "score": float(scores[idx]),
                }
            )
        return results
