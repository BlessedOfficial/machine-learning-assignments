"""Replay a single problem from a saved trace ID."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from strategies import (
    PlanAndExecuteStrategy,
    Problem,
    ProgramOfThoughtStrategy,
    ReActStrategy,
)
from strategies.utils.golden import load_answer_by_id, load_question_by_id
from strategies.utils.llm import get_solver_model, solver_model_override

from Observability.logger import default_log_root

_STRATEGIES = {
    "react": ReActStrategy,
    "plan_and_execute": PlanAndExecuteStrategy,
    "program_of_thought": ProgramOfThoughtStrategy,
}


@dataclass(frozen=True)
class TraceRecord:
    trace_id: str
    strategy: str
    problem_id: str
    question: str
    final_answer: str | None
    log_dir: Path
    llm_call_count: int
    tool_call_count: int
    reasoning_step_count: int


@dataclass(frozen=True)
class ReplayResult:
    original: TraceRecord
    replay_trace_id: str
    strategy: str
    model: str
    answer: str
    log_dir: Path


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def _count_events(log_dir: Path, filename: str) -> int:
    return len(_read_jsonl(log_dir / filename))


def trace_log_dir(trace_id: str, *, logs_root: Path | None = None) -> Path:
    root = logs_root or default_log_root()
    path = root / trace_id
    if not path.is_dir():
        raise FileNotFoundError(f"No trace folder for id {trace_id}: {path}")
    return path


def load_trace_record(trace_id: str, *, logs_root: Path | None = None) -> TraceRecord:
    log_dir = trace_log_dir(trace_id, logs_root=logs_root)
    reasoning = _read_jsonl(log_dir / "reasoning_steps.jsonl")
    if not reasoning:
        raise ValueError(f"Trace {trace_id} has no reasoning_steps.jsonl")

    first = reasoning[0]
    strategy = str(first.get("strategy", ""))
    problem_id = str(first.get("problem_id", ""))
    question = ""
    for event in reasoning:
        if event.get("inputs", {}).get("kind") == "run_start":
            question = str(event.get("inputs", {}).get("question", ""))
            break

    if not question and problem_id:
        golden = load_question_by_id(problem_id)
        if golden:
            question = golden["question"]

    if not question:
        raise ValueError(f"Could not resolve question for trace {trace_id}")

    final_answer: str | None = None
    for event in reversed(reasoning):
        if event.get("inputs", {}).get("kind") == "final_answer":
            final_answer = str(event.get("outputs", {}).get("content", "")) or None
            break

    return TraceRecord(
        trace_id=trace_id,
        strategy=strategy,
        problem_id=problem_id,
        question=question,
        final_answer=final_answer,
        log_dir=log_dir,
        llm_call_count=_count_events(log_dir, "llm_calls.jsonl"),
        tool_call_count=_count_events(log_dir, "tool_calls.jsonl"),
        reasoning_step_count=len(reasoning),
    )


def _resolve_strategy(name: str | None, original: str):
    key = (name or original).lower().replace("-", "_")
    strategy_cls = _STRATEGIES.get(key)
    if strategy_cls is None:
        raise ValueError(
            f"Unknown strategy: {name}. Choose from: {', '.join(_STRATEGIES)}"
        )
    return key, strategy_cls


async def replay_trace(
    trace_id: str,
    *,
    strategy: str | None = None,
    model: str | None = None,
    logs_root: Path | None = None,
) -> ReplayResult:
    """Re-run one problem; writes a fresh trace under Observability/logs/."""
    original = load_trace_record(trace_id, logs_root=logs_root)
    strategy_key, strategy_cls = _resolve_strategy(strategy, original.strategy)

    with solver_model_override(model):
        trace = await strategy_cls().solve(
            Problem(id=original.problem_id, question=original.question)
        )

    return ReplayResult(
        original=original,
        replay_trace_id=trace.trace_id,
        strategy=strategy_key,
        model=model or get_solver_model(),
        answer=trace.answer,
        log_dir=trace_log_dir(trace.trace_id, logs_root=logs_root),
    )


def diff_traces(original: TraceRecord, replay: ReplayResult) -> dict:
    replay_record = load_trace_record(replay.replay_trace_id)
    ground_truth = None
    answer_row = load_answer_by_id(original.problem_id)
    if answer_row:
        ground_truth = answer_row.get("ground_truth")

    return {
        "problem_id": original.problem_id,
        "ground_truth": ground_truth,
        "original": {
            "trace_id": original.trace_id,
            "strategy": original.strategy,
            "answer": original.final_answer,
            "llm_calls": original.llm_call_count,
            "tool_calls": original.tool_call_count,
            "reasoning_steps": original.reasoning_step_count,
        },
        "replay": {
            "trace_id": replay.replay_trace_id,
            "strategy": replay.strategy,
            "model": replay.model,
            "answer": replay.answer,
            "llm_calls": replay_record.llm_call_count,
            "tool_calls": replay_record.tool_call_count,
            "reasoning_steps": replay_record.reasoning_step_count,
        },
        "answer_changed": original.final_answer != replay.answer,
    }


def print_replay_summary(result: ReplayResult, *, show_diff: bool = False) -> None:
    original = result.original
    print(f"Original trace: {original.trace_id}")
    print(f"  strategy={original.strategy}  problem={original.problem_id}")
    print(f"  answer={original.final_answer!r}")
    print(f"  log={original.log_dir}")
    print()
    print(f"Replay trace: {result.replay_trace_id}")
    print(f"  strategy={result.strategy}  model={result.model}")
    print(f"  answer={result.answer!r}")
    print(f"  log={result.log_dir}")

    if show_diff:
        diff = diff_traces(original, result)
        print("\nDiff:")
        print(
            f"- llm_calls: {diff['original']['llm_calls']} -> {diff['replay']['llm_calls']}"
        )
        print(
            f"- tool_calls: {diff['original']['tool_calls']} -> {diff['replay']['tool_calls']}"
        )
        print(
            f"- reasoning_steps: {diff['original']['reasoning_steps']} "
            f"-> {diff['replay']['reasoning_steps']}"
        )
        print(f"- answer_changed: {diff['answer_changed']}")
        if diff.get("ground_truth"):
            print(f"- ground_truth: {diff['ground_truth']}")


def main() -> None:
    import argparse
    import asyncio

    parser = argparse.ArgumentParser(
        description="Replay a single problem from an Observability trace ID",
    )
    parser.add_argument("trace_id", help="UUID folder name under Observability/logs/")
    parser.add_argument(
        "--strategy",
        choices=["react", "plan_and_execute", "program_of_thought"],
        help="Override strategy (default: same as original trace)",
    )
    parser.add_argument(
        "--model",
        help="Override solver model for this replay (default: SOLVER_MODEL from .env)",
    )
    parser.add_argument(
        "--show-only",
        action="store_true",
        help="Print original trace metadata without re-running",
    )
    parser.add_argument(
        "--diff",
        action="store_true",
        help="Print event-count and answer diff vs original trace",
    )
    args = parser.parse_args()

    if args.show_only:
        record = load_trace_record(args.trace_id)
        print(f"trace_id: {record.trace_id}")
        print(f"strategy: {record.strategy}")
        print(f"problem_id: {record.problem_id}")
        print(f"question: {record.question}")
        print(f"final_answer: {record.final_answer!r}")
        print(f"log_dir: {record.log_dir}")
        print(f"llm_calls: {record.llm_call_count}")
        print(f"tool_calls: {record.tool_call_count}")
        print(f"reasoning_steps: {record.reasoning_step_count}")
        return

    result = asyncio.run(
        replay_trace(
            args.trace_id,
            strategy=args.strategy,
            model=args.model,
        )
    )
    print_replay_summary(result, show_diff=args.diff)


if __name__ == "__main__":
    main()
