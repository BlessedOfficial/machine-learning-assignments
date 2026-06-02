from strategies.base import Problem, Trace, TraceStep
from llms.client import ask
from tools.code_executor import run_python_code

_POT_SYSTEM = (
    "You are a Program-of-Thought solver. Write Python 3 code that computes the answer "
    "and prints ONLY the final result (one line). No input(), no file/network access. "
    "Return code in a single ```python fenced block."
)


class ProgramOfThoughtStrategy:
    """Generate executable Python and run it to produce the answer (advanced strategy)."""

    name = "program_of_thought"

    async def solve(self, problem: Problem) -> Trace:
        trace = Trace(strategy=self.name, problem_id=problem.id)

        code = await ask(problem.question, system=_POT_SYSTEM)
        trace.steps.append(TraceStep(step_type="program", content=code))

        try:
            output = run_python_code(code)
            trace.steps.append(
                TraceStep(step_type="execution", content=output, data={"ok": True})
            )
            trace.answer = output
        except Exception as e:
            trace.steps.append(
                TraceStep(
                    step_type="execution",
                    content=str(e),
                    data={"ok": False, "error": type(e).__name__},
                )
            )
            trace.answer = ""
        return trace
