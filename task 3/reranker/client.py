from config import RERANKER_MODEL


class RerankerClient:
    def __init__(self, model_name=None):
        self.model_name = model_name or RERANKER_MODEL
        self._model = None

    @property
    def model(self):
        if self._model is None:
            from sentence_transformers import CrossEncoder

            self._model = CrossEncoder(self.model_name)
        return self._model

    def rerank(self, query: str, candidates: list[dict], top_k: int = 5) -> list[dict]:
        if not candidates:
            return []

        pairs = [(query, candidate["text"]) for candidate in candidates]
        scores = self.model.predict(pairs)

        ranked = []
        for candidate, score in zip(candidates, scores):
            ranked.append(
            {
                **candidate,
                "retrieval_score": candidate.get("score"),
                "rerank_score": float(score),
            }
        )

        ranked.sort(key=lambda item: item["rerank_score"], reverse=True)
        return ranked[:top_k]
