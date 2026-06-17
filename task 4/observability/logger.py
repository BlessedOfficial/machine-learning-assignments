"""Append-only JSONL event logs (one file per event category per run)."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_LOG_ROOT = Path(__file__).resolve().parent / "logs"

# Maps high-level categories to JSONL filenames inside each trace folder.
_CATEGORY_FILES = {
    "llm_call": "llm_calls.jsonl",
    "tool_call": "tool_calls.jsonl",
    "reasoning_step": "reasoning_steps.jsonl",
}


def default_log_root() -> Path:
    return _LOG_ROOT


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class TraceEvent:
    timestamp: str
    trace_id: str
    strategy: str
    problem_id: str
    step_type: str
    inputs: dict[str, Any] = field(default_factory=dict)
    outputs: dict[str, Any] = field(default_factory=dict)
    tokens_in: int | None = None
    tokens_out: int | None = None
    latency_ms: float | None = None
    model: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        payload = asdict(self)
        # Drop null model to keep lines compact when unused.
        if payload.get("model") is None:
            payload.pop("model", None)
        return json.dumps(payload, ensure_ascii=False)


class EventLogger:
    """Writes structured events to category-specific JSONL files per trace."""

    def __init__(self, root: Path | None = None):
        self.root = root or _LOG_ROOT
        self.root.mkdir(parents=True, exist_ok=True)

    def trace_dir(self, trace_id: str) -> Path:
        path = self.root / trace_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def log_event(self, event: TraceEvent) -> None:
        filename = _CATEGORY_FILES.get(event.step_type)
        if filename is None:
            raise ValueError(f"Unknown step_type for logging: {event.step_type}")

        path = self.trace_dir(event.trace_id) / filename
        with path.open("a", encoding="utf-8") as handle:
            handle.write(event.to_json() + "\n")

    def log_llm_call(
        self,
        *,
        trace_id: str,
        strategy: str,
        problem_id: str,
        inputs: dict[str, Any],
        outputs: dict[str, Any],
        model: str,
        tokens_in: int | None,
        tokens_out: int | None,
        latency_ms: float,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.log_event(
            TraceEvent(
                timestamp=_utc_now(),
                trace_id=trace_id,
                strategy=strategy,
                problem_id=problem_id,
                step_type="llm_call",
                inputs=inputs,
                outputs=outputs,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                latency_ms=latency_ms,
                model=model,
                metadata=metadata or {},
            )
        )

    def log_tool_call(
        self,
        *,
        trace_id: str,
        strategy: str,
        problem_id: str,
        tool: str,
        inputs: dict[str, Any],
        outputs: dict[str, Any],
        latency_ms: float,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.log_event(
            TraceEvent(
                timestamp=_utc_now(),
                trace_id=trace_id,
                strategy=strategy,
                problem_id=problem_id,
                step_type="tool_call",
                inputs={"tool": tool, **inputs},
                outputs=outputs,
                latency_ms=latency_ms,
                metadata=metadata or {},
            )
        )

    def log_reasoning_step(
        self,
        *,
        trace_id: str,
        strategy: str,
        problem_id: str,
        kind: str,
        inputs: dict[str, Any],
        outputs: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.log_event(
            TraceEvent(
                timestamp=_utc_now(),
                trace_id=trace_id,
                strategy=strategy,
                problem_id=problem_id,
                step_type="reasoning_step",
                inputs={"kind": kind, **inputs},
                outputs=outputs,
                metadata=metadata or {},
            )
        )
