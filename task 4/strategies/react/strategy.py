from strategies.base import Problem, Trace, TraceStep
from llms.client import ask


class ReActStrategy:
    """Reason–Act–Observe loop with tool use (stub — implement loop next)."""

    name = "react"

    async def solve(self, problem: Problem) -> Trace:
        trace = Trace(strategy=self.name, problem_id=problem.id)

        # Placeholder: direct LLM answer until ReAct loop + tools are wired.
        answer = await ask(
            problem.question,
            system=(
                "You are a ReAct-style agent. Think step by step, then give a final answer."
            ),
        )
        trace.steps.append(TraceStep(step_type="answer", content=answer))
        trace.answer = answer
        return trace
