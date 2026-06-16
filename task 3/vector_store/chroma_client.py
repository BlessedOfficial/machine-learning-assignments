from pathlib import Path

import chromadb
from chromadb.config import Settings

from config import CHROMA_COLLECTION, CHROMA_PATH, EMBEDDING_MODEL
from embeddings.client import EmbeddingClient


class ChromaVectorStore:
    """Persistent ChromaDB store for AI.Inc proposition chunks."""

    def __init__(
        self,
        persist_path: str | Path | None = None,
        collection_name: str | None = None,
        embedding_client: EmbeddingClient | None = None,
    ):
        self.persist_path = Path(persist_path or CHROMA_PATH)
        self.collection_name = collection_name or CHROMA_COLLECTION
        self.embedding_client = embedding_client or EmbeddingClient()
        self.persist_path.mkdir(parents=True, exist_ok=True)

        self._client = chromadb.PersistentClient(
            path=str(self.persist_path),
            settings=Settings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine", "embedding_model": EMBEDDING_MODEL},
        )

    @property
    def collection(self):
        return self._collection

    def count(self) -> int:
        return self._collection.count()

    def reset(self) -> None:
        self._client.delete_collection(self.collection_name)
        self._collection = self._client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine", "embedding_model": EMBEDDING_MODEL},
        )

    def add_documents(
        self,
        documents: list[dict],
        batch_size: int = 100,
    ) -> int:
        if not documents:
            return 0

        added = 0
        for start in range(0, len(documents), batch_size):
            batch = documents[start : start + batch_size]
            texts = [doc["text"] for doc in batch]
            embeddings = self.embedding_client.embed(texts).tolist()

            ids = []
            metadatas = []
            for doc in batch:
                chunk_id = doc["chunk_id"]
                ids.append(chunk_id)
                base_meta = doc.get("metadata") or {}
                metadatas.append(
                    {
                        "source_file": str(
                            base_meta.get("source_file", doc.get("source_file", ""))
                        ),
                        "policy_id": str(
                            base_meta.get("policy_id", doc.get("policy_id", ""))
                        ),
                        "section": str(
                            base_meta.get("section", doc.get("section", ""))
                        ),
                        "page": str(base_meta.get("page", doc.get("page", ""))),
                        "url": str(base_meta.get("url", doc.get("url", ""))),
                        "min_role": str(
                            base_meta.get("min_role", doc.get("min_role", "employee"))
                        ),
                        "paragraph_index": int(
                            base_meta.get(
                                "paragraph_index", doc.get("paragraph_index", -1)
                            )
                        ),
                        "proposition_index": int(
                            base_meta.get(
                                "proposition_index", doc.get("proposition_index", -1)
                            )
                        ),
                        "agentic_title": str(base_meta.get("agentic_title", "")),
                        "agentic_summary": str(base_meta.get("agentic_summary", "")),
                        "proposition_count": int(
                            base_meta.get(
                                "proposition_count", doc.get("proposition_count", 1)
                            )
                        ),
                    }
                )

            self._collection.add(
                ids=ids,
                documents=texts,
                embeddings=embeddings,
                metadatas=metadatas,
            )
            added += len(batch)

        return added

    def search(self, query: str, k: int = 5) -> list[dict]:
        if self.count() == 0:
            return []

        query_embedding = self.embedding_client.embed_query(query).tolist()
        result = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=min(k, self.count()),
            include=["documents", "metadatas", "distances"],
        )

        hits: list[dict] = []
        if not result["ids"] or not result["ids"][0]:
            return hits

        for chunk_id, text, metadata, distance in zip(
            result["ids"][0],
            result["documents"][0],
            result["metadatas"][0],
            result["distances"][0],
        ):
            # Chroma cosine distance: lower is more similar; convert to similarity score
            score = 1.0 - float(distance)
            hits.append(
                {
                    "chunk_id": chunk_id,
                    "text": text,
                    "metadata": metadata or {},
                    "score": score,
                    "distance": float(distance),
                }
            )

        return hits
