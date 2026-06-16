import asyncio
import sys
import uuid

from strategies import (
    PlanAndExecuteStrategy,
    Problem,
    ProgramOfThoughtStrategy,
    ReActStrategy,
)
from strategies.utils.golden import load_question

_STRATEGIES = {
    "react": ReActStrategy,
    "plan_and_execute": PlanAndExecuteStrategy,
    "program_of_thought": ProgramOfThoughtStrategy,
}


async def main() -> None:
    strategy_name = "react"
    if len(sys.argv) > 1:
        strategy_name = sys.argv[1].lower().replace("-", "_")

    strategy_cls = _STRATEGIES.get(strategy_name)
    if strategy_cls is None:
        print(f"Unknown strategy: {strategy_name}")
        print(f"Choose from: {', '.join(_STRATEGIES)}")
        return

    if len(sys.argv) > 2:
        ref = sys.argv[2]
        row = load_question(ref)
        if row:
            question = row["question"]
            problem_id = row["id"]
        else:
            question = ref
            problem_id = f"interactive-{uuid.uuid4().hex[:8]}"
    else:
        question = input("Question: ").strip()
        if not question:
            print("No question provided.")
            return
        problem_id = f"interactive-{uuid.uuid4().hex[:8]}"

    trace = await strategy_cls().solve(Problem(id=problem_id, question=question))
    print(f"Graded value: {trace.answer}")


if __name__ == "__main__":
    asyncio.run(main())
