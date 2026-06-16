from pydantic import BaseModel, Field


class PropositionList(BaseModel):
    """Structured output for wfh/proposal-indexing decomposition."""

    sentences: list[str] = Field(default_factory=list)


class ChunkRecord(BaseModel):
    chunk_id: str
    source_file: str
    paragraph_index: int
    proposition_index: int
    text: str
    policy_id: str | None = None
    section: str | None = None
    page: str | None = None
    url: str | None = None
    agentic_title: str | None = None
    agentic_summary: str | None = None
    agentic_chunk_key: str | None = None
    proposition_count: int | None = None
    min_role: str | None = None
