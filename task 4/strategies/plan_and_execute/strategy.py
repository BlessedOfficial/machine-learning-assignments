import re

from config import SOLVER_MODEL
from llms.base import call_llm
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
from tools.calculator import calculate

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
_FINISH_RE = re.compile(r"finish\[(.+?)\]", re.IGNORECASE)


def _parse_plan(text: str) -> list[str]:
    steps: list[str] = []
    for match in _PLAN_LINE_RE.finditer(text):
        step = match.group(2).strip()
        if step:
            steps.append(step)
    if steps:
        return steps[:MAX_PLAN_STEPS]

    # Fallback: non-empty lines after "Plan:"
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


def _extract_finish(text: str) -> str:
    match = _FINISH_RE.search(text)
    return match.group(1).strip() if match else ""


class PlanAndExecuteStrategy:
    """Planner produces a step list upfront; executor runs each step with calculator access."""

    name = "plan_and_execute"

    async def solve(self, problem: Problem) -> Trace:
        trace = Trace(strategy=self.name, problem_id=problem.id)

        # --- Phase 1: Plan ---
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
            model=SOLVER_MODEL,
            temperature=0.2,
            role="solver",
        )
        plan_text = plan_result.content
        plan_steps = _parse_plan(plan_text)

        trace.steps.append(
            TraceStep(
                step_type="plan",
                content=plan_text,
                data={"steps": plan_steps, "step_count": len(plan_steps)},
            )
        )

        # --- Phase 2: Execute each plan step ---
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
            for _ in range(MAX_TOOL_ROUNDS_PER_STEP + 1):
                exec_result = await call_llm(
                    messages,
                    model=SOLVER_MODEL,
                    temperature=0.2,
                    role="solver",
                )
                turn = exec_result.content
                thought, kind, arg = _parse_executor_turn(turn)

                if thought:
                    trace.steps.append(
                        TraceStep(
                            step_type="thought",
                            content=thought,
                            data={"plan_step": idx},
                        )
                    )
                trace.steps.append(
                    TraceStep(
                        step_type="action",
                        content=turn,
                        data={"plan_step": idx, "kind": kind, "arg": arg},
                    )
                )

                if kind == "finish" and arg:
                    final_answer = arg.strip()
                    step_outcome = f"Final answer: {final_answer}"
                    trace.steps.append(
                        TraceStep(
                            step_type="final_answer",
                            content=final_answer,
                            data={"plan_step": idx},
                        )
                    )
                    break

                if kind == "step_done" and arg:
                    step_outcome = arg.strip()
                    trace.steps.append(
                        TraceStep(
                            step_type="observation",
                            content=f"Step {idx} complete: {step_outcome}",
                            data={"plan_step": idx},
                        )
                    )
                    break

                if kind == "calculator" and arg:
                    observation = _run_calculator(arg)
                    trace.steps.append(
                        TraceStep(
                            step_type="observation",
                            content=observation,
                            data={"plan_step": idx, "tool": "calculator"},
                        )
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

                trace.steps.append(
                    TraceStep(
                        step_type="observation",
                        content="Error: Use calculator[expr], step_done[result], or finish[number].",
                        data={"plan_step": idx},
                    )
                )
                break

            if final_answer:
                break

            if not step_outcome:
                step_outcome = turn.strip() or f"(no result recorded for step {idx})"
            step_results.append(step_outcome)

        # --- Phase 3: Synthesize final number if not finished ---
        if not final_answer:
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
                model=SOLVER_MODEL,
                temperature=0.0,
                role="solver",
            )
            synth_text = synth_result.content
            final_answer = _extract_finish(synth_text) or synth_text.strip()
            trace.steps.append(
                TraceStep(
                    step_type="synthesis",
                    content=synth_text,
                    data={"extracted": final_answer},
                )
            )
            trace.steps.append(
                TraceStep(step_type="final_answer", content=final_answer)
            )

        trace.answer = final_answer
        return trace
