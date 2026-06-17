import asyncio
import time
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any, Iterator

from openrouter import OpenRouter

from Observability.context import get_trace_context
from strategies.utils.config import (
    LLM_MAX_RETRIES,
    LLM_REQUEST_TIMEOUT_SEC,
    LLM_RETRY_BASE_SEC,
    OPENROUTER_API_KEY,
    SOLVER_MODEL,
)

if not OPENROUTER_API_KEY:
    raise ValueError("API key not found. Set OPENROUTER_API_KEY in .env")

_client = OpenRouter(api_key=OPENROUTER_API_KEY)
_solver_model_override: ContextVar[str | None] = ContextVar(
    "solver_model_override", default=None
)


def get_solver_model() -> str:
    override = _solver_model_override.get()
    return override if override else SOLVER_MODEL


@contextmanager
def solver_model_override(model: str | None) -> Iterator[None]:
    """Temporarily route strategy LLM calls through a different model."""
    if model is None:
        yield
        return
    token = _solver_model_override.set(model)
    try:
        yield
    finally:
        _solver_model_override.reset(token)


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


def is_rate_limit_error(exc: Exception) -> bool:
    name = type(exc).__name__.lower()
    msg = str(exc).lower()
    return (
        "toomanyrequests" in name
        or "rate" in msg
        or "429" in msg
        or "quota" in msg
        or "capacity" in msg
        or "overloaded" in msg
    )


def is_quota_exhausted_error(exc: Exception) -> bool:
    """True when further LLM calls are unlikely to succeed (quota/credits/tokens)."""
    msg = str(exc).lower()
    return is_rate_limit_error(exc) or any(
        token in msg
        for token in (
            "free-models-per-day",
            "insufficient",
            "credit",
            "exhausted",
            "billing",
            "payment",
            "spend limit",
        )
    )


def retry_delay_sec(attempt: int, exc: Exception) -> float:
    base = LLM_RETRY_BASE_SEC
    if is_rate_limit_error(exc):
        return base * (2**attempt)
    return base * (attempt + 1)


async def call_llm(
    messages: list[dict[str, str]],
    *,
    model: str,
    temperature: float = 0.7,
    role: str = "solver",
) -> LLMResult:
    started = time.perf_counter()
    last_error: Exception | None = None

    for attempt in range(LLM_MAX_RETRIES):
        try:
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    _client.chat.send,
                    model=model,
                    messages=messages,
                    temperature=temperature,
                ),
                timeout=LLM_REQUEST_TIMEOUT_SEC,
            )
            if not response.choices:
                raise ValueError("No choices returned")

            content = (response.choices[0].message.content or "").strip()
            tokens_in, tokens_out, raw_usage = _extract_usage(response)
            latency_ms = (time.perf_counter() - started) * 1000
            result = LLMResult(
                content=content,
                model=model,
                latency_ms=latency_ms,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                raw_usage=raw_usage,
            )
            ctx = get_trace_context()
            if ctx is not None:
                ctx.logger.log_llm_call(
                    trace_id=ctx.trace_id,
                    strategy=ctx.strategy,
                    problem_id=ctx.problem_id,
                    inputs={"messages": messages, "role": role, "temperature": temperature},
                    outputs={"content": content, "usage": raw_usage},
                    model=model,
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                    latency_ms=latency_ms,
                )
            return result
        except Exception as e:
            last_error = e
            if attempt >= LLM_MAX_RETRIES - 1:
                break
            delay = retry_delay_sec(attempt, e)
            print(
                f"  [llm] {role} retry {attempt + 1}/{LLM_MAX_RETRIES - 1} "
                f"after {delay:.0f}s ({type(e).__name__})",
                flush=True,
            )
            await asyncio.sleep(delay)

    raise RuntimeError(
        f"LLM call failed ({role}/{model}): {last_error}"
    ) from last_error
