"""Retry LangChain/OpenRouter calls on transient API failures."""

import re
import time
from typing import Any, TypeVar

T = TypeVar("T")

_TRANSIENT_MARKERS = (
    "500",
    "502",
    "503",
    "504",
    "429",
    "rate limit",
    "internal server error",
    "overloaded",
    "timeout",
    "temporarily unavailable",
)


class RateLimitExhaustedError(RuntimeError):
    """OpenRouter free-tier daily quota is exhausted; retries will not help."""


def is_daily_quota_exhausted(exc: BaseException) -> bool:
    message = str(exc).lower()
    if "free-models-per-day" not in message:
        return False
    if "x-ratelimit-remaining': '0'" in message:
        return True
    if re.search(r"x-ratelimit-remaining['\"]:\s*['\"]0['\"]", message):
        return True
    return "add 10 credits" in message


def is_transient_llm_error(exc: BaseException) -> bool:
    if is_daily_quota_exhausted(exc):
        return False
    message = str(exc).lower()
    if any(marker in message for marker in _TRANSIENT_MARKERS):
        return True
    if isinstance(exc, ValueError) and isinstance(exc.args[0], dict):
        code = exc.args[0].get("code")
        if code in (429, 500, 502, 503, 504):
            return True
    return False


def _retry_delay_s(exc: BaseException, attempt: int, base_delay_s: float) -> float:
    message = str(exc).lower()
    if "free-models-per-min" in message or "429" in message:
        return max(65.0, base_delay_s * (2**attempt))
    return base_delay_s * (2**attempt)


def invoke_with_retry(
    runnable: Any,
    inputs: dict[str, Any],
    *,
    max_attempts: int = 5,
    base_delay_s: float = 2.0,
    label: str = "LLM",
) -> T:
    last_exc: BaseException | None = None
    for attempt in range(max_attempts):
        try:
            return runnable.invoke(inputs)
        except Exception as exc:
            last_exc = exc
            if is_daily_quota_exhausted(exc):
                raise RateLimitExhaustedError(
                    "OpenRouter free-model daily limit reached (50/day). "
                    "Use `scripts/run_chunking.py --local` for zero API calls, "
                    "add OpenRouter credits, or wait until the quota resets."
                ) from exc
            if not is_transient_llm_error(exc) or attempt >= max_attempts - 1:
                raise
            delay = _retry_delay_s(exc, attempt, base_delay_s)
            print(
                f"  {label} unavailable; "
                f"retry {attempt + 2}/{max_attempts} in {delay:.0f}s..."
            )
            time.sleep(delay)
    assert last_exc is not None
    raise last_exc
