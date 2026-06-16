import re

from strategies.react.prompts import (
    OBSERVATION_TEMPLATE,
    REACT_SYSTEM_PROMPT,
    REACT_USER_TEMPLATE,
)
from strategies.base import Problem, Trace, TraceStep
from strategies.utils import (
    SOLVER_MODEL,
    append_trace_step,
    calculate,
    call_llm,
    log_final_answer,
    log_run_header,
    log_step,
    normalize_numeric_answer,
    trace_session,
)

MAX_STEPS = 8

_ACTION_RE = re.compile(
    r"Action:\s*(calculator\[(.+?)\]|finish\[(.+?)\])\s*$",
    re.IGNORECASE | re.MULTILINE,
)
_THOUGHT_RE = re.compile(r"Thought:\s*(.+?)(?=\nAction:|\Z)", re.IGNORECASE | re.DOTALL)


def _parse_turn(text: str) -> tuple[str, str, str | None]:
    """Return (thought, action_kind, action_arg). action_kind is 'calculator'|'finish'."""
    thought_match = _THOUGHT_RE.search(text)
    thought = thought_match.group(1).strip() if thought_match else ""

    action_match = _ACTION_RE.search(text)
    if not action_match:
        return thought, "", None

    if action_match.group(1).lower().startswith("calculator"):
        return thought, "calculator", action_match.group(2).strip()
    return thought, "finish", action_match.group(3).strip()


def _run_tool(kind: str, arg: str | None) -> str:
    if kind == "calculator" and arg:
        try:
            return calculate(arg)
        except Exception as e:
            return f"Error: {e}"
    if kind == "finish" and arg:
        return f"Submitted final answer: {arg.strip()}"
    return "Error: Unrecognized action. Use calculator[expr] or finish[number]."


class ReActStrategy:
    """Reason–Act–Observe loop with calculator tool for GSM8K math problems."""

    name = "react"

    async def solve(self, problem: Problem) -> Trace:
        trace = Trace(strategy=self.name, problem_id=problem.id)
        log_run_header(
            strategy=self.name,
            problem_id=problem.id,
            question=problem.question,
        )
        async with trace_session(self.name, problem.id, problem.question) as trace_id:
            trace.trace_id = trace_id
            final_answer = await self._run(trace, problem)
        trace.answer = log_final_answer(final_answer)
        return trace

    async def _run(self, trace: Trace, problem: Problem) -> str:
        system = REACT_SYSTEM_PROMPT.format(max_steps=MAX_STEPS)
        messages: list[dict[str, str]] = [
            {"role": "system", "content": system},
            {"role": "user", "content": REACT_USER_TEMPLATE.format(question=problem.question)},
        ]

        final_answer = ""
        turn = ""
        for step in range(1, MAX_STEPS + 1):
            result = await call_llm(
                messages,
                model=SOLVER_MODEL,
                temperature=0.2,
                role="solver",
            )
            turn = result.content
            thought, kind, arg = _parse_turn(turn)

            if thought:
                log_step(step, "thought", thought)
                append_trace_step(trace, TraceStep(step_type="thought", content=thought))
            if kind:
                log_step(step, "action", turn)
            append_trace_step(
                trace, TraceStep(step_type="action", content=turn, data={"kind": kind, "arg": arg})
            )

            if kind == "finish" and arg:
                final_answer = normalize_numeric_answer(arg)
                append_trace_step(
                    trace,
                    TraceStep(
                        step_type="final_answer",
                        content=final_answer,
                        data={"step": step},
                    ),
                )
                break

            observation = _run_tool(kind, arg)
            log_step(step, "observation", observation)
            append_trace_step(trace, TraceStep(step_type="observation", content=observation))

            messages.append({"role": "assistant", "content": turn})
            messages.append(
                {"role": "user", "content": OBSERVATION_TEMPLATE.format(result=observation)}
            )

        if not final_answer:
            for s in reversed(trace.steps):
                if s.step_type == "observation" and not s.content.startswith("Error"):
                    raw = s.content.replace("Submitted final answer: ", "").strip()
                    final_answer = normalize_numeric_answer(raw)
                    break
            if not final_answer:
                final_answer = normalize_numeric_answer(turn)

        return final_answer
