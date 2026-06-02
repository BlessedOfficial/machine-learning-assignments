"""Re-run a single problem from a stored trace (replay tooling)."""

from __future__ import annotations

from strategies.base import Problem, Strategy, Trace
from observability.trace_logger import TraceLogger


async def replay_from_trace(
    trace_id: str,
    strategy: Strategy,
    *,
    logger: TraceLogger | None = None,
) -> Trace:
    """
    Load trace events, extract the original question, re-run with the given strategy.
    Returns the new trace (does not mutate the stored trace file).
    """
    log = logger or TraceLogger()
    events = log.load_trace(trace_id)
    if not events:
        raise ValueError(f"Empty trace: {trace_id}")

    problem_id = events[0].problem_id
    question = None
    for event in events:
        if event.step_type in ("llm_call", "reasoning_step", "answer"):
            msgs = event.inputs.get("messages")
            if msgs:
                for msg in reversed(msgs):
                    if msg.get("role") == "user":
                        question = msg["content"]
                        break
        if question:
            break

    if not question:
        raise ValueError(f"Could not extract question from trace {trace_id}")

    problem = Problem(id=problem_id, question=question)
    return await strategy.solve(problem)
