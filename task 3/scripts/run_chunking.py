"""Run LLM proposition chunking + optional AgenticChunker grouping.

Pipeline:
  1. wfh/proposal-indexing (LangChain Hub) -> atomic propositions per paragraph
  2. AgenticChunker (default on) -> group propositions into semantic chunks per file

Use --local when OpenRouter free-tier limits are hit (no API calls).

Examples:
  .venv\\Scripts\\python.exe scripts\\run_chunking.py --local
  .venv\\Scripts\\python.exe scripts\\run_chunking.py --limit-files 1 --limit-paragraphs 3
  .venv\\Scripts\\python.exe scripts\\run_chunking.py --no-agentic
  .venv\\Scripts\\python.exe scripts\\run_chunking.py --verbose-agentic
"""

import argparse
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR.parent))

from rag.chunk_corpus import chunk_all_sources  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Chunk AI.Inc corpus: propositions + agentic grouping"
    )
    parser.add_argument("--limit-files", type=int, default=None)
    parser.add_argument("--limit-paragraphs", type=int, default=None)
    parser.add_argument(
        "--local",
        action="store_true",
        help="Chunk by bullet lines (no OpenRouter calls)",
    )
    parser.add_argument(
        "--no-agentic",
        action="store_true",
        help="Skip AgenticChunker; emit one chunk per proposition",
    )
    parser.add_argument(
        "--verbose-agentic",
        action="store_true",
        help="Print AgenticChunker assignment logs",
    )
    args = parser.parse_args()

    chunk_all_sources(
        limit_files=args.limit_files,
        limit_paragraphs_per_file=args.limit_paragraphs,
        use_agentic=not args.no_agentic,
        use_local=args.local,
        verbose_agentic=args.verbose_agentic,
    )


if __name__ == "__main__":
    main()
