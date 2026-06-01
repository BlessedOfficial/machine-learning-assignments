"""Orchestrator agent — Orchestrator-Worker delegation with feedback loop."""

from __future__ import annotations

from pathlib import Path

from config import MAX_SYNTHESIS_ROUNDS, SHOW_PIPELINE_LOG
from agents.base import BaseAgent
from agents.bus import MessageBroker
from agents.pipeline_log import PipelineRunLog
from agents.protocol import (
    AgentEnvelope,
    AgentRole,
    MessageType,
    RetrievalRequest,
    RetrievalResult,
    ReviewDecision,
    SafetyIssue,
    SafetyReviewRequest,
    SafetyVerdict,
    SynthesisRequest,
    SynthesisResult,
    UserRequest,
    WorkflowComplete,
    WorkflowError,
)
from agents.retriever_agent import RetrieverAgent
from agents.safety_reviewer_agent import SafetyReviewerAgent
from agents.synthesizer_agent import SynthesizerAgent
from agents.trace import RequestTrace
from workflow.guardrails import apply_response_guardrail
from workflow.incident_log import log_guardrail_incident
from workflow.input_guardrails import guard_user_input
from workflow.prompts import OUT_OF_SCOPE_REPLY


class OrchestratorAgent(BaseAgent):
    role = AgentRole.ORCHESTRATOR

    def __init__(self, broker: MessageBroker | None = None) -> None:
        super().__init__()
        self._broker = broker or self._build_default_broker()
        self._max_rounds = MAX_SYNTHESIS_ROUNDS
        self.pipeline_log: PipelineRunLog | None = None

    @staticmethod
    def _build_default_broker() -> MessageBroker:
        broker = MessageBroker()
        retriever = RetrieverAgent()
        broker.register(AgentRole.RETRIEVER, retriever)
        broker.register(AgentRole.SYNTHESIZER, SynthesizerAgent())
        broker.register(AgentRole.SAFETY_REVIEWER, SafetyReviewerAgent())
        broker._retriever_agent = retriever
        return broker

    @property
    def broker(self) -> MessageBroker:
        return self._broker

    async def run(
        self,
        request: UserRequest,
        *,
        run_label: str = "live",
    ) -> tuple[str, RequestTrace, Path | None, PipelineRunLog]:
        correlation_id = AgentEnvelope.create(
            sender=AgentRole.ORCHESTRATOR,
            recipient=AgentRole.ORCHESTRATOR,
            message_type=MessageType.USER_REQUEST,
            payload=request,
        ).correlation_id

        self.pipeline_log = PipelineRunLog(
            run_label=run_label,
            correlation_id=correlation_id,
            question=request.question,
        )
        retriever = getattr(self._broker, "_retriever_agent", None)
        if isinstance(retriever, RetrieverAgent):
            retriever.pipeline_log = self.pipeline_log

        trace = self._broker.start_trace(correlation_id)
        user_envelope = AgentEnvelope.create(
            sender=AgentRole.ORCHESTRATOR,
            recipient=AgentRole.ORCHESTRATOR,
            message_type=MessageType.USER_REQUEST,
            payload=request,
            correlation_id=correlation_id,
        )
        self._broker.record_local(user_envelope)

        guard = guard_user_input(request.question)
        self.pipeline_log.record_input_guard(guard)

        if not guard.allowed:
            answer = guard.block_message or apply_response_guardrail(
                "", source_input=request.question
            )
            self.pipeline_log.final_answer = answer
            self._finalize_run(correlation_id, answer, regeneration_rounds=0)
            return answer, trace, self._broker.save_trace(), self.pipeline_log

        safe_question = request.model_copy(update={"question": guard.text})
        retrieve_response = await self._broker.send(
            AgentEnvelope.create(
                sender=AgentRole.ORCHESTRATOR,
                recipient=AgentRole.RETRIEVER,
                message_type=MessageType.RETRIEVAL_REQUEST,
                payload=RetrievalRequest(
                    query=safe_question.question,
                    user_role=safe_question.user_role,
                    top_k=safe_question.top_k,
                    min_score=safe_question.min_score,
                ),
                correlation_id=correlation_id,
            )
        )
        retrieve_result = RetrievalResult.model_validate(retrieve_response.payload)

        if retrieve_result.chunk_count == 0:
            log_guardrail_incident(
                rule_triggered="no_retrieval_hits",
                raw_input=safe_question.question,
                decision="block",
                stage="retrieval",
                detail="no accessible chunks after retrieval and RBAC",
            )
            self._broker.record_local(
                AgentEnvelope.create(
                    sender=AgentRole.ORCHESTRATOR,
                    recipient=AgentRole.ORCHESTRATOR,
                    message_type=MessageType.WORKFLOW_ERROR,
                    payload=WorkflowError(
                        error_code="no_retrieval_hits",
                        stage="retrieval",
                        rule_triggered="no_retrieval_hits",
                    ),
                    correlation_id=correlation_id,
                )
            )
            self.pipeline_log.final_answer = OUT_OF_SCOPE_REPLY
            self._finalize_run(correlation_id, OUT_OF_SCOPE_REPLY, regeneration_rounds=0)
            return OUT_OF_SCOPE_REPLY, trace, self._broker.save_trace(), self.pipeline_log

        chunks = retrieve_result.chunks
        regeneration_rounds = 0
        critique: list[SafetyIssue] = []
        final_answer = OUT_OF_SCOPE_REPLY

        for round_number in range(1, self._max_rounds + 1):
            synth_response = await self._broker.send(
                AgentEnvelope.create(
                    sender=AgentRole.ORCHESTRATOR,
                    recipient=AgentRole.SYNTHESIZER,
                    message_type=MessageType.SYNTHESIS_REQUEST,
                    payload=SynthesisRequest(
                        question=safe_question.question,
                        chunks=chunks,
                        round_number=round_number,
                        critique=critique,
                    ),
                    correlation_id=correlation_id,
                )
            )
            synth_result = SynthesisResult.model_validate(synth_response.payload)

            review_response = await self._broker.send(
                AgentEnvelope.create(
                    sender=AgentRole.ORCHESTRATOR,
                    recipient=AgentRole.SAFETY_REVIEWER,
                    message_type=MessageType.SAFETY_REVIEW_REQUEST,
                    payload=SafetyReviewRequest(
                        question=safe_question.question,
                        draft=synth_result.draft,
                        chunks=chunks,
                        round_number=round_number,
                    ),
                    correlation_id=correlation_id,
                )
            )
            verdict = SafetyVerdict.model_validate(review_response.payload)
            self.pipeline_log.record_safety_verdict(
                verdict, max_rounds=self._max_rounds
            )
            final_answer = verdict.final_answer

            if verdict.decision != ReviewDecision.REGENERATE:
                break

            regeneration_rounds += 1
            critique = verdict.critique
            if round_number >= self._max_rounds:
                break

        self.pipeline_log.regeneration_rounds = regeneration_rounds
        self.pipeline_log.final_answer = final_answer
        self._finalize_run(
            correlation_id, final_answer, regeneration_rounds=regeneration_rounds
        )
        return final_answer, trace, self._broker.save_trace(), self.pipeline_log

    def _finalize_run(
        self,
        correlation_id: str,
        answer: str,
        *,
        regeneration_rounds: int,
    ) -> None:
        self._complete(correlation_id, answer, regeneration_rounds=regeneration_rounds)
        if self.pipeline_log and self._broker.trace:
            self.pipeline_log.record_from_trace(self._broker.trace)
        if self.pipeline_log and SHOW_PIPELINE_LOG:
            print(self.pipeline_log.format_console())

    def _complete(
        self,
        correlation_id: str,
        answer: str,
        *,
        regeneration_rounds: int,
    ) -> None:
        step_count = len(self._broker.trace.steps) if self._broker.trace else 0
        self._broker.record_local(
            AgentEnvelope.create(
                sender=AgentRole.ORCHESTRATOR,
                recipient=AgentRole.ORCHESTRATOR,
                message_type=MessageType.WORKFLOW_COMPLETE,
                payload=WorkflowComplete(
                    answer=answer,
                    message_count=step_count + 1,
                    regeneration_rounds=regeneration_rounds,
                    correlation_id=correlation_id,
                ),
                correlation_id=correlation_id,
            )
        )

    async def _handle(self, envelope: AgentEnvelope) -> AgentEnvelope:
        if envelope.message_type != MessageType.USER_REQUEST:
            raise ValueError(
                f"OrchestratorAgent expected user_request, got {envelope.message_type}"
            )
        request = UserRequest.model_validate(envelope.payload)
        answer, _, _, _ = await self.run(request)
        return self._reply(
            envelope,
            message_type=MessageType.WORKFLOW_COMPLETE,
            payload=WorkflowComplete(
                answer=answer,
                message_count=len(self._broker.trace.steps) if self._broker.trace else 0,
                regeneration_rounds=0,
                correlation_id=envelope.correlation_id,
            ),
        )
