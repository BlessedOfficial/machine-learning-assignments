from rag.schemas import ChunkRecord


def records_to_documents(records: list[ChunkRecord]) -> list[dict]:
    return [
        {
            "chunk_id": r.chunk_id,
            "text": r.text,
            "source_file": r.source_file,
            "policy_id": r.policy_id or "",
            "section": r.section or "",
            "page": r.page or "",
            "url": r.url or "",
            "min_role": r.min_role or "employee",
            "paragraph_index": r.paragraph_index,
            "proposition_index": r.proposition_index,
            "metadata": {
                "source_file": r.source_file,
                "policy_id": r.policy_id or "",
                "section": r.section or "",
                "page": r.page or "",
                "url": r.url or "",
                "min_role": r.min_role or "employee",
                "paragraph_index": r.paragraph_index,
                "proposition_index": r.proposition_index,
                "agentic_title": r.agentic_title or "",
                "agentic_summary": r.agentic_summary or "",
                "proposition_count": r.proposition_count or 1,
            },
        }
        for r in records
    ]
