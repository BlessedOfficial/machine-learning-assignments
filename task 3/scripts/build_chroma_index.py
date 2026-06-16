"""Build or refresh the ChromaDB index from chunks.jsonl (or corpus fallback)."""

import argparse
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR.parent))

from rag.index_chroma import build_chroma_index  # noqa: E402
from rag.retriever import retrieve_dense, retrieve_with_rerank  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Build ChromaDB index for AI.Inc RAG")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete and rebuild the collection",
    )
    parser.add_argument(
        "--query",
        type=str,
        default=None,
        help="Optional test query after indexing",
    )
    parser.add_argument(
        "--k",
        type=int,
        default=5,
        help="Number of results for --query",
    )
    parser.add_argument(
        "--dense-only",
        action="store_true",
        help="Use dense retrieval only for --query (skip BM25 fusion)",
    )
    parser.add_argument(
        "--no-rerank",
        action="store_true",
        help="Skip reranking for --query",
    )
    parser.add_argument(
        "--rerank-mode",
        type=str,
        default=None,
        choices=["cross_encoder", "llm", "mmr", "none"],
        help="Override RERANKER_MODE for --query",
    )
    args = parser.parse_args()

    build_chroma_index(reset=args.reset)

    if args.query:
        print(f"\nQuery: {args.query}\n")
        hits, rerank_result = retrieve_with_rerank(
            args.query,
            k=args.k,
            hybrid=not args.dense_only,
            rerank=not args.no_rerank,
            rerank_mode=args.rerank_mode,
        )
        if rerank_result:
            mode = f"hybrid + rerank ({rerank_result.mode})"
        else:
            mode = "dense" if args.dense_only else "hybrid (no rerank)"
        print(f"Mode: {mode}\n")
        for i, hit in enumerate(hits, start=1):
            sources = hit.get("retrieval_sources")
            source_label = f" [{', '.join(sources)}]" if sources else ""
            rerank_score = hit.get("rerank_score")
            score_label = (
                f"rerank={rerank_score:.4f}"
                if rerank_score is not None
                else f"score={hit['score']:.4f}"
            )
            print(f"{i}. [{hit['chunk_id']}] {score_label}{source_label}")
            print(f"   {hit['text'][:200]}...")
            print()


if __name__ == "__main__":
    main()
