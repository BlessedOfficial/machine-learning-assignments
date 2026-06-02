import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import TRACE_LOG_DIR


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class TraceEvent:
    timestamp: str
    trace_id: str
    strategy: str
    problem_id: str
    step_type: str  # llm_call | tool_call | reasoning_step | eval
    inputs: dict[str, Any] = field(default_factory=dict)
    outputs: dict[str, Any] = field(default_factory=dict)
    model: str | None = None
    tokens_in: int | None = None
    tokens_out: int | None = None
    latency_ms: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class TraceLogger:
    """Hand-rolled JSONL trace store (OpenTelemetry-style fields, no external deps)."""

    def __init__(self, log_dir: Path | None = None):
        self.log_dir = Path(log_dir or TRACE_LOG_DIR)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def new_trace_id(self) -> str:
        return str(uuid.uuid4())

    def append(self, event: TraceEvent) -> Path:
        path = self.log_dir / f"{event.trace_id}.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(event), ensure_ascii=False) + "\n")
        return path

    def log_llm_call(
        self,
        *,
        trace_id: str,
        strategy: str,
        problem_id: str,
        step_type: str,
        messages: list[dict],
        result_content: str,
        model: str,
        tokens_in: int | None,
        tokens_out: int | None,
        latency_ms: float,
        metadata: dict | None = None,
    ) -> Path:
        return self.append(
            TraceEvent(
                timestamp=_utc_now(),
                trace_id=trace_id,
                strategy=strategy,
                problem_id=problem_id,
                step_type=step_type,
                inputs={"messages": messages},
                outputs={"content": result_content},
                model=model,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                latency_ms=latency_ms,
                metadata=metadata or {},
            )
        )

    def load_trace(self, trace_id: str) -> list[TraceEvent]:
        path = self.log_dir / f"{trace_id}.jsonl"
        if not path.exists():
            raise FileNotFoundError(f"No trace: {trace_id}")
        events: list[TraceEvent] = []
        with path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    events.append(TraceEvent(**json.loads(line)))
        return events

    def list_traces(self) -> list[str]:
        return sorted(p.stem for p in self.log_dir.glob("*.jsonl"))
