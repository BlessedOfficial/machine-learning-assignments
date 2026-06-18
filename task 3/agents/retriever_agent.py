"""Retriever agent — owns vector-store access and ranked chunk retrieval."""

from __future__ import annotations

from typing import TYPE_CHECKING

from agents.base import BaseAgent
from agents.pipeline_console import PipelineConsole
from agents.protocol import (
    AgentEnvelope,
    AgentRole,
    ChunkHit,
    MessageType,
    RetrievalRequest,
    RetrievalResult,
)
from rag.retrieval_diagnostics import retrieve_with_diagnostics
from workflow.rbac import filter_hits_by_role

if TYPE_CHECKING:
    from agents.pipeline_log import PipelineRunLog


class RetrieverAgent(BaseAgent):
    role = AgentRole.RETRIEVER
    pipeline_log: PipelineRunLog | None = None
    console: PipelineConsole | None = None

    async def _handle(self, envelope: AgentEnvelope) -> AgentEnvelope:
        if envelope.message_type != MessageType.RETRIEVAL_REQUEST:
            raise ValueError(
                f"RetrieverAgent expected retrieval_request, got {envelope.message_type}"
            )

        task = RetrievalRequest.model_validate(envelope.payload)
        raw_hits, diagnostics = retrieve_with_diagnostics(
            task.query,
            top_k=task.top_k,
        )
        if self.pipeline_log is not None:
            self.pipeline_log.record_retrieval(diagnostics)

        filtered = filter_hits_by_role(raw_hits, task.user_role)
        chunks = [ChunkHit.from_retriever_dict(hit) for hit in filtered]

        top_id = chunks[0].chunk_id if chunks else "(none)"
        if self.console:
            self.console.header("Retriever", "Hybrid retrieval + RBAC")
            self.console.step(
                "Retriever",
                "dense + BM25 + RRF + rerank",
                result=f"{len(chunks)} chunks",
                detail=f"top: {top_id}; rbac filtered {len(raw_hits)} -> {len(filtered)}",
            )

        result = RetrievalResult(
            query=task.query,
            chunks=chunks,
            chunk_count=len(chunks),
        )
        return self._reply(
            envelope,
            message_type=MessageType.RETRIEVAL_RESULT,
            payload=result,
        )
