from strategies.base import Problem, Trace, TraceStep
from llms.client import ask


class PlanAndExecuteStrategy:
    """Planner produces steps upfront; executor runs each step (stub)."""

    name = "plan_and_execute"

    async def solve(self, problem: Problem) -> Trace:
        trace = Trace(strategy=self.name, problem_id=problem.id)

        plan = await ask(
            problem.question,
            system=(
                "You are a planner. Break the problem into numbered steps only. "
                "Do not solve yet."
            ),
        )
        trace.steps.append(TraceStep(step_type="plan", content=plan))

        answer = await ask(
            f"Problem:\n{problem.question}\n\nPlan:\n{plan}\n\nExecute the plan and give the final answer.",
            system="You are an executor. Follow the plan and return only the final answer.",
        )
        trace.steps.append(TraceStep(step_type="execute", content=answer))
        trace.answer = answer
        return trace
