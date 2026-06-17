"""Binomial accuracy summaries with 95% confidence intervals."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass


@dataclass(frozen=True)
class AccuracyCI:
    correct: int
    total: int
    rate: float
    ci_low: float
    ci_high: float
    method: str = "wilson"

    def format_rate(self, *, digits: int = 1) -> str:
        pct = self.rate * 100
        lo = self.ci_low * 100
        hi = self.ci_high * 100
        return f"{pct:.{digits}f}% [95% CI: {lo:.{digits}f}%–{hi:.{digits}f}%]"


def wilson_ci(
    correct: int,
    total: int,
    *,
    z: float = 1.96,
) -> tuple[float, float]:
    if total <= 0:
        return 0.0, 0.0
    p = correct / total
    z2 = z * z
    denom = 1.0 + z2 / total
    centre = (p + z2 / (2.0 * total)) / denom
    margin = z * math.sqrt((p * (1.0 - p) + z2 / (4.0 * total)) / total) / denom
    return max(0.0, centre - margin), min(1.0, centre + margin)


def bootstrap_ci(
    outcomes: list[bool],
    *,
    samples: int = 1000,
    alpha: float = 0.05,
    seed: int = 0,
) -> tuple[float, float]:
    if not outcomes:
        return 0.0, 0.0
    rng = random.Random(seed)
    n = len(outcomes)
    rates = []
    for _ in range(samples):
        draw = [outcomes[rng.randrange(n)] for _ in range(n)]
        rates.append(sum(draw) / n)
    rates.sort()
    lo_idx = int((alpha / 2.0) * samples)
    hi_idx = int((1.0 - alpha / 2.0) * samples) - 1
    return rates[lo_idx], rates[hi_idx]


def accuracy_ci(
    outcomes: list[bool],
    *,
    method: str = "wilson",
) -> AccuracyCI:
    total = len(outcomes)
    correct = sum(1 for ok in outcomes if ok)
    rate = correct / total if total else 0.0
    if method == "bootstrap":
        lo, hi = bootstrap_ci(outcomes)
        label = "bootstrap"
    else:
        lo, hi = wilson_ci(correct, total)
        label = "wilson"
    return AccuracyCI(
        correct=correct,
        total=total,
        rate=rate,
        ci_low=lo,
        ci_high=hi,
        method=label,
    )


def intervals_overlap(a: AccuracyCI, b: AccuracyCI) -> bool:
    return a.ci_low <= b.ci_high and b.ci_low <= a.ci_high


def pick_winner(
    accuracies: dict[str, AccuracyCI],
    *,
    min_margin: int = 3,
) -> str | None:
    """
    Return a strategy name only when it leads by >= min_margin correct answers
    and its 95% CI does not overlap the runner-up.
    A 2-point lead on 20 examples is not enough to declare a winner.
    """
    if len(accuracies) < 2:
        return None
    ranked = sorted(accuracies.items(), key=lambda item: (-item[1].correct, item[0]))
    best_name, best = ranked[0]
    second_name, second = ranked[1]
    if best.correct == second.correct:
        return None
    if best.correct - second.correct < min_margin:
        return None
    if intervals_overlap(best, second):
        return None
    return best_name
