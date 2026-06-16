"""Active trace context for automatic JSONL logging during strategy runs."""

from __future__ import annotations

from contextlib import asynccontextmanager
from contextvars import ContextVar
from typing import TYPE_CHECKING
from uuid import uuid4

from Observability.logger import EventLogger, default_log_root

if TYPE_CHECKING:
    from strategies.base import Trace, TraceStep


class TraceContext:
    def __init__(
        self,
        *,
        trace_id: str,
        strategy: str,
        problem_id: str,
        question: str,
        logger: EventLogger,
    ):
        self.trace_id = trace_id
        self.strategy = strategy
        self.problem_id = problem_id
        self.question = question
        self.logger = logger


_active_trace: ContextVar[TraceContext | None] = ContextVar(
    "observability_trace", default=None
)
_default_logger = EventLogger()


def get_trace_context() -> TraceContext | None:
    return _active_trace.get()


@asynccontextmanager
async def trace_session(
    strategy: str,
    problem_id: str,
    question: str,
    *,
    logger: EventLogger | None = None,
):
    """Bind a trace id and write run metadata for the duration of solve()."""
    trace_id = str(uuid4())
    event_logger = logger or _default_logger
    ctx = TraceContext(
        trace_id=trace_id,
        strategy=strategy,
        problem_id=problem_id,
        question=question,
        logger=event_logger,
    )
    token = _active_trace.set(ctx)
    event_logger.log_reasoning_step(
        trace_id=trace_id,
        strategy=strategy,
        problem_id=problem_id,
        kind="run_start",
        inputs={"question": question},
        outputs={},
    )
    try:
        yield trace_id
    finally:
        _active_trace.reset(token)


def append_trace_step(trace: Trace, step: TraceStep) -> None:
    """Record an in-memory step and mirror it to reasoning_steps.jsonl when active."""
    trace.steps.append(step)
    ctx = get_trace_context()
    if ctx is None:
        return

    ctx.logger.log_reasoning_step(
        trace_id=ctx.trace_id,
        strategy=ctx.strategy,
        problem_id=ctx.problem_id,
        kind=step.step_type,
        inputs={"data": step.data},
        outputs={"content": step.content},
    )
