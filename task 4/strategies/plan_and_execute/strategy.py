import re

from strategies.base import Problem, Trace, TraceStep
from strategies.plan_and_execute.prompts import (
    EXECUTOR_OBSERVATION_TEMPLATE,
    EXECUTOR_SYSTEM_PROMPT,
    EXECUTOR_USER_TEMPLATE,
    PLANNER_SYSTEM_PROMPT,
    PLANNER_USER_TEMPLATE,
    SYNTHESIS_SYSTEM_PROMPT,
    SYNTHESIS_USER_TEMPLATE,
)
from strategies.utils import (
    get_solver_model,
    append_trace_step,
    calculate,
    call_llm,
    log_final_answer,
    log_phase,
    log_plan,
    log_run_header,
    log_step,
    normalize_numeric_answer,
    trace_session,
)
from strategies.utils.answer import extract_finish_value

MAX_PLAN_STEPS = 8
MAX_TOOL_ROUNDS_PER_STEP = 3

_PLAN_LINE_RE = re.compile(r"^\s*(\d+)[\.\)]\s*(.+)$", re.MULTILINE)
_EXEC_ACTION_RE = re.compile(
    r"Action:\s*(calculator\[(.+?)\]|step_done\[(.+?)\]|finish\[(.+?)\])\s*$",
    re.IGNORECASE | re.MULTILINE,
)
_EXEC_THOUGHT_RE = re.compile(
    r"Thought:\s*(.+?)(?=\nAction:|\Z)", re.IGNORECASE | re.DOTALL
)


def _parse_plan(text: str) -> list[str]:
    steps: list[str] = []
    for match in _PLAN_LINE_RE.finditer(text):
        step = match.group(2).strip()
        if step:
            steps.append(step)
    if steps:
        return steps[:MAX_PLAN_STEPS]

    if "plan:" in text.lower():
        block = text.split(":", 1)[-1]
        for line in block.splitlines():
            line = re.sub(r"^\s*\d+[\.\)]\s*", "", line).strip()
            if line:
                steps.append(line)
    return steps[:MAX_PLAN_STEPS] or ["Read the problem and determine what quantity is asked."]


def _parse_executor_turn(text: str) -> tuple[str, str, str | None]:
    thought_match = _EXEC_THOUGHT_RE.search(text)
    thought = thought_match.group(1).strip() if thought_match else ""

    action_match = _EXEC_ACTION_RE.search(text)
    if not action_match:
        return thought, "", None

    raw = action_match.group(0).lower()
    if "calculator" in raw:
        return thought, "calculator", action_match.group(2).strip()
    if "finish" in raw:
        return thought, "finish", action_match.group(4).strip()
    return thought, "step_done", action_match.group(3).strip()


def _run_calculator(expression: str) -> str:
    try:
        return calculate(expression)
    except Exception as e:
        return f"Error: {e}"


class PlanAndExecuteStrategy:
    """Planner produces a step list upfront; executor runs each step with calculator access."""

    name = "plan_and_execute"

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
        log_phase("Planning")
        planner_messages = [
            {
                "role": "system",
                "content": PLANNER_SYSTEM_PROMPT.format(max_plan_steps=MAX_PLAN_STEPS),
            },
            {
                "role": "user",
                "content": PLANNER_USER_TEMPLATE.format(question=problem.question),
            },
        ]
        plan_result = await call_llm(
            planner_messages,
            model=get_solver_model(),
            temperature=0.2,
            role="solver",
        )
        plan_text = plan_result.content
        plan_steps = _parse_plan(plan_text)
        log_plan(plan_steps)

        append_trace_step(
            trace,
            TraceStep(
                step_type="plan",
                content=plan_text,
                data={"steps": plan_steps, "step_count": len(plan_steps)},
            ),
        )

        log_phase("Execution")
        step_results: list[str] = []
        final_answer = ""

        for idx, current_step in enumerate(plan_steps, start=1):
            prior = "\n".join(
                f"- Step {i}: {r}" for i, r in enumerate(step_results, start=1)
            ) or "(none yet)"

            executor_system = EXECUTOR_SYSTEM_PROMPT.format(
                max_tool_rounds=MAX_TOOL_ROUNDS_PER_STEP
            )
            messages: list[dict[str, str]] = [
                {"role": "system", "content": executor_system},
                {
                    "role": "user",
                    "content": EXECUTOR_USER_TEMPLATE.format(
                        question=problem.question,
                        plan=plan_text,
                        prior_results=prior,
                        step_index=idx,
                        step_total=len(plan_steps),
                        current_step=current_step,
                    ),
                },
            ]

            step_outcome = ""
            turn = ""
            round_num = 0
            for _ in range(MAX_TOOL_ROUNDS_PER_STEP + 1):
                round_num += 1
                exec_result = await call_llm(
                    messages,
                    model=get_solver_model(),
                    temperature=0.2,
                    role="solver",
                )
                turn = exec_result.content
                thought, kind, arg = _parse_executor_turn(turn)
                step_label = f"plan {idx}/{len(plan_steps)}"

                if thought:
                    log_step(round_num, f"{step_label} thought", thought)
                    append_trace_step(
                        trace,
                        TraceStep(
                            step_type="thought",
                            content=thought,
                            data={"plan_step": idx},
                        ),
                    )
                if kind:
                    log_step(round_num, f"{step_label} action", turn)
                append_trace_step(
                    trace,
                    TraceStep(
                        step_type="action",
                        content=turn,
                        data={"plan_step": idx, "kind": kind, "arg": arg},
                    ),
                )

                if kind == "finish" and arg:
                    final_answer = normalize_numeric_answer(arg)
                    step_outcome = f"Final answer: {final_answer}"
                    append_trace_step(
                        trace,
                        TraceStep(
                            step_type="final_answer",
                            content=final_answer,
                            data={"plan_step": idx},
                        ),
                    )
                    break

                if kind == "step_done" and arg:
                    step_outcome = arg.strip()
                    log_step(round_num, f"{step_label} result", step_outcome)
                    append_trace_step(
                        trace,
                        TraceStep(
                            step_type="observation",
                            content=f"Step {idx} complete: {step_outcome}",
                            data={"plan_step": idx},
                        ),
                    )
                    break

                if kind == "calculator" and arg:
                    observation = _run_calculator(arg)
                    log_step(round_num, f"{step_label} observation", observation)
                    append_trace_step(
                        trace,
                        TraceStep(
                            step_type="observation",
                            content=observation,
                            data={"plan_step": idx, "tool": "calculator"},
                        ),
                    )
                    messages.append({"role": "assistant", "content": turn})
                    messages.append(
                        {
                            "role": "user",
                            "content": EXECUTOR_OBSERVATION_TEMPLATE.format(
                                result=observation
                            ),
                        }
                    )
                    continue

                observation = "Error: Use calculator[expr], step_done[result], or finish[number]."
                log_step(round_num, f"{step_label} observation", observation)
                append_trace_step(
                    trace,
                    TraceStep(
                        step_type="observation",
                        content=observation,
                        data={"plan_step": idx},
                    ),
                )
                break

            if final_answer:
                break

            if not step_outcome:
                step_outcome = turn.strip() or f"(no result recorded for step {idx})"
            step_results.append(step_outcome)

        if not final_answer:
            log_phase("Synthesis")
            execution_log = "\n".join(
                f"Step {i}: {r}" for i, r in enumerate(step_results, start=1)
            )
            synth_messages = [
                {"role": "system", "content": SYNTHESIS_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": SYNTHESIS_USER_TEMPLATE.format(
                        question=problem.question,
                        plan=plan_text,
                        execution_log=execution_log,
                    ),
                },
            ]
            synth_result = await call_llm(
                synth_messages,
                model=get_solver_model(),
                temperature=0.0,
                role="solver",
            )
            synth_text = synth_result.content
            log_step(1, "synthesis", synth_text)
            raw = extract_finish_value(synth_text) or synth_text.strip()
            final_answer = normalize_numeric_answer(raw)
            append_trace_step(
                trace,
                TraceStep(
                    step_type="synthesis",
                    content=synth_text,
                    data={"extracted": final_answer},
                ),
            )
            append_trace_step(
                trace, TraceStep(step_type="final_answer", content=final_answer)
            )

        return final_answer

