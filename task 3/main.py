import asyncio
import os

from config import DEFAULT_USER_ROLE, PIPELINE_LOG_DIR
from workflow.simple_qa import answer_question


async def main():
    question = input("Ask an AI.Inc question:\n").strip()
    if not question:
        print("No question provided.")
        return

    role = os.getenv("USER_ROLE", DEFAULT_USER_ROLE)
    role_input = input(
        f"Your role (intern/employee/manager/hr/admin) [{role}]: "
    ).strip()
    if role_input:
        role = role_input

    print("\nThinking...\n")
    answer, _, trace_path, pipeline_log = await answer_question(
        question, user_role=role, trace=True
    )

    print("Answer:")
    print(answer)

    if trace_path:
        txt_path = trace_path.with_suffix(".trace.txt")
        print(f"\nAgent trace JSON: {trace_path}")
        if txt_path.is_file():
            print(f"Agent trace TXT:  {txt_path}")
    print(f"Pipeline log:  {PIPELINE_LOG_DIR}/{pipeline_log.correlation_id}.pipeline.log.json")


if __name__ == "__main__":
    asyncio.run(main())
