import asyncio
import time
from dataclasses import dataclass
from typing import Any

from openrouter import OpenRouter

from config import OPENROUTER_API_KEY

if not OPENROUTER_API_KEY:
    raise ValueError("API key not found. Set OPENROUTER_API_KEY in .env")

_client = OpenRouter(api_key=OPENROUTER_API_KEY)


@dataclass
class LLMResult:
    content: str
    model: str
    latency_ms: float
    tokens_in: int | None = None
    tokens_out: int | None = None
    raw_usage: dict[str, Any] | None = None


def _extract_usage(response) -> tuple[int | None, int | None, dict | None]:
    usage = getattr(response, "usage", None)
    if usage is None:
        return None, None, None
    if isinstance(usage, dict):
        return usage.get("prompt_tokens"), usage.get("completion_tokens"), usage
    prompt = getattr(usage, "prompt_tokens", None)
    completion = getattr(usage, "completion_tokens", None)
    raw = {
        "prompt_tokens": prompt,
        "completion_tokens": completion,
        "total_tokens": getattr(usage, "total_tokens", None),
    }
    return prompt, completion, raw


async def call_llm(
    messages: list[dict[str, str]],
    *,
    model: str,
    temperature: float = 0.7,
    role: str = "solver",
) -> LLMResult:
    started = time.perf_counter()
    last_error: Exception | None = None

    for attempt in range(3):
        try:
            response = await asyncio.to_thread(
                _client.chat.send,
                model=model,
                messages=messages,
                temperature=temperature,
            )
            if not response.choices:
                raise ValueError("No choices returned")

            content = (response.choices[0].message.content or "").strip()
            tokens_in, tokens_out, raw_usage = _extract_usage(response)
            latency_ms = (time.perf_counter() - started) * 1000

            return LLMResult(
                content=content,
                model=model,
                latency_ms=latency_ms,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                raw_usage=raw_usage,
            )
        except Exception as e:
            last_error = e
            if attempt == 2:
                break
            await asyncio.sleep(1)

    raise RuntimeError(f"LLM call failed ({role}/{model}): {last_error}") from last_error
