import numpy as np
from sentence_transformers import SentenceTransformer

from config import EMBEDDING_MODEL


class EmbeddingClient:
    def __init__(self, model_name=None):
        self.model_name = model_name or EMBEDDING_MODEL
        self._model = None

    @property
    def model(self):
        if self._model is None:
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def embed(self, texts: list[str]) -> np.ndarray:
        return np.array(self.model.encode(texts, convert_to_numpy=True))

    def embed_query(self, query: str) -> np.ndarray:
        return self.embed([query])[0]
