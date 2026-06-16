from dataclasses import dataclass

from eval.runner import EvalRow, run_evaluate

_STRATEGIES = ["react", "plan_and_execute", "program_of_thought"]


@dataclass
class PairwiseResult:
    rows_by_strategy: dict[str, list[EvalRow]]
    win_matrix: dict[str, dict[str, int]]
    selected_count: int


def _is_row_win(row: EvalRow) -> bool:
    if row.match_type in ("exact", "tolerance"):
        return True
    return bool(row.judge_used and row.judge_is_correct)


def run_pairwise_20(
    *,
    rel_tol: float = 0.01,
    abs_tol: float = 1e-9,
    use_llm_judge: bool = True,
) -> PairwiseResult:
    rows_by_strategy: dict[str, list[EvalRow]] = {}
    for strategy in _STRATEGIES:
        rows, _ = run_evaluate(
            strategy,
            rel_tol=rel_tol,
            abs_tol=abs_tol,
            limit=20,
            use_llm_judge=use_llm_judge,
        )
        rows_by_strategy[strategy] = rows

    selected_count = min(len(v) for v in rows_by_strategy.values()) if rows_by_strategy else 0
    for k in list(rows_by_strategy):
        rows_by_strategy[k] = rows_by_strategy[k][:selected_count]

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

    return PairwiseResult(
        rows_by_strategy=rows_by_strategy,
        win_matrix=win_matrix,
        selected_count=selected_count,
    )

