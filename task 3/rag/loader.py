from pathlib import Path

CORPUS_DIR = Path(__file__).resolve().parent.parent / "data" / "corpus" / "ai_inc"
MIN_PARAGRAPH_CHARS = 40


def iter_source_files() -> list[Path]:
    return sorted(
        p
        for p in CORPUS_DIR.glob("*.md")
        if p.is_file() and not p.name.startswith("_")
    )


def load_source_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def split_paragraphs(text: str) -> list[str]:
    paragraphs: list[str] = []
    for block in text.split("\n\n"):
        block = block.strip()
        if not block or len(block) < MIN_PARAGRAPH_CHARS:
            continue
        if _is_header_only(block):
            continue
        paragraphs.append(block)
    return paragraphs


def split_local_chunks(text: str) -> list[str]:
    """Split corpus text into chunks without LLM calls (bullets + prose blocks)."""
    chunks: list[str] = []

    for block in text.split("\n\n"):
        block = block.strip()
        if not block:
            continue

        lines = [line.strip() for line in block.splitlines() if line.strip()]
        bullets = [line for line in lines if line.startswith(("- ", "* ", "• "))]
        if bullets:
            for bullet in bullets:
                chunk = bullet.lstrip("-*• ").strip()
                if chunk:
                    chunks.append(chunk)
            continue

        if _is_header_only(block):
            continue

        if len(block) >= 10:
            chunks.append(block)

    return chunks


def _is_header_only(block: str) -> bool:
    lines = [line.strip() for line in block.splitlines() if line.strip()]
    return len(lines) == 1 and lines[0].startswith("#")
