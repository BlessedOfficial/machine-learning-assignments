"""Per-request message-passing trace (deliverable artifact)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from agents.protocol import (
    AgentEnvelope,
    MessageType,
    PayloadModel,
    ReviewDecision,
    SafetyVerdict,
)


class TraceStep(BaseModel):
    sequence: int
    sender: str
    recipient: str
    message_type: str
    message_id: str
    summary: str
    payload: dict[str, Any]


class PreflightStep(BaseModel):
    """Non-bus steps (e.g. input guardrail) recorded before agent messages."""

    actor: str
    step: str
    result: str
    detail: str | None = None


class RequestTrace(BaseModel):
    correlation_id: str
    started_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    completed_at: str | None = None
    preflight_steps: list[PreflightStep] = Field(default_factory=list)
    steps: list[TraceStep] = Field(default_factory=list)
    feedback_loops: list[str] = Field(default_factory=list)

    def record_input_guard(self, result: object) -> None:
        """Record input guardrail outcome (orchestrator-local, not on message bus)."""
        from workflow.input_guardrails import InputGuardResult, input_guard_decision

        if not isinstance(result, InputGuardResult):
            return
        detail_parts: list[str] = []
        if result.rule_triggered:
            detail_parts.append(f"rule={result.rule_triggered}")
        if result.pii_detected:
            detail_parts.append(f"pii={','.join(result.pii_detected)}")
        if result.llm_reviewed and result.llm_decision:
            detail_parts.append(f"llm={result.llm_decision}")
        self.preflight_steps.append(
            PreflightStep(
                actor="guardrail",
                step="input_guard (rules + optional LLM)",
                result=input_guard_decision(result).upper(),
                detail="; ".join(detail_parts) if detail_parts else None,
            )
        )

    def record_preflight(
        self,
        *,
        actor: str,
        step: str,
        result: str,
        detail: str | None = None,
    ) -> None:
        self.preflight_steps.append(
            PreflightStep(actor=actor, step=step, result=result, detail=detail)
        )

    def record(self, envelope: AgentEnvelope) -> None:
        payload = envelope.parse_payload()
        self.steps.append(
            TraceStep(
                sequence=len(self.steps) + 1,
                sender=envelope.sender.value,
                recipient=envelope.recipient.value,
                message_type=envelope.message_type.value,
                message_id=envelope.message_id,
                summary=_summarize_payload(envelope.message_type, payload),
                payload=envelope.payload,
            )
        )
        if (
            envelope.message_type == MessageType.SAFETY_VERDICT
            and isinstance(payload, SafetyVerdict)
            and payload.decision == ReviewDecision.REGENERATE
        ):
            codes = ", ".join(issue.code.value for issue in payload.critique)
            self.feedback_loops.append(
                f"Round {payload.round_number}: SafetyVerdict=regenerate "
                f"({codes}) -> Orchestrator will re-dispatch SynthesisRequest"
            )

    def finalize(self) -> None:
        self.completed_at = datetime.now(timezone.utc).isoformat()

    def format_human(self) -> str:
        lines = [
            f"Request trace (correlation_id={self.correlation_id})",
            f"Started: {self.started_at}",
            "",
            "Full message-passing sequence (in order):",
            "",
        ]
        seq = 0
        if self.preflight_steps:
            lines.append("  [Preflight - not on agent bus]")
            for pre in self.preflight_steps:
                seq += 1
                detail = f" ({pre.detail})" if pre.detail else ""
                lines.append(
                    f"  {seq}. {pre.actor} | {pre.step} | {pre.result}{detail}"
                )
            lines.append("")
            lines.append("  [Agent messages]")
        for step in self.steps:
            seq += 1
            lines.append(
                f"  {seq}. {step.sender} -> {step.recipient} "
                f"[{step.message_type}] {step.summary}"
            )
        if self.feedback_loops:
            lines.append("")
            lines.append("Feedback loops:")
            for note in self.feedback_loops:
                lines.append(f"  - {note}")
        if self.completed_at:
            lines.append("")
            lines.append(f"Completed: {self.completed_at}")
        return "\n".join(lines)

    def save(self, directory: Path) -> Path:
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{self.correlation_id}.json"
        path.write_text(
            json.dumps(self.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )
        txt_path = directory / f"{self.correlation_id}.trace.txt"
        txt_path.write_text(self.format_human() + "\n", encoding="utf-8")
        return path


def _summarize_payload(message_type: MessageType, payload: PayloadModel) -> str:
    from agents.protocol import (
        RetrievalRequest,
        RetrievalResult,
        SafetyReviewRequest,
        SafetyVerdict,
        SynthesisRequest,
        SynthesisResult,
        UserRequest,
        WorkflowComplete,
        WorkflowError,
    )

    if isinstance(payload, UserRequest):
        preview = payload.question[:60].replace("\n", " ")
        return f'question="{preview}..." role={payload.user_role}'
    if isinstance(payload, RetrievalRequest):
        preview = payload.query[:50].replace("\n", " ")
        return f'query="{preview}..."'
    if isinstance(payload, RetrievalResult):
        return f"chunks={payload.chunk_count} status={payload.status.value}"
    if isinstance(payload, SynthesisRequest):
        critique = len(payload.critique)
        extra = f" critique_items={critique}" if critique else ""
        return f"round={payload.round_number}{extra}"
    if isinstance(payload, SynthesisResult):
        preview = payload.draft[:50].replace("\n", " ")
        return f'round={payload.round_number} draft="{preview}..."'
    if isinstance(payload, SafetyReviewRequest):
        return f"round={payload.round_number} draft_len={len(payload.draft)}"
    if isinstance(payload, SafetyVerdict):
        codes = ",".join(i.code.value for i in payload.critique) or "none"
        return f"decision={payload.decision.value} issues=[{codes}]"
    if isinstance(payload, WorkflowComplete):
        return (
            f"answer_len={len(payload.answer)} "
            f"regeneration_rounds={payload.regeneration_rounds}"
        )
    if isinstance(payload, WorkflowError):
        return f"error={payload.error_code} stage={payload.stage}"
    return message_type.value
