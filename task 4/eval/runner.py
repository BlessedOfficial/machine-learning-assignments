import asyncio
from dataclasses import dataclass

from eval.judge import judge_answer
from eval.metrics import GradeResult, grade_math_answer
from strategies import PlanAndExecuteStrategy, Problem, ProgramOfThoughtStrategy, ReActStrategy
from strategies.utils.golden import load_all_answers, load_all_questions


@dataclass
class EvalRow:
    number: int
    problem_id: str
    strategy: str
    prediction: str
    expected: str
    match_type: str
    precision_score: float
    judge_used: bool = False
    judge_is_correct: bool | None = None
    judge_reason: str = ""


_STRATEGIES = {
    "react": ReActStrategy,
    "plan_and_execute": PlanAndExecuteStrategy,
    "program_of_thought": ProgramOfThoughtStrategy,
}


async def evaluate(
    strategy_name: str,
    *,
    rel_tol: float = 0.01,
    abs_tol: float = 1e-9,
    limit: int | None = None,
    use_llm_judge: bool = True,
) -> tuple[list[EvalRow], dict[str, float]]:
    strategy_key = strategy_name.lower().replace("-", "_")
    strategy_cls = _STRATEGIES.get(strategy_key)
    if strategy_cls is None:
        raise ValueError(f"Unknown strategy: {strategy_name}")

    questions = load_all_questions()
    answers = {row["id"]: row for row in load_all_answers()}
    if limit is not None:
        questions = questions[:limit]

    rows: list[EvalRow] = []
    exact = 0
    tolerance = 0
    judge = 0

    for q in questions:
        trace = await strategy_cls().solve(Problem(id=q["id"], question=q["question"]))
        ans = answers[q["id"]]
        result: GradeResult = grade_math_answer(
            trace.answer,
            ans["ground_truth"],
            rel_tol=rel_tol,
            abs_tol=abs_tol,
        )
        judge_used = False
        judge_is_correct: bool | None = None
        judge_reason = ""

        if not result.exact_match and not result.tolerance_match and use_llm_judge:
            verdict = await judge_answer(
                q["question"],
                result.prediction,
                ans["ground_truth"],
            )
            judge_used = True
            judge_is_correct = verdict.is_correct
            judge_reason = verdict.reason

        if result.exact_match:
            exact += 1
        elif result.tolerance_match:
            tolerance += 1
        elif judge_is_correct:
            judge += 1

        rows.append(
            EvalRow(
                number=q["number"],
                problem_id=q["id"],
                strategy=strategy_key,
                prediction=result.prediction,
                expected=result.expected,
                match_type=result.match_type,
                precision_score=result.precision_score,
                judge_used=judge_used,
                judge_is_correct=judge_is_correct,
                judge_reason=judge_reason,
            )
        )

    total = len(rows)
    matched = exact + tolerance + judge
    summary = {
        "total": float(total),
        "exact_count": float(exact),
        "tolerance_count": float(tolerance),
        "judge_count": float(judge),
        "exact_rate": (exact / total) if total else 0.0,
        "tolerance_rate": (tolerance / total) if total else 0.0,
        "judge_rate": (judge / total) if total else 0.0,
        "overall_rate": (matched / total) if total else 0.0,
    }
    return rows, summary


def run_evaluate(*args, **kwargs):
    return asyncio.run(evaluate(*args, **kwargs))
