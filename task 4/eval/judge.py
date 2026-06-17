import json
from dataclasses import dataclass
from pathlib import Path

from strategies.utils import JUDGE_MODEL, call_llm

_SANITY_PATH = Path(__file__).resolve().parents[1] / "data" / "eval" / "judge_sanity_samples.jsonl"


@dataclass
class JudgeVerdict:
    is_correct: bool
    reason: str


def _parse_judge_output(text: str) -> JudgeVerdict:
    stripped = text.strip()
    if stripped.startswith("{"):
        try:
            parsed = json.loads(stripped)
            verdict = parsed.get("is_correct", False) is True
            reason = str(parsed.get("reason", "")).strip()
            return JudgeVerdict(is_correct=verdict, reason=reason)
        except json.JSONDecodeError:
            return JudgeVerdict(
                is_correct=False,
                reason="unparseable_json_from_judge",
            )

    # Strict mode: non-JSON output is treated as judge failure (not correct).
    return JudgeVerdict(is_correct=False, reason="non_json_judge_output")


async def judge_answer(question: str, prediction: str, expected: str) -> JudgeVerdict:
    system = (
        "You are a strict math grading judge.\n"
        "You must return JSON only with this exact schema:\n"
        '{"is_correct": true|false, "reason": "<short_reason>"}\n'
        "Rubric:\n"
        "1) Mark true only when predicted answer is mathematically equivalent to expected.\n"
        "2) Be conservative: if uncertain, mark false.\n"
        "3) Ignore cosmetic formatting differences only (spaces, optional '$', "
        "prefix like 'Answer:', trailing .0).\n"
        "4) Do not give credit for near-miss approximations unless the question explicitly "
        "asks for approximation.\n"
        "5) If predicted answer includes multiple conflicting numbers, mark false."
    )
    user = (
        f"Question:\n{question}\n\n"
        f"Expected answer:\n{expected}\n\n"
        f"Predicted answer:\n{prediction}\n\n"
        "Judge correctness for grading."
    )
    result = await call_llm(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        model=JUDGE_MODEL,
        temperature=0.0,
        role="judge",
    )
    return _parse_judge_output(result.content)


def load_judge_sanity_samples(path: Path | None = None) -> list[dict]:
    p = path or _SANITY_PATH
    rows: list[dict] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


async def run_judge_sanity_check(
    *,
    min_examples: int = 8,
    min_agreement: float = 0.70,
    path: Path | None = None,
) -> tuple[float, list[dict]]:
    samples = load_judge_sanity_samples(path)
    if len(samples) < min_examples:
        raise ValueError(
            f"Need at least {min_examples} judge sanity examples, found {len(samples)}"
        )

    agreed = 0
    rows: list[dict] = []
    for sample in samples:
        verdict = await judge_answer(
            sample["question"],
            sample["prediction"],
            sample["expected"],
        )
        human = bool(sample["human_is_correct"])
        is_agree = verdict.is_correct == human
        if is_agree:
            agreed += 1
        rows.append(
            {
                "id": sample["id"],
                "judge_is_correct": verdict.is_correct,
                "human_is_correct": human,
                "agree": is_agree,
                "judge_reason": verdict.reason,
            }
        )

    acc = agreed / len(samples)
    if acc < min_agreement:
        raise RuntimeError(
            f"Judge sanity failed: agreement={acc:.1%} < {min_agreement:.0%}. "
            "Fix judge rubric before trusting numbers."
        )
    return acc, rows
