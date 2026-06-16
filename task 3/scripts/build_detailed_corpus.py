"""Write minimal AI.Inc corpus (30 docs) to data/corpus/ai_inc/."""

import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))

from corpus_builder import DOCS  # noqa: E402

CORPUS_DIR = SCRIPTS_DIR.parent / "data" / "corpus" / "ai_inc"
INGESTION_NOTE = """# Ingestion exclusion

Files prefixed with `_` are metadata only and must not be passed to the RAG pipeline.
"""


def main() -> None:
    CORPUS_DIR.mkdir(parents=True, exist_ok=True)

    keep = {name for name, _ in DOCS}
    keep.add("_INGESTION.md")

    for path in CORPUS_DIR.glob("*.md"):
        if path.name not in keep:
            path.unlink()
            print(f"Removed {path.name}")

    seen: set[str] = set()
    for filename, body in DOCS:
        if filename in seen:
            raise ValueError(f"Duplicate corpus filename: {filename}")
        seen.add(filename)
        (CORPUS_DIR / filename).write_text(body, encoding="utf-8")

    (CORPUS_DIR / "_INGESTION.md").write_text(INGESTION_NOTE, encoding="utf-8")

    print(f"Wrote {len(DOCS)} minimal documents to {CORPUS_DIR}")


if __name__ == "__main__":
    main()
