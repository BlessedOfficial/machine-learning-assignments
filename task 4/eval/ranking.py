"""Accuracy, letter grades, and strategy ranking for eval."""

from __future__ import annotations

from dataclasses import dataclass

from eval.metrics import exact_match
from eval.stats import bootstrap_ci, wilson_ci


@dataclass
class StrategyResult:
    strategy: str
    correct: int
    total: int
    ci_low: float | None = None
    ci_high: float | None = None

    @property
    def accuracy(self) -> float:
        return self.correct / self.total if self.total else 0.0

    def with_wilson_ci(self, confidence: float = 0.95) -> StrategyResult:
        low, high = wilson_ci(self.correct, self.total, confidence=confidence)
        self.ci_low, self.ci_high = low, high
        return self

    def with_bootstrap_ci(
        self, outcomes: list[bool], *, confidence: float = 0.95, seed: int = 42
    ) -> StrategyResult:
        low, high = bootstrap_ci(outcomes, confidence=confidence, seed=seed)
        self.ci_low, self.ci_high = low, high
        return self


# Letter grade tiers (accuracy thresholds)
LETTER_GRADES: list[tuple[str, float]] = [
    ("A", 0.90),
    ("B", 0.80),
    ("C", 0.70),
    ("D", 0.60),
    ("F", 0.0),
]


def letter_grade(accuracy: float) -> str:
    for grade, threshold in LETTER_GRADES:
        if accuracy >= threshold:
            return grade
    return "F"


def score_predictions(
    predictions: dict[str, str],
    answers: dict[str, dict],
    *,
    strategy: str,
) -> StrategyResult:
    """Score strategy predictions against held-out answer labels."""
    correct = 0
    total = 0
    for problem_id, label in answers.items():
        total += 1
        pred = predictions.get(problem_id, "")
        if exact_match(pred, label["ground_truth"]):
            correct += 1
    return StrategyResult(strategy=strategy, correct=correct, total=total)


def rank_strategies(results: list[StrategyResult]) -> list[StrategyResult]:
    """Rank by accuracy descending; tie-break by name."""
    return sorted(results, key=lambda r: (-r.accuracy, r.strategy))


def format_results_table(results: list[StrategyResult]) -> str:
    ranked = rank_strategies(results)
    lines = [
        "Strategy              Correct  Total  Accuracy  95% CI           Grade",
        "-" * 72,
    ]
    for r in ranked:
        acc = r.accuracy * 100
        if r.ci_low is not None and r.ci_high is not None:
            ci = f"[{r.ci_low * 100:4.1f}–{r.ci_high * 100:4.1f}%]"
        else:
            ci = "           —"
        lines.append(
            f"{r.strategy:<22}{r.correct:>7}{r.total:>7}{acc:>9.1f}%  {ci}  {letter_grade(r.accuracy)}"
        )
    return "\n".join(lines)


def pairwise_win_matrix(
    per_problem: dict[str, dict[str, bool]],
    strategies: list[str],
) -> dict[str, dict[str, int]]:
    """
    Win matrix: wins[strategy_a][strategy_b] = count of problems where
    a was correct and b was wrong.
    per_problem: {problem_id: {strategy_name: was_correct}}
    """
    matrix = {a: {b: 0 for b in strategies if b != a} for a in strategies}
    for outcomes in per_problem.values():
        for a in strategies:
            for b in strategies:
                if a == b:
                    continue
                if outcomes.get(a) and not outcomes.get(b):
                    matrix[a][b] += 1
    return matrix


def format_win_matrix(matrix: dict[str, dict[str, int]], strategies: list[str]) -> str:
    header = " " * 22 + "".join(f"{s[:12]:>14}" for s in strategies)
    lines = [header]
    for a in strategies:
        row = f"{a[:20]:<22}"
        for b in strategies:
            if a == b:
                row += f"{'—':>14}"
            else:
                row += f"{matrix[a][b]:>14}"
        lines.append(row)
    return "\n".join(lines)
