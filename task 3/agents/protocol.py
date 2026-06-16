"""Typed message schemas and A2A envelope validation for inter-agent traffic."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, TypeVar
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

T = TypeVar("T", bound=BaseModel)


class AgentRole(str, Enum):
    ORCHESTRATOR = "orchestrator"
    RETRIEVER = "retriever"
    SYNTHESIZER = "synthesizer"
    SAFETY_REVIEWER = "safety_reviewer"


class MessageType(str, Enum):
    USER_REQUEST = "user_request"
    RETRIEVAL_REQUEST = "retrieval_request"
    RETRIEVAL_RESULT = "retrieval_result"
    SYNTHESIS_REQUEST = "synthesis_request"
    SYNTHESIS_RESULT = "synthesis_result"
    SAFETY_REVIEW_REQUEST = "safety_review_request"
    SAFETY_VERDICT = "safety_verdict"
    WORKFLOW_COMPLETE = "workflow_complete"
    WORKFLOW_ERROR = "workflow_error"


class ReviewDecision(str, Enum):
    APPROVE = "approve"
    REDACT = "redact"
    REGENERATE = "regenerate"


class RetrievalStatus(str, Enum):
    OK = "ok"
    EMPTY = "empty"


class SafetyIssueCode(str, Enum):
    RESPONSE_META_LEAK = "response_meta_leak"
    CITATION_DISCIPLINE = "citation_discipline"
    PII_EMAIL = "pii_email"
    PII_PHONE = "pii_phone"
    PII_SSN = "pii_ssn"
    PII_CREDIT_CARD = "pii_credit_card"
    GROUNDING_FAILURE = "grounding_failure"


class ChunkHit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chunk_id: str = Field(min_length=1)
    text: str
    score: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    retrieval_sources: list[str] | None = None

    @classmethod
    def from_retriever_dict(cls, hit: dict[str, Any]) -> ChunkHit:
        return cls(
            chunk_id=str(hit["chunk_id"]),
            text=str(hit["text"]),
            score=float(hit["score"]) if hit.get("score") is not None else None,
            metadata=dict(hit.get("metadata") or {}),
            retrieval_sources=hit.get("retrieval_sources"),
        )

    def to_retriever_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "chunk_id": self.chunk_id,
            "text": self.text,
            "metadata": self.metadata,
        }
        if self.score is not None:
            data["score"] = self.score
        if self.retrieval_sources:
            data["retrieval_sources"] = self.retrieval_sources
        return data


class UserRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1)
    user_role: str | None = None
    top_k: int | None = Field(default=None, ge=1)
    min_score: float | None = Field(default=None, ge=0.0, le=1.0)


class RetrievalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1)
    user_role: str | None = None
    top_k: int | None = Field(default=None, ge=1)
    min_score: float | None = Field(default=None, ge=0.0, le=1.0)


class RetrievalResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str
    chunks: list[ChunkHit]
    chunk_count: int = Field(ge=0)
    status: RetrievalStatus = RetrievalStatus.OK

    @model_validator(mode="after")
    def _sync_count(self) -> RetrievalResult:
        if self.chunk_count != len(self.chunks):
            raise ValueError("chunk_count must match len(chunks)")
        if self.chunk_count == 0 and self.status == RetrievalStatus.OK:
            object.__setattr__(self, "status", RetrievalStatus.EMPTY)
        return self


class SafetyIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: SafetyIssueCode
    detail: str = Field(min_length=1)


class SynthesisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1)
    chunks: list[ChunkHit]
    round_number: int = Field(default=1, ge=1)
    critique: list[SafetyIssue] = Field(default_factory=list)


class SynthesisResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str
    draft: str
    round_number: int = Field(ge=1)
    model_used: str | None = None


class SafetyReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1)
    draft: str
    chunks: list[ChunkHit]
    round_number: int = Field(default=1, ge=1)


class SafetyVerdict(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: ReviewDecision
    final_answer: str
    critique: list[SafetyIssue] = Field(default_factory=list)
    round_number: int = Field(ge=1)


class WorkflowComplete(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answer: str
    message_count: int = Field(ge=0)
    regeneration_rounds: int = Field(default=0, ge=0)
    correlation_id: str


class WorkflowError(BaseModel):
    model_config = ConfigDict(extra="forbid")

    error_code: str = Field(min_length=1)
    stage: str = Field(min_length=1)
    rule_triggered: str | None = None


PayloadModel = (
    UserRequest
    | RetrievalRequest
    | RetrievalResult
    | SynthesisRequest
    | SynthesisResult
    | SafetyReviewRequest
    | SafetyVerdict
    | WorkflowComplete
    | WorkflowError
)

PAYLOAD_SCHEMAS: dict[MessageType, type[BaseModel]] = {
    MessageType.USER_REQUEST: UserRequest,
    MessageType.RETRIEVAL_REQUEST: RetrievalRequest,
    MessageType.RETRIEVAL_RESULT: RetrievalResult,
    MessageType.SYNTHESIS_REQUEST: SynthesisRequest,
    MessageType.SYNTHESIS_RESULT: SynthesisResult,
    MessageType.SAFETY_REVIEW_REQUEST: SafetyReviewRequest,
    MessageType.SAFETY_VERDICT: SafetyVerdict,
    MessageType.WORKFLOW_COMPLETE: WorkflowComplete,
    MessageType.WORKFLOW_ERROR: WorkflowError,
}


def validate_payload(message_type: MessageType, payload: dict[str, Any]) -> PayloadModel:
    schema = PAYLOAD_SCHEMAS.get(message_type)
    if schema is None:
        raise ValueError(f"No payload schema registered for {message_type!r}")
    return schema.model_validate(payload)


class AgentEnvelope(BaseModel):
    """
    A2A-style envelope: sender, recipient, correlation_id, typed payload.

    Payload is validated against the schema for message_type on construction.
    """

    model_config = ConfigDict(extra="forbid")

    message_id: str = Field(default_factory=lambda: str(uuid4()))
    correlation_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    sender: AgentRole
    recipient: AgentRole
    message_type: MessageType
    payload: dict[str, Any]

    @model_validator(mode="after")
    def _validate_payload(self) -> AgentEnvelope:
        validate_payload(self.message_type, self.payload)
        return self

    def parse_payload(self) -> PayloadModel:
        return validate_payload(self.message_type, self.payload)

    @classmethod
    def create(
        cls,
        *,
        sender: AgentRole,
        recipient: AgentRole,
        message_type: MessageType,
        payload: BaseModel,
        correlation_id: str | None = None,
    ) -> AgentEnvelope:
        return cls(
            sender=sender,
            recipient=recipient,
            message_type=message_type,
            payload=payload.model_dump(mode="json"),
            correlation_id=correlation_id or str(uuid4()),
        )


AgentMessage = AgentEnvelope

# Legacy payload aliases
UserRequestPayload = UserRequest
RetrieveTaskPayload = RetrievalRequest
RetrieveResultPayload = RetrievalResult
SynthesizeTaskPayload = SynthesisRequest
SynthesizeResultPayload = SynthesisResult
ReviewTaskPayload = SafetyReviewRequest
ReviewResultPayload = SafetyVerdict
WorkflowCompletePayload = WorkflowComplete
WorkflowErrorPayload = WorkflowError
