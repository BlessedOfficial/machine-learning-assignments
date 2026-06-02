import json
import re

from llms.base import LLMResult, call_llm
from config import JUDGE_MODEL, SOLVER_MODEL

_JUDGE_SYSTEM = (
    "You are a strict math answer judge. Compare the predicted answer to the reference. "
    "Ignore formatting differences ($, commas). Accept equivalent numbers (18 vs 18.0). "
    'Respond with JSON only: {"correct": true|false, "reason": "one sentence"}'
)


def _warn_if_collusion() -> None:
    if SOLVER_MODEL.strip() == JUDGE_MODEL.strip():
        raise ValueError(
            "JUDGE_MODEL must differ from SOLVER_MODEL (anti-collusion, same as Task 2 critic)."
        )


def _parse_judge_json(raw: str) -> dict:
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*\n(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if fence:
        text = fence.group(1).strip()
    return json.loads(text)


async def judge_answer(
    question: str,
    prediction: str,
    ground_truth: str,
    *,
    model: str | None = None,
    temperature: float = 0.0,
) -> tuple[bool, str, LLMResult]:
    """
    LLM-as-judge for brittle cases. Uses a different model than the solver.
    Returns (is_correct, reason, llm_result).
    """
    _warn_if_collusion()
    user = (
        f"Question:\n{question}\n\n"
        f"Reference answer:\n{ground_truth}\n\n"
        f"Predicted answer:\n{prediction}\n\n"
        "Is the prediction correct?"
    )
    messages = [
        {"role": "system", "content": _JUDGE_SYSTEM},
        {"role": "user", "content": user},
    ]
    result = await call_llm(
        messages,
        model=model or JUDGE_MODEL,
        temperature=temperature,
        role="judge",
    )
    try:
        parsed = _parse_judge_json(result.content)
        return bool(parsed.get("correct")), str(parsed.get("reason", "")), result
    except (json.JSONDecodeError, TypeError):
        return False, "invalid_judge_output", result
