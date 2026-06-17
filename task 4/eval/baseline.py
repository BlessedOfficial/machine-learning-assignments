"""Load, save, and diff evaluation baselines."""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from typing import Any

from eval.stats import accuracy_ci, pick_winner

DEFAULT_BASELINE_PATH = Path(__file__).resolve().parents[1] / "data" / "eval" / "baseline.json"
_STRATEGIES = ("react", "plan_and_execute", "program_of_thought")
_OUTCOME_LINE = re.compile(
    r"^-\s+#(?P<number>\d+)\s+(?P<problem_id>\S+):\s+"
    r"react=(?P<react>\w+),\s+"
    r"plan_and_execute=(?P<plan_and_execute>\w+),\s+"
    r"program_of_thought=(?P<program_of_thought>\w+)\s*$"
)
_WIN_MATRIX_ROW = re.compile(
    r"^(?P<strategy>\S+)\s+(?P<react>\d+)\s+(?P<plan_and_execute>\d+)\s+(?P<program_of_thought>\d+)\s*$"
)


def _is_win(match_type: str) -> bool:
    return match_type in ("exact", "tolerance")


def _strategy_accuracy(outcomes: list[str]) -> dict[str, Any]:
    acc = accuracy_ci([_is_win(value) for value in outcomes])
    return {
        "correct": acc.correct,
        "total": acc.total,
        "rate": round(acc.rate, 6),
        "ci_low": round(acc.ci_low, 6),
        "ci_high": round(acc.ci_high, 6),
        "ci_method": acc.method,
    }


def record_from_pairwise_result(result) -> dict[str, Any]:
    per_problem = []
    for i in range(result.selected_count):
        row = {
            "number": result.rows_by_strategy["react"][i].number,
            "problem_id": result.rows_by_strategy["react"][i].problem_id,
            "outcomes": {
                strategy: result.rows_by_strategy[strategy][i].match_type
                for strategy in _STRATEGIES
            },
        }
        per_problem.append(row)

    strategies = {
        strategy: {
            "correct": acc.correct,
            "total": acc.total,
            "rate": round(acc.rate, 6),
            "ci_low": round(acc.ci_low, 6),
            "ci_high": round(acc.ci_high, 6),
            "ci_method": acc.method,
        }
        for strategy, acc in result.accuracy_by_strategy.items()
    }

    return {
        "schema_version": 1,
        "recorded_at": date.today().isoformat(),
        "label": f"pairwise-{result.requested_count}",
        "run": {
            "kind": "pairwise",
            "limit": result.requested_count,
            "comparable_count": result.selected_count,
        },
        "declared_winner": result.winner,
        "strategies": strategies,
        "win_matrix": result.win_matrix,
        "per_problem": per_problem,
    }


def record_from_console_log(log_path: Path) -> dict[str, Any]:
    text = log_path.read_text(encoding="utf-8")
    per_problem: list[dict[str, Any]] = []
    win_matrix: dict[str, dict[str, int]] = {s: {b: 0 for b in _STRATEGIES} for s in _STRATEGIES}
    in_matrix = False

    for line in text.splitlines():
        outcome = _OUTCOME_LINE.match(line.strip())
        if outcome:
            per_problem.append(
                {
                    "number": int(outcome.group("number")),
                    "problem_id": outcome.group("problem_id"),
                    "outcomes": {
                        "react": outcome.group("react"),
                        "plan_and_execute": outcome.group("plan_and_execute"),
                        "program_of_thought": outcome.group("program_of_thought"),
                    },
                }
            )
            continue

        if line.strip().startswith("Pairwise win matrix"):
            in_matrix = True
            continue

        if in_matrix:
            row = _WIN_MATRIX_ROW.match(line.strip())
            if row and row.group("strategy") in _STRATEGIES:
                name = row.group("strategy")
                win_matrix[name] = {
                    "react": int(row.group("react")),
                    "plan_and_execute": int(row.group("plan_and_execute")),
                    "program_of_thought": int(row.group("program_of_thought")),
                }
            elif line.strip().startswith("Traces:"):
                break

    if not per_problem:
        raise ValueError(f"No per-problem outcomes found in {log_path}")

    strategies = {
        strategy: _strategy_accuracy([row["outcomes"][strategy] for row in per_problem])
        for strategy in _STRATEGIES
    }
    accuracies = {
        strategy: accuracy_ci([_is_win(row["outcomes"][strategy]) for row in per_problem])
        for strategy in _STRATEGIES
    }

    return {
        "schema_version": 1,
        "recorded_at": date.today().isoformat(),
        "label": f"pairwise-{len(per_problem)}-from-log",
        "run": {
            "kind": "pairwise",
            "limit": len(per_problem),
            "comparable_count": len(per_problem),
            "source": str(log_path),
        },
        "declared_winner": pick_winner(accuracies, min_margin=3),
        "strategies": strategies,
        "win_matrix": win_matrix,
        "per_problem": per_problem,
    }


def load_baseline(path: Path | None = None) -> dict[str, Any]:
    baseline_path = path or DEFAULT_BASELINE_PATH
    with baseline_path.open(encoding="utf-8") as handle:
        return json.load(handle)


def save_baseline(record: dict[str, Any], path: Path | None = None) -> Path:
    baseline_path = path or DEFAULT_BASELINE_PATH
    baseline_path.parent.mkdir(parents=True, exist_ok=True)
    with baseline_path.open("w", encoding="utf-8") as handle:
        json.dump(record, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    return baseline_path


def diff_baselines(baseline: dict[str, Any], current: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    base_strategies = baseline.get("strategies", {})
    curr_strategies = current.get("strategies", {})

    for strategy in _STRATEGIES:
        base = base_strategies.get(strategy)
        curr = curr_strategies.get(strategy)
        if base is None or curr is None:
            rows.append(
                {
                    "strategy": strategy,
                    "status": "missing",
                    "baseline": base,
                    "current": curr,
                }
            )
            continue

        correct_delta = curr["correct"] - base["correct"]
        rate_delta = curr["rate"] - base["rate"]
        rows.append(
            {
                "strategy": strategy,
                "status": "changed" if correct_delta != 0 else "unchanged",
                "baseline": base,
                "current": curr,
                "correct_delta": correct_delta,
                "rate_delta": rate_delta,
            }
        )

    return rows


def print_baseline_diff(
    baseline: dict[str, Any],
    current: dict[str, Any],
    *,
    baseline_label: str,
) -> None:
    print(f"\nBaseline diff (current vs {baseline_label}):")
    print(
        f"- comparable: {baseline.get('run', {}).get('comparable_count')} "
        f"-> {current.get('run', {}).get('comparable_count')}"
    )

    for row in diff_baselines(baseline, current):
        strategy = row["strategy"]
        if row["status"] == "missing":
            print(f"- {strategy}: missing in baseline or current")
            continue

        base = row["baseline"]
        curr = row["current"]
        if row["status"] == "unchanged":
            print(
                f"- {strategy}: unchanged "
                f"({curr['correct']}/{curr['total']} = {curr['rate'] * 100:.1f}%)"
            )
            continue

        sign = "+" if row["correct_delta"] > 0 else ""
        print(
            f"- {strategy}: {base['correct']}/{base['total']} "
            f"({base['rate'] * 100:.1f}%) -> {curr['correct']}/{curr['total']} "
            f"({curr['rate'] * 100:.1f}%) "
            f"[{sign}{row['correct_delta']} correct, {row['rate_delta'] * 100:+.1f} pp]"
        )

    base_winner = baseline.get("declared_winner")
    curr_winner = current.get("declared_winner")
    if base_winner != curr_winner:
        print(f"- declared winner: {base_winner!r} -> {curr_winner!r}")

    changed_problems = _changed_problems(baseline, current)
    if changed_problems:
        print("- per-problem regressions/improvements:")
        for item in changed_problems[:10]:
            print(
                f"  - #{item['number']:02d} {item['problem_id']} "
                f"{item['strategy']}: {item['baseline']} -> {item['current']}"
            )
        if len(changed_problems) > 10:
            print(f"  - ... and {len(changed_problems) - 10} more")


def _changed_problems(
    baseline: dict[str, Any],
    current: dict[str, Any],
) -> list[dict[str, Any]]:
    base_by_id = {row["problem_id"]: row for row in baseline.get("per_problem", [])}
    curr_by_id = {row["problem_id"]: row for row in current.get("per_problem", [])}
    changes: list[dict[str, Any]] = []

    for problem_id in sorted(set(base_by_id) & set(curr_by_id)):
        base_row = base_by_id[problem_id]
        curr_row = curr_by_id[problem_id]
        for strategy in _STRATEGIES:
            base_outcome = base_row["outcomes"][strategy]
            curr_outcome = curr_row["outcomes"][strategy]
            if base_outcome != curr_outcome:
                changes.append(
                    {
                        "number": curr_row["number"],
                        "problem_id": problem_id,
                        "strategy": strategy,
                        "baseline": base_outcome,
                        "current": curr_outcome,
                    }
                )
    return changes
