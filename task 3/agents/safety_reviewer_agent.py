"""Safety Reviewer agent — output guardrails with approve / redact / regenerate."""

from __future__ import annotations

from agents.base import BaseAgent
from agents.protocol import (
    AgentEnvelope,
    AgentRole,
    MessageType,
    ReviewDecision,
    SafetyIssue,
    SafetyIssueCode,
    SafetyReviewRequest,
    SafetyVerdict,
)
from workflow.citations import (
    enforce_citation_discipline,
    has_explicit_uncertainty,
    is_out_of_scope_reply,
)
from workflow.grounding import apply_grounding_check
from workflow.guardrails import apply_response_guardrail
from workflow.pii_utils import redact_leaked_pii
from workflow.prompts import OUT_OF_SCOPE_REPLY


_CITATION_REJECTION = (
    "I don't have enough information in the retrieved excerpts to answer "
    "that question. Please contact the appropriate AI.Inc support channel "
    "for further assistance."
)

_PII_CODE_MAP = {
    "email": SafetyIssueCode.PII_EMAIL,
    "phone": SafetyIssueCode.PII_PHONE,
    "ssn": SafetyIssueCode.PII_SSN,
    "credit_card": SafetyIssueCode.PII_CREDIT_CARD,
}


class SafetyReviewerAgent(BaseAgent):
    role = AgentRole.SAFETY_REVIEWER

    async def _handle(self, envelope: AgentEnvelope) -> AgentEnvelope:
        if envelope.message_type != MessageType.SAFETY_REVIEW_REQUEST:
            raise ValueError(
                f"SafetyReviewerAgent expected safety_review_request, "
                f"got {envelope.message_type}"
            )

        task = SafetyReviewRequest.model_validate(envelope.payload)
        hits = [chunk.to_retriever_dict() for chunk in task.chunks]
        critique: list[SafetyIssue] = []

        after_meta = apply_response_guardrail(
            task.draft, source_input=task.question
        )
        if (
            after_meta == OUT_OF_SCOPE_REPLY
            and task.draft.strip()
            and not is_out_of_scope_reply(task.draft)
        ):
            critique.append(
                SafetyIssue(
                    code=SafetyIssueCode.RESPONSE_META_LEAK,
                    detail="Draft disclosed system restrictions or internal instructions.",
                )
            )
            return self._reply(
                envelope,
                message_type=MessageType.SAFETY_VERDICT,
                payload=SafetyVerdict(
                    decision=ReviewDecision.REGENERATE,
                    final_answer=after_meta,
                    critique=critique,
                    round_number=task.round_number,
                ),
            )

        after_citations = enforce_citation_discipline(
            after_meta, hits, source_input=task.question
        )
        if self._needs_citation_regeneration(task.draft, after_citations):
            critique.append(
                SafetyIssue(
                    code=SafetyIssueCode.CITATION_DISCIPLINE,
                    detail="Factual claims require inline chunk ID citations.",
                )
            )
            return self._reply(
                envelope,
                message_type=MessageType.SAFETY_VERDICT,
                payload=SafetyVerdict(
                    decision=ReviewDecision.REGENERATE,
                    final_answer=after_citations,
                    critique=critique,
                    round_number=task.round_number,
                ),
            )

        after_grounding = apply_grounding_check(
            after_citations, hits, source_input=task.question
        )
        final, pii_flags = redact_leaked_pii(after_grounding)

        for flag in pii_flags:
            code = _PII_CODE_MAP.get(flag, SafetyIssueCode.PII_EMAIL)
            critique.append(
                SafetyIssue(
                    code=code,
                    detail=f"PII detected in output ({flag}); redacted before delivery.",
                )
            )

        if critique:
            verdict = SafetyVerdict(
                decision=ReviewDecision.REDACT,
                final_answer=final,
                critique=critique,
                round_number=task.round_number,
            )
        else:
            verdict = SafetyVerdict(
                decision=ReviewDecision.APPROVE,
                final_answer=final,
                critique=[],
                round_number=task.round_number,
            )

        return self._reply(
            envelope,
            message_type=MessageType.SAFETY_VERDICT,
            payload=verdict,
        )

    @staticmethod
    def _needs_citation_regeneration(draft: str, after_citations: str) -> bool:
        if has_explicit_uncertainty(draft) or is_out_of_scope_reply(draft):
            return False
        return (
            after_citations.strip() == _CITATION_REJECTION.strip()
            and draft.strip() != after_citations.strip()
        )
