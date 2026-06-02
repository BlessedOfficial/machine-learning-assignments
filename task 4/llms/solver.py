from llms.base import LLMResult, call_llm
from config import SOLVER_MODEL


async def ask(
    question: str,
    *,
    model: str | None = None,
    system: str = "You are a helpful assistant. Answer clearly and concisely.",
    temperature: float = 0.7,
) -> str:
    """Solver LLM — used by all reasoning strategies."""
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": question},
    ]
    result = await call_llm(
        messages,
        model=model or SOLVER_MODEL,
        temperature=temperature,
        role="solver",
    )
    return result.content


async def ask_with_metadata(
    question: str,
    *,
    model: str | None = None,
    system: str = "You are a helpful assistant. Answer clearly and concisely.",
    temperature: float = 0.7,
) -> LLMResult:
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": question},
    ]
    return await call_llm(
        messages,
        model=model or SOLVER_MODEL,
        temperature=temperature,
        role="solver",
    )
