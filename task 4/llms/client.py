import asyncio

from openrouter import OpenRouter

from config import OPENROUTER_API_KEY, SOLVER_MODEL

if not OPENROUTER_API_KEY:
    raise ValueError("API key not found. Set OPENROUTER_API_KEY in .env")

_client = OpenRouter(api_key=OPENROUTER_API_KEY)


async def ask(
    question: str,
    *,
    model: str | None = None,
    system: str = "You are a helpful assistant. Answer clearly and concisely.",
    temperature: float = 0.7,
) -> str:
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": question},
    ]
    chosen_model = model or SOLVER_MODEL

    for attempt in range(3):
        try:
            response = await asyncio.to_thread(
                _client.chat.send,
                model=chosen_model,
                messages=messages,
                temperature=temperature,
            )
            if not response.choices:
                raise ValueError("No choices returned")
            return (response.choices[0].message.content or "").strip()
        except Exception as e:
            if attempt == 2:
                raise RuntimeError(f"LLM call failed ({chosen_model}): {e}") from e
            await asyncio.sleep(1)

    return ""
