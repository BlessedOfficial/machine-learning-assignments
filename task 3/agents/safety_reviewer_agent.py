"""Safety Reviewer agent ΓÇö hybrid rule + LLM output guardrails."""

from __future__ import annotations

from dataclasses import dataclass

from agents.base import BaseAgent
from agents.pipeline_console import PipelineConsole
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
from config import ENABLE_LLM_SAFETY_REVIEW
from llms.safety_reviewer.review import (
    merge_critiques,
    merge_decisions,
    run_llm_safety_review,
)
from workflow.citations import (
    enforce_citation_discipline,
    has_explicit_uncertainty,
    is_out_of_scope_reply,
)
from workflow.grounding import apply_grounding_check
from workflow.guardrails import apply_response_guardrail
from workflow.incident_log import log_guardrail_incident
from workflow.pii_utils import redact_output_pii
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


@dataclass
class RulePipelineResult:
    decision: ReviewDecision
    final_answer: str
    critique: list[SafetyIssue]
    regenerate: bool = False


class SafetyReviewerAgent(BaseAgent):
    role = AgentRole.SAFETY_REVIEWER
    console: PipelineConsole | None = None

    async def _handle(self, envelope: AgentEnvelope) -> AgentEnvelope:
        if envelope.message_type != MessageType.SAFETY_REVIEW_REQUEST:
            raise ValueError(
                f"SafetyReviewerAgent expected safety_review_request, "
                f"got {envelope.message_type}"
            )

        task = SafetyReviewRequest.model_validate(envelope.payload)
        hits = [chunk.to_retriever_dict() for chunk in task.chunks]
        rule_result = self._run_rule_pipeline(task.draft, hits, task.question)

        if self.console:
            self.console.header(
                "SafetyReviewer",
                f"Rule pipeline (round {task.round_number})",
            )
            self.console.step(
                "SafetyReviewer",
                "deterministic rules",
                result=rule_result.decision.value.upper(),
                detail="regenerate" if rule_result.regenerate else None,
            )

        decision = rule_result.decision
        critique = list(rule_result.critique)
        candidate = rule_result.final_answer

        if ENABLE_LLM_SAFETY_REVIEW:
            llm_review = await run_llm_safety_review(
                question=task.question,
                draft=task.draft,
                hits=hits,
                rule_decision=rule_result.decision,
                rule_critique=rule_result.critique,
                processed_answer=rule_result.final_answer,
            )
            if llm_review is not None:
                if self.console:
                    llm_result = "BLOCK" if llm_review.blocked else llm_review.decision.value.upper()
                    self.console.step(
                        "SafetyReviewer",
                        "LLM safety review",
                        result=llm_result,
                    )
                if llm_review.blocked:
                    for issue in llm_review.issues:
                        log_guardrail_incident(
                            rule_triggered=f"llm_{issue.code.value}",
                            raw_input=task.question,
                            decision="block",
                            stage="output",
                            detail=issue.detail,
                        )
                    decision = ReviewDecision.APPROVE
                    candidate = llm_review.safe_answer or OUT_OF_SCOPE_REPLY
                else:
                    decision = merge_decisions(
                        rule_result.decision, llm_review.decision
                    )
                    if llm_review.safe_answer:
                        candidate = llm_review.safe_answer
                    elif llm_review.decision == ReviewDecision.REGENERATE:
                        log_guardrail_incident(
                            rule_triggered="llm_safety_regenerate",
                            raw_input=task.question,
                            decision="regenerate",
                            stage="output",
                            detail="; ".join(
                                f"[{i.code.value}] {i.detail}" for i in llm_review.issues
                            )
                            or None,
                        )
                        candidate = task.draft
                    critique = merge_critiques(rule_result.critique, llm_review.issues)

        if rule_result.regenerate or decision == ReviewDecision.REGENERATE:
            post = self._postprocess_final(candidate, hits, task.question)
            return self._reply(
                envelope,
                message_type=MessageType.SAFETY_VERDICT,
                payload=SafetyVerdict(
                    decision=ReviewDecision.REGENERATE,
                    final_answer=post.final_answer,
                    critique=critique or post.critique,
                    round_number=task.round_number,
                ),
            )

        post = self._postprocess_final(candidate, hits, task.question)
        final_answer = post.final_answer
        critique = merge_critiques(critique, post.critique)
        if post.regenerate:
            verdict = SafetyVerdict(
                decision=ReviewDecision.REGENERATE,
                final_answer=final_answer,
                critique=critique,
                round_number=task.round_number,
            )
        elif critique:
            verdict = SafetyVerdict(
                decision=ReviewDecision.REDACT,
                final_answer=final_answer,
                critique=critique,
                round_number=task.round_number,
            )
        else:
            verdict = SafetyVerdict(
                decision=ReviewDecision.APPROVE,
                final_answer=final_answer,
                critique=[],
                round_number=task.round_number,
            )

        return self._reply(
            envelope,
            message_type=MessageType.SAFETY_VERDICT,
            payload=verdict,
        )

    def _run_rule_pipeline(
        self, draft: str, hits: list[dict], question: str
    ) -> RulePipelineResult:
        critique: list[SafetyIssue] = []

        after_meta = apply_response_guardrail(draft, source_input=question)
        if (
            after_meta == OUT_OF_SCOPE_REPLY
            and draft.strip()
            and not is_out_of_scope_reply(draft)
        ):
            critique.append(
                SafetyIssue(
                    code=SafetyIssueCode.RESPONSE_META_LEAK,
                    detail="Draft disclosed system restrictions or internal instructions.",
                )
            )
            return RulePipelineResult(
                decision=ReviewDecision.REGENERATE,
                final_answer=after_meta,
                critique=critique,
                regenerate=True,
            )

        after_citations = enforce_citation_discipline(
            after_meta, hits, source_input=question
        )
        if self._needs_citation_regeneration(draft, after_citations):
            critique.append(
                SafetyIssue(
                    code=SafetyIssueCode.CITATION_DISCIPLINE,
                    detail="Factual claims require inline chunk ID citations.",
                )
            )
            return RulePipelineResult(
                decision=ReviewDecision.REGENERATE,
                final_answer=after_citations,
                critique=critique,
                regenerate=True,
            )

        after_grounding = apply_grounding_check(
            after_citations, hits, source_input=question
        )
        final, pii_flags = redact_output_pii(
            after_grounding, hits, source_input=question
        )

        for flag in pii_flags:
            code = _PII_CODE_MAP.get(flag, SafetyIssueCode.PII_EMAIL)
            critique.append(
                SafetyIssue(
                    code=code,
                    detail=f"PII detected in output ({flag}); redacted before delivery.",
                )
            )

        decision = ReviewDecision.REDACT if critique else ReviewDecision.APPROVE
        return RulePipelineResult(
            decision=decision,
            final_answer=final,
            critique=critique,
            regenerate=False,
        )

    def _postprocess_final(
        self, answer: str, hits: list[dict], question: str
    ) -> RulePipelineResult:
        critique: list[SafetyIssue] = []

        after_meta = apply_response_guardrail(answer, source_input=question)
        if (
            after_meta == OUT_OF_SCOPE_REPLY
            and answer.strip()
            and not is_out_of_scope_reply(answer)
        ):
            critique.append(
                SafetyIssue(
                    code=SafetyIssueCode.RESPONSE_META_LEAK,
                    detail="Final answer disclosed system restrictions or internal instructions.",
                )
            )
            return RulePipelineResult(
                decision=ReviewDecision.REGENERATE,
                final_answer=after_meta,
                critique=critique,
                regenerate=True,
            )

        after_citations = enforce_citation_discipline(
            after_meta, hits, source_input=question
        )
        if self._needs_citation_regeneration(answer, after_citations):
            critique.append(
                SafetyIssue(
                    code=SafetyIssueCode.CITATION_DISCIPLINE,
                    detail="Final answer lacks required chunk ID citations.",
                )
            )
            return RulePipelineResult(
                decision=ReviewDecision.REGENERATE,
                final_answer=after_citations,
                critique=critique,
                regenerate=True,
            )

        after_grounding = apply_grounding_check(
            after_citations, hits, source_input=question
        )
        final, pii_flags = redact_output_pii(
            after_grounding, hits, source_input=question
        )

        for flag in pii_flags:
            code = _PII_CODE_MAP.get(flag, SafetyIssueCode.PII_EMAIL)
            critique.append(
                SafetyIssue(
                    code=code,
                    detail=f"PII detected in output ({flag}); redacted before delivery.",
                )
            )

        return RulePipelineResult(
            decision=ReviewDecision.REDACT if critique else ReviewDecision.APPROVE,
            final_answer=final,
            critique=critique,
            regenerate=False,
        )

    @staticmethod
    def _needs_citation_regeneration(draft: str, after_citations: str) -> bool:
        if has_explicit_uncertainty(draft) or is_out_of_scope_reply(draft):
            return False
        return (
            after_citations.strip() == _CITATION_REJECTION.strip()
            and draft.strip() != after_citations.strip()
        )
