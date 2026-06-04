import asyncio
import uuid

from strategies import PlanAndExecuteStrategy, Problem


def _print_trace(trace) -> None:
    for step in trace.steps:
        label = step.step_type.replace("_", " ").title()
        print(f"  [{label}] {step.content}")


async def main() -> None:
    question = input("Ask a math question:\n").strip()
    if not question:
        print("No question provided.")
        return

    print("\nPlan-and-Execute solving...\n")
    trace = await PlanAndExecuteStrategy().solve(
        Problem(id=f"interactive-{uuid.uuid4().hex[:8]}", question=question)
    )

    _print_trace(trace)
    print("\nAnswer:")
    print(trace.answer)


if __name__ == "__main__":
    asyncio.run(main())
