from pathlib import Path

from config import CHUNKS_PATH
from rag.chunk_corpus import load_chunks
from rag.citation_meta import citation_fields_for_document
from rag.documents import records_to_documents
from rag.loader import iter_source_files, load_source_text, split_paragraphs
from rag.schemas import ChunkRecord
from rag.sparse_index import reset_sparse_index
from vector_store.chroma_client import ChromaVectorStore


def chunks_from_corpus() -> list[ChunkRecord]:
    """Fallback: one chunk per paragraph when chunks.jsonl is not built yet."""
    records: list[ChunkRecord] = []
    for path in iter_source_files():
        doc_text = load_source_text(path)
        paragraphs = split_paragraphs(doc_text)
        stem = path.stem
        for paragraph_index, paragraph in enumerate(paragraphs):
            records.append(
                ChunkRecord(
                    chunk_id=f"{stem}#para-{paragraph_index:03d}",
                    source_file=path.name,
                    paragraph_index=paragraph_index,
                    proposition_index=0,
                    text=paragraph,
                    **citation_fields_for_document(
                        doc_text, path.name, chunk_index=paragraph_index
                    ),
                )
            )
    return records


def build_chroma_index(
    reset: bool = False,
    chunks_path: Path | None = None,
    use_corpus_fallback: bool = True,
) -> ChromaVectorStore:
    store = ChromaVectorStore()

    if reset and store.count() > 0:
        print("Resetting Chroma collection...")
        store.reset()

    if store.count() > 0 and not reset:
        print(f"Chroma already has {store.count()} chunks; skipping index (use --reset to rebuild).")
        return store

    path = chunks_path or Path(CHUNKS_PATH)
    if path.exists():
        print(f"Loading chunks from {path}...")
        records = load_chunks(path)
    elif use_corpus_fallback:
        print("chunks.jsonl not found; indexing raw paragraphs from corpus...")
        records = chunks_from_corpus()
    else:
        raise FileNotFoundError(
            f"No chunks at {path}. Run scripts/run_chunking.py first or pass use_corpus_fallback=True."
        )

    if not records:
        raise ValueError("No chunks to index.")

    documents = records_to_documents(records)
    print(f"Embedding and indexing {len(documents)} chunks into Chroma...")
    added = store.add_documents(documents)
    reset_sparse_index()
    print(f"Indexed {added} chunks (collection total: {store.count()})")
    return store
