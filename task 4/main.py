import asyncio

from llms.client import ask


async def main() -> None:
    question = input("Ask a question:\n").strip()
    if not question:
        print("No question provided.")
        return

    print("\nThinking...\n")
    answer = await ask(question)
    print("Answer:")
    print(answer)


if __name__ == "__main__":
    asyncio.run(main())
