"""Synthesizer agent — produces grounded draft answers with citations."""

from __future__ import annotations

import os

from config import SYNTHESIZER_MODEL
from agents.base import BaseAgent
from agents.pipeline_console import PipelineConsole
from agents.protocol import (
    AgentEnvelope,
    AgentRole,
    MessageType,
    SynthesisRequest,
    SynthesisResult,
)
from llms.synthesizer.client import call_synthesizer
from rag.retriever import build_rag_user_message
from workflow.prompts import SYSTEM_PROMPT


def _to_text(response) -> str:
    if isinstance(response, str):
        return response.strip()
    if isinstance(response, dict):
        for key in ("answer", "content", "response", "text"):
            if key in response:
                return str(response[key]).strip()
        return str(response)
    return str(response).strip()


def _mock_draft(question: str, chunks) -> str:
    """Deterministic synthesis for pipeline demos (no LLM)."""
    if not chunks:
        return (
            "I don't have enough information in the retrieved excerpts to answer "
            "that question."
        )
    primary = chunks[0]
    snippet = primary.text.strip().rstrip(".")
    return (
        f"Based on the retrieved policy excerpts, {snippet} "
        f"[`{primary.chunk_id}`]."
    )


class SynthesizerAgent(BaseAgent):
    role = AgentRole.SYNTHESIZER
    console: PipelineConsole | None = None

    async def _handle(self, envelope: AgentEnvelope) -> AgentEnvelope:
        if envelope.message_type != MessageType.SYNTHESIS_REQUEST:
            raise ValueError(
                f"SynthesizerAgent expected synthesis_request, got {envelope.message_type}"
            )

        task = SynthesisRequest.model_validate(envelope.payload)
        hits = [chunk.to_retriever_dict() for chunk in task.chunks]
        user_content = build_rag_user_message(task.question, hits)

        if task.critique:
            lines = [
                f"- [{issue.code.value}] {issue.detail}" for issue in task.critique
            ]
            user_content += (
                "\n\nSafety Reviewer critique (fix in this revision):\n"
                + "\n".join(lines)
                + "\n"
            )

        mock_mode = os.getenv("DEMO_MOCK_SYNTHESIS", "").lower() in ("1", "true", "yes")
        if mock_mode:
            draft = _mock_draft(task.question, task.chunks)
            mode_label = "mock"
        else:
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ]
            response = await call_synthesizer(messages, temperature=0.3)
            draft = _to_text(response)
            mode_label = SYNTHESIZER_MODEL

        if self.console:
            self.console.header("Synthesizer", f"Draft synthesis (round {task.round_number})")
            self.console.step(
                "Synthesizer",
                "generate draft",
                result=f"{len(draft)} chars",
                detail=f"mode={mode_label}",
            )

        result = SynthesisResult(
            question=task.question,
            draft=draft,
            round_number=task.round_number,
            model_used=SYNTHESIZER_MODEL,
        )
        return self._reply(
            envelope,
            message_type=MessageType.SYNTHESIS_RESULT,
            payload=result,
        )
