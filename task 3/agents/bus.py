"""In-process message broker — Orchestrator-Worker delegation with A2A envelopes."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from config import AGENT_MESSAGE_LOG_PATH, AGENT_TRACE_DIR, LOG_AGENT_MESSAGES
from agents.protocol import AgentEnvelope, AgentRole, validate_payload
from agents.trace import RequestTrace

if TYPE_CHECKING:
    from agents.base import BaseAgent


class MessageBroker:
    """
    Orchestrator-Worker pattern: orchestrator delegates via typed envelopes;
    broker validates schema on every send and records the request trace.
    """

    def __init__(self) -> None:
        self._agents: dict[AgentRole, BaseAgent] = {}
        self.trace: RequestTrace | None = None

    def register(self, role: AgentRole, agent: BaseAgent) -> None:
        self._agents[role] = agent
        agent.bind_broker(self)

    def get_agent(self, role: AgentRole) -> BaseAgent | None:
        return self._agents.get(role)

    def start_trace(self, correlation_id: str) -> RequestTrace:
        self.trace = RequestTrace(correlation_id=correlation_id)
        return self.trace

    async def send(self, envelope: AgentEnvelope) -> AgentEnvelope:
        validate_payload(envelope.message_type, envelope.payload)

        recipient = self._agents.get(envelope.recipient)
        if recipient is None:
            raise KeyError(f"No agent registered for role {envelope.recipient!r}")

        self._record(envelope)
        self._maybe_log(envelope)

        response = await recipient.handle(envelope)
        validate_payload(response.message_type, response.payload)
        self._record(response)
        self._maybe_log(response)
        return response

    def record_local(self, envelope: AgentEnvelope) -> None:
        """Record orchestrator-local messages (not sent through an agent)."""
        validate_payload(envelope.message_type, envelope.payload)
        self._record(envelope)
        self._maybe_log(envelope)

    def _record(self, envelope: AgentEnvelope) -> None:
        if self.trace is not None:
            self.trace.record(envelope)

    def save_trace(self) -> Path | None:
        if self.trace is None:
            return None
        self.trace.finalize()
        return self.trace.save(Path(AGENT_TRACE_DIR))

    @staticmethod
    def _maybe_log(envelope: AgentEnvelope) -> None:
        if not LOG_AGENT_MESSAGES or not AGENT_MESSAGE_LOG_PATH:
            return
        log_path = Path(AGENT_MESSAGE_LOG_PATH)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as f:
            f.write(envelope.model_dump_json() + "\n")

    @classmethod
    def format_trace(cls, trace: RequestTrace) -> str:
        return trace.format_human()
