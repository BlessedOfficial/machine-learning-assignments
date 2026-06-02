"""Statistical tests for strategy comparison (Task 4 spec)."""

from __future__ import annotations

import numpy as np
from scipy import stats


def wilson_ci(correct: int, total: int, confidence: float = 0.95) -> tuple[float, float]:
    """Wilson score interval for binomial proportion."""
    if total == 0:
        return 0.0, 0.0
    z = stats.norm.ppf(1 - (1 - confidence) / 2)
    p = correct / total
    denom = 1 + z**2 / total
    center = (p + z**2 / (2 * total)) / denom
    margin = z * np.sqrt((p * (1 - p) + z**2 / (4 * total)) / total) / denom
    return max(0.0, center - margin), min(1.0, center + margin)


def bootstrap_ci(
    outcomes: list[bool],
    *,
    n_samples: int = 1000,
    confidence: float = 0.95,
    seed: int = 42,
) -> tuple[float, float]:
    """Bootstrap CI for accuracy from per-problem bool outcomes."""
    if not outcomes:
        return 0.0, 0.0
    rng = np.random.default_rng(seed)
    arr = np.array(outcomes, dtype=float)
    n = len(arr)
    samples = []
    for _ in range(n_samples):
        draw = rng.choice(arr, size=n, replace=True)
        samples.append(draw.mean())
    low = float(np.percentile(samples, (1 - confidence) / 2 * 100))
    high = float(np.percentile(samples, (1 + confidence) / 2 * 100))
    return low, high


def mcnemar_test(
    strategy_a_correct: list[bool],
    strategy_b_correct: list[bool],
) -> tuple[float, float]:
    """
    McNemar's test for paired strategy comparison.
    Returns (statistic, p_value). Exact binomial when b+c < 25.
    """
    if len(strategy_a_correct) != len(strategy_b_correct):
        raise ValueError("Outcome lists must have equal length")
    a = np.array(strategy_a_correct, dtype=bool)
    b = np.array(strategy_b_correct, dtype=bool)
    b_count = int(np.sum(a & ~b))  # A correct, B wrong
    c_count = int(np.sum(~a & b))  # A wrong, B correct
    n = b_count + c_count
    if n == 0:
        return 0.0, 1.0

    if n < 25:
        p_value = float(stats.binomtest(b_count, n, 0.5, alternative="two-sided").pvalue)
        stat = float((b_count - c_count) ** 2 / n)
    else:
        stat = float((abs(b_count - c_count) - 1) ** 2 / n)
        p_value = float(stats.chi2.sf(stat, df=1))
    return stat, p_value
