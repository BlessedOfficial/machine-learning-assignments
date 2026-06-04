import re

from config import SOLVER_MODEL
from llms.base import call_llm
from strategies.base import Problem, Trace, TraceStep
from strategies.program_of_thought.prompts import (
    POT_EXECUTION_OBSERVATION_TEMPLATE,
    POT_PARSE_RETRY_USER_TEMPLATE,
    POT_RETRY_USER_TEMPLATE,
    POT_SYSTEM_PROMPT,
    POT_USER_TEMPLATE,
)
from tools.code_executor import extract_python_code, run_python_code

MAX_RETRIES = 2

_REASONING_RE = re.compile(
    r"Reasoning:\s*(.+?)(?=```|\Z)", re.IGNORECASE | re.DOTALL
)
_NUMBER_RE = re.compile(r"^-?\d+(?:\.\d+)?$")


def _extract_reasoning(text: str) -> str:
    match = _REASONING_RE.search(text)
    return match.group(1).strip() if match else ""


def _extract_code(text: str) -> str:
    return extract_python_code(text)


def _normalize_answer(stdout: str) -> str:
    """Take the last non-empty line and coerce to a gradable numeric string."""
    lines = [ln.strip() for ln in stdout.strip().splitlines() if ln.strip()]
    if not lines:
        return ""
    candidate = lines[-1]
    # Strip common prefixes: "Answer: 14", "$125"
    candidate = re.sub(r"^[\$£]?\s*", "", candidate)
    candidate = re.sub(
        r"^(?:answer|result)\s*[:=]\s*", "", candidate, flags=re.IGNORECASE
    ).strip()
    if _NUMBER_RE.fullmatch(candidate):
        value = float(candidate)
        if value.is_integer():
            return str(int(value))
        return candidate
    # Last resort: first number in the line
    nums = re.findall(r"-?\d+(?:\.\d+)?", candidate)
    if nums:
        value = float(nums[-1])
        if value.is_integer():
            return str(int(value))
        return nums[-1]
    return candidate


def _is_gradable(stdout: str) -> bool:
    return bool(_normalize_answer(stdout))


class ProgramOfThoughtStrategy:
    """Generate Python, execute in sandbox, grade from stdout (Program-of-Thought)."""

    name = "program_of_thought"

    async def solve(self, problem: Problem) -> Trace:
        trace = Trace(strategy=self.name, problem_id=problem.id)
        messages: list[dict[str, str]] = [
            {"role": "system", "content": POT_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": POT_USER_TEMPLATE.format(question=problem.question),
            },
        ]

        final_answer = ""
        code = ""
        raw_response = ""

        for attempt in range(MAX_RETRIES + 1):
            result = await call_llm(
                messages,
                model=SOLVER_MODEL,
                temperature=0.2 if attempt == 0 else 0.1,
                role="solver",
            )
            raw_response = result.content
            reasoning = _extract_reasoning(raw_response)
            code = _extract_code(raw_response)

            if reasoning:
                trace.steps.append(
                    TraceStep(step_type="thought", content=reasoning, data={"attempt": attempt + 1})
                )
            trace.steps.append(
                TraceStep(
                    step_type="code",
                    content=code or raw_response,
                    data={"attempt": attempt + 1},
                )
            )

            if not code:
                error = "No ```python``` code block found in the response."
                trace.steps.append(
                    TraceStep(step_type="observation", content=error, data={"attempt": attempt + 1})
                )
                if attempt >= MAX_RETRIES:
                    break
                messages.append({"role": "assistant", "content": raw_response})
                messages.append(
                    {
                        "role": "user",
                        "content": POT_RETRY_USER_TEMPLATE.format(
                            question=problem.question,
                            previous_code="",
                            error=error,
                        ),
                    }
                )
                continue

            try:
                stdout = run_python_code(code)
                trace.steps.append(
                    TraceStep(
                        step_type="observation",
                        content=POT_EXECUTION_OBSERVATION_TEMPLATE.format(stdout=stdout),
                        data={"attempt": attempt + 1, "success": True},
                    )
                )
            except Exception as e:
                error = str(e).strip()
                trace.steps.append(
                    TraceStep(
                        step_type="observation",
                        content=f"Execution error: {error}",
                        data={"attempt": attempt + 1, "success": False},
                    )
                )
                if attempt >= MAX_RETRIES:
                    break
                messages.append({"role": "assistant", "content": raw_response})
                messages.append(
                    {
                        "role": "user",
                        "content": POT_RETRY_USER_TEMPLATE.format(
                            question=problem.question,
                            previous_code=code,
                            error=error,
                        ),
                    }
                )
                continue

            if _is_gradable(stdout):
                final_answer = _normalize_answer(stdout)
                trace.steps.append(
                    TraceStep(
                        step_type="final_answer",
                        content=final_answer,
                        data={"attempt": attempt + 1, "stdout": stdout},
                    )
                )
                break

            if attempt >= MAX_RETRIES:
                final_answer = _normalize_answer(stdout)
                trace.steps.append(
                    TraceStep(
                        step_type="final_answer",
                        content=final_answer,
                        data={"attempt": attempt + 1, "stdout": stdout, "parsed": False},
                    )
                )
                break

            messages.append({"role": "assistant", "content": raw_response})
            messages.append(
                {
                    "role": "user",
                    "content": POT_PARSE_RETRY_USER_TEMPLATE.format(
                        question=problem.question,
                        previous_code=code,
                        stdout=stdout or "(empty)",
                    ),
                }
            )

        if not final_answer:
            final_answer = _normalize_answer(raw_response) or raw_response.strip()

        trace.answer = final_answer
        return trace
