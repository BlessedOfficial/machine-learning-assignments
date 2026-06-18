"""Append new GSM8K test problems to data/golden/ (folders N+1, N+2, ...)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from eval.gsm8k_loader import GSM8K_TEST_SPLIT, _row_to_record, load_gsm8k_rows
from strategies.utils.golden import golden_root, list_problem_numbers


def _used_source_indices(root: Path) -> set[int]:
    used: set[int] = set()
    for number in list_problem_numbers():
        question_path = root / str(number) / "questions" / "question.json"
        row = json.loads(question_path.read_text(encoding="utf-8"))
        if "source_index" in row:
            used.add(int(row["source_index"]))
    return used


def extend_golden_set(*, count: int, seed: int = 42) -> list[int]:
    root = golden_root()
    used = _used_source_indices(root)
    ds = load_gsm8k_rows()
    candidates = [idx for idx in range(len(ds)) if idx not in used]
    if len(candidates) < count:
        raise ValueError(
            f"Only {len(candidates)} unused GSM8K test rows left; requested {count}."
        )

    import random

    rng = random.Random(seed)
    rng.shuffle(candidates)
    chosen = sorted(candidates[:count])

    start_number = max(list_problem_numbers(), default=0) + 1
    added_numbers: list[int] = []

    for offset, source_index in enumerate(chosen):
        number = start_number + offset
        record = _row_to_record(ds[source_index], split=GSM8K_TEST_SPLIT, index=source_index)
        record["number"] = number

        problem_dir = root / str(number)
        question_dir = problem_dir / "questions"
        answer_dir = problem_dir / "answers"
        question_dir.mkdir(parents=True, exist_ok=True)
        answer_dir.mkdir(parents=True, exist_ok=True)

        question_path = question_dir / "question.json"
        answer_path = answer_dir / "answer.json"
        question_path.write_text(
            json.dumps(
                {
                    "number": number,
                    "id": record["id"],
                    "question": record["question"],
                    "source_index": record["source_index"],
                    "split": record["split"],
                },
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        answer_path.write_text(
            json.dumps(
                {
                    "number": number,
                    "id": record["id"],
                    "ground_truth": record["ground_truth"],
                    "full_solution": record["full_solution"],
                },
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        added_numbers.append(number)

    return added_numbers


def main() -> None:
    parser = argparse.ArgumentParser(description="Append GSM8K problems to data/golden/")
    parser.add_argument(
        "-n",
        "--count",
        type=int,
        default=15,
        help="How many new problems to add (default: 15)",
    )
    parser.add_argument("--seed", type=int, default=42, help="Shuffle seed for selection")
    args = parser.parse_args()

    if args.count < 1:
        parser.error("count must be >= 1")

    added = extend_golden_set(count=args.count, seed=args.seed)
    print(f"Added {len(added)} problems: folders {added[0]}–{added[-1]}")


if __name__ == "__main__":
    main()
