"""LLM-as-judge eval helpers + human agreement sanity check."""

from __future__ import annotations

from dataclasses import dataclass

from eval.metrics import exact_match
from llms.judge import judge_answer


@dataclass
class JudgeAgreementReport:
    checked: int
    agree: int
    agreement_rate: float
    details: list[dict]

    @property
    def passes_sanity(self) -> bool:
        """Spec: fix rubric if judge agrees with human < 70%."""
        return self.agreement_rate >= 0.70


async def grade_with_judge(
    question: str,
    prediction: str,
    ground_truth: str,
    *,
    use_exact_first: bool = True,
) -> tuple[bool, str, str]:
    """
    Grade a prediction: exact match first, then LLM judge fallback.
    Returns (correct, method, reason).
    """
    if use_exact_first and exact_match(prediction, ground_truth):
        return True, "exact_match", "numeric exact match"
    is_correct, reason, _ = await judge_answer(question, prediction, ground_truth)
    return is_correct, "llm_judge", reason


async def sanity_check_judge(
    samples: list[dict],
    *,
    human_labels: dict[str, bool] | None = None,
) -> JudgeAgreementReport:
    """
    Compare LLM judge to human labels on a small hand-graded subset.
    Each sample: {id, question, prediction, ground_truth, human_correct?}
    """
    details: list[dict] = []
    agree = 0
    for row in samples:
        pid = row["id"]
        human = (
            row["human_correct"]
            if "human_correct" in row
            else human_labels[pid]
            if human_labels
            else exact_match(row["prediction"], row["ground_truth"])
        )
        judge_ok, reason, _ = await judge_answer(
            row["question"], row["prediction"], row["ground_truth"]
        )
        matches = judge_ok == human
        agree += int(matches)
        details.append(
            {
                "id": pid,
                "human_correct": human,
                "judge_correct": judge_ok,
                "agree": matches,
                "reason": reason,
            }
        )
    n = len(samples)
    return JudgeAgreementReport(
        checked=n,
        agree=agree,
        agreement_rate=agree / n if n else 0.0,
        details=details,
    )
