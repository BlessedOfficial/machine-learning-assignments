from config import CHUNKS_PATH
from rag.chunk_corpus import load_chunks
from rag.documents import records_to_documents
from rag.bm25 import SparseRetriever

_sparse: SparseRetriever | None = None


def get_sparse_retriever() -> SparseRetriever:
    global _sparse
    if _sparse is None:
        records = load_chunks()
        if not records:
            raise ValueError(
                f"No chunks at {CHUNKS_PATH}. Run scripts/run_chunking.py first."
            )
        retriever = SparseRetriever()
        retriever.add_documents(records_to_documents(records))
        _sparse = retriever
    return _sparse


def reset_sparse_index() -> None:
    global _sparse
    _sparse = None
