"""Structured console / file logging for full pipeline visibility."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agents.protocol import ReviewDecision, SafetyVerdict
from agents.trace import RequestTrace
from rag.retrieval_diagnostics import RetrievalDiagnostics, ScoredChunk
from workflow.citations import extract_chunk_ids_from_answer
from workflow.input_guardrails import InputGuardResult, input_guard_decision

_CHUNK_ID_PATTERN = re.compile(
    r"[a-z0-9][a-z0-9-]*#(?:loc|prop|ag|para)-\d+",
    re.IGNORECASE,
)


@dataclass
class InputGuardLog:
    decision: str
    rule: str | None
    pii_flags: list[str] = field(default_factory=list)


@dataclass
class SafetyRoundLog:
    round_number: int
    decision: str
    critique: list[dict[str, str]]
    feedback_to_synthesizer: bool = False


@dataclass
class PipelineRunLog:
    run_label: str
    correlation_id: str
    question: str
    input_guard: InputGuardLog | None = None
    retrieval: RetrievalDiagnostics | None = None
    agent_messages: list[dict[str, str]] = field(default_factory=list)
    safety_rounds: list[SafetyRoundLog] = field(default_factory=list)
    final_answer: str | None = None
    regeneration_rounds: int = 0

    def record_input_guard(self, result: InputGuardResult) -> None:
        self.input_guard = InputGuardLog(
            decision=input_guard_decision(result),
            rule=result.rule_triggered,
            pii_flags=list(result.pii_detected),
        )

    def record_retrieval(self, diagnostics: RetrievalDiagnostics) -> None:
        self.retrieval = diagnostics

    def record_agent_message(
        self,
        *,
        sender: str,
        recipient: str,
        message_type: str,
        summary: str,
    ) -> None:
        self.agent_messages.append(
            {
                "sender": sender,
                "recipient": recipient,
                "message_type": message_type,
                "summary": summary,
            }
        )

    def record_from_trace(self, trace: RequestTrace) -> None:
        self.agent_messages.clear()
        for step in trace.steps:
            self.record_agent_message(
                sender=step.sender,
                recipient=step.recipient,
                message_type=step.message_type,
                summary=step.summary,
            )

    def record_safety_verdict(self, verdict: SafetyVerdict, *, max_rounds: int) -> None:
        critique = [
            {"code": issue.code.value, "detail": issue.detail}
            for issue in verdict.critique
        ]
        will_loop = (
            verdict.decision == ReviewDecision.REGENERATE
            and verdict.round_number < max_rounds
        )
        self.safety_rounds.append(
            SafetyRoundLog(
                round_number=verdict.round_number,
                decision=verdict.decision.value,
                critique=critique,
                feedback_to_synthesizer=will_loop,
            )
        )

    def format_console(self) -> str:
        lines = [
            "",
            "=" * 72,
            f"PIPELINE RUN: {self.run_label}  (correlation_id={self.correlation_id})",
            "=" * 72,
            f"Question: {self.question}",
            "",
            "--- [1] INPUT GUARDRAIL ---",
        ]
        if self.input_guard:
            lines.append(f"  decision : {self.input_guard.decision.upper()}")
            lines.append(f"  rule     : {self.input_guard.rule or '(none)'}")
            if self.input_guard.pii_flags:
                lines.append(f"  pii      : {', '.join(self.input_guard.pii_flags)}")
        else:
            lines.append("  (not recorded)")

        lines.extend(["", "--- [2] RETRIEVAL ---"])
        if self.retrieval:
            r = self.retrieval
            lines.append(f"  query       : {r.query}")
            lines.append(f"  candidate_k : {r.candidate_k}  |  top_k : {r.top_k}")
            lines.extend(self._format_score_table("  Dense (Chroma)", r.dense))
            lines.extend(self._format_score_table("  Sparse (BM25)", r.sparse))
            lines.extend(self._format_score_table("  Fused (RRF)", r.fused))
            if r.rerank_log:
                lines.append(
                    f"  Reranked ({r.rerank_mode or 'unknown'}): "
                    f"{len(r.fused)} candidates -> top {r.top_k}"
                )
                lines.extend(self._format_rerank_table(r.rerank_log))
            if r.final_chunk_ids:
                lines.append("  Final order : " + " -> ".join(r.final_chunk_ids))
        else:
            lines.append("  (skipped - input blocked or no retrieval)")

        lines.extend(["", "--- [3] INTER-AGENT MESSAGES ---"])
        if self.agent_messages:
            for index, msg in enumerate(self.agent_messages, start=1):
                lines.append(
                    f"  {index}. {msg['sender']} -> {msg['recipient']} "
                    f"[{msg['message_type']}] {msg['summary']}"
                )
        else:
            lines.append("  (none)")

        lines.extend(["", "--- [4] SAFETY REVIEWER ---"])
        if self.safety_rounds:
            for rnd in self.safety_rounds:
                lines.append(
                    f"  Round {rnd.round_number}: {rnd.decision.upper()}"
                )
                if rnd.critique:
                    for item in rnd.critique:
                        lines.append(f"    - [{item['code']}] {item['detail']}")
                if rnd.feedback_to_synthesizer:
                    lines.append(
                        "    >> Feedback loop: Orchestrator re-dispatching "
                        "SynthesisRequest with critique"
                    )
            lines.append(f"  Total regeneration rounds: {self.regeneration_rounds}")
        else:
            lines.append("  (skipped - input blocked or no synthesis)")

        lines.extend(["", "--- [5] FINAL ANSWER ---"])
        if self.final_answer:
            lines.append(self.final_answer)
            citations = sorted(extract_chunk_ids_from_answer(self.final_answer))
            if citations:
                lines.append("")
                lines.append(f"  Inline citations: {', '.join(f'`{c}`' for c in citations)}")
            else:
                lines.append("")
                lines.append("  Inline citations: (none - blocked or decline)")
        else:
            lines.append("  (none)")

        lines.append("")
        lines.append("=" * 72)
        return "\n".join(lines)

    @staticmethod
    def _format_score_table(title: str, rows: list[ScoredChunk]) -> list[str]:
        lines = [title + ":"]
        if not rows:
            lines.append("    (empty)")
            return lines
        lines.append(f"    {'rank':>4}  {'chunk_id':<42}  {'score':>10}")
        for row in rows[:10]:
            lines.append(
                f"    {row.rank:>4}  {row.chunk_id:<42}  {row.score:>10.4f}"
            )
        if len(rows) > 10:
            lines.append(f"    ... ({len(rows) - 10} more)")
        return lines

    @staticmethod
    def _format_rerank_table(entries: list) -> list[str]:
        lines = [
            f"    {'chunk_id':<42} {'rank_before':>11} {'score_before':>12} "
            f"{'rank_after':>10} {'score_after':>11}"
        ]
        lines.append("    " + "-" * 90)
        for entry in entries:
            rank_after = str(entry.rank_after) if entry.rank_after is not None else "-"
            score_after = (
                f"{entry.score_after:.4f}"
                if entry.score_after is not None
                else "-"
            )
            lines.append(
                f"    {entry.chunk_id:<42} {entry.rank_before:>11} "
                f"{entry.score_before:>12.4f} {rank_after:>10} {score_after:>11}"
            )
        return lines

    def save(self, directory: Path) -> Path:
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{self.correlation_id}.pipeline.log.json"
        payload: dict[str, Any] = {
            "run_label": self.run_label,
            "correlation_id": self.correlation_id,
            "question": self.question,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "input_guard": asdict(self.input_guard) if self.input_guard else None,
            "retrieval": asdict(self.retrieval) if self.retrieval else None,
            "agent_messages": self.agent_messages,
            "safety_rounds": [asdict(r) for r in self.safety_rounds],
            "final_answer": self.final_answer,
            "regeneration_rounds": self.regeneration_rounds,
            "console": self.format_console(),
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return path
