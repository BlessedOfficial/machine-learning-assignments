"""Base class for collaborating agents."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from pydantic import BaseModel

from agents.protocol import AgentEnvelope, AgentRole, MessageType, validate_payload

if TYPE_CHECKING:
    from agents.bus import MessageBroker


class BaseAgent(ABC):
    role: AgentRole

    def __init__(self) -> None:
        self._broker: MessageBroker | None = None

    def bind_broker(self, broker: MessageBroker) -> None:
        self._broker = broker

    async def handle(self, envelope: AgentEnvelope) -> AgentEnvelope:
        if envelope.recipient != self.role:
            raise ValueError(
                f"{self.role.value} received message for {envelope.recipient.value}"
            )
        validate_payload(envelope.message_type, envelope.payload)
        return await self._handle(envelope)

    @abstractmethod
    async def _handle(self, envelope: AgentEnvelope) -> AgentEnvelope:
        ...

    def _reply(
        self,
        request: AgentEnvelope,
        *,
        message_type: MessageType,
        payload: BaseModel,
    ) -> AgentEnvelope:
        return AgentEnvelope.create(
            sender=self.role,
            recipient=request.sender,
            message_type=message_type,
            payload=payload,
            correlation_id=request.correlation_id,
        )
