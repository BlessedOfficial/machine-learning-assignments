from dataclasses import dataclass, field

from eval.runner import EvalRow, run_evaluate
from eval.stats import AccuracyCI, accuracy_ci, pick_winner

_STRATEGIES = ["react", "plan_and_execute", "program_of_thought"]


@dataclass
class PairwiseResult:
    rows_by_strategy: dict[str, list[EvalRow]]
    win_matrix: dict[str, dict[str, int]]
    selected_count: int
    requested_count: int
    accuracy_by_strategy: dict[str, AccuracyCI] = field(default_factory=dict)
    winner: str | None = None
    completed_by_strategy: dict[str, int] = field(default_factory=dict)
    aborted_by_strategy: dict[str, bool] = field(default_factory=dict)
    abort_reasons: dict[str, str] = field(default_factory=dict)


def _is_row_win(row: EvalRow) -> bool:
    if row.match_type in ("exact", "tolerance"):
        return True
    return bool(row.judge_used and row.judge_is_correct)


def run_pairwise(
    *,
    limit: int = 4,
    offset: int = 0,
    rel_tol: float = 0.01,
    abs_tol: float = 1e-9,
    use_llm_judge: bool = True,
    stop_on_quota: bool = True,
) -> PairwiseResult:
    rows_by_strategy: dict[str, list[EvalRow]] = {}
    completed_by_strategy: dict[str, int] = {}
    aborted_by_strategy: dict[str, bool] = {}
    abort_reasons: dict[str, str] = {}

    for strategy in _STRATEGIES:
        rows, summary = run_evaluate(
            strategy,
            rel_tol=rel_tol,
            abs_tol=abs_tol,
            limit=limit,
            offset=offset,
            use_llm_judge=use_llm_judge,
            stop_on_quota=stop_on_quota,
        )
        rows_by_strategy[strategy] = rows
        completed_by_strategy[strategy] = len(rows)
        aborted_by_strategy[strategy] = bool(summary.get("aborted"))
        abort_reasons[strategy] = str(summary.get("abort_reason") or "")

    selected_count = min(len(v) for v in rows_by_strategy.values()) if rows_by_strategy else 0
    for key in list(rows_by_strategy):
        rows_by_strategy[key] = rows_by_strategy[key][:selected_count]

    win_matrix: dict[str, dict[str, int]] = {
        a: {b: 0 for b in _STRATEGIES} for a in _STRATEGIES
    }

    # Cell (A, B): #problems where A solved and B did not.
    for i in range(selected_count):
        solved = {s: _is_row_win(rows_by_strategy[s][i]) for s in _STRATEGIES}
        for a in _STRATEGIES:
            for b in _STRATEGIES:
                if a == b:
                    continue
                if solved[a] and not solved[b]:
                    win_matrix[a][b] += 1

    accuracy_by_strategy = {
        strategy: accuracy_ci([_is_row_win(row) for row in rows])
        for strategy, rows in rows_by_strategy.items()
    }
    winner = pick_winner(accuracy_by_strategy, min_margin=3)

    return PairwiseResult(
        rows_by_strategy=rows_by_strategy,
        win_matrix=win_matrix,
        selected_count=selected_count,
        requested_count=limit,
        accuracy_by_strategy=accuracy_by_strategy,
        winner=winner,
        completed_by_strategy=completed_by_strategy,
        aborted_by_strategy=aborted_by_strategy,
        abort_reasons=abort_reasons,
    )


def run_pairwise_20(**kwargs) -> PairwiseResult:
    """Backward-compatible alias for a 20-question pairwise run."""
    return run_pairwise(limit=20, **kwargs)
