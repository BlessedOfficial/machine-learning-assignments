"""Download GSM8K test split and write questions + answers as separate JSONL files."""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from eval.gsm8k_loader import export_golden_split, export_golden_split_from_combined

DEFAULT_QUESTIONS = ROOT / "data" / "golden" / "gsm8k_test_35_questions.jsonl"
DEFAULT_ANSWERS = ROOT / "data" / "golden" / "gsm8k_test_35_answers.jsonl"
DEFAULT_COMBINED = ROOT / "data" / "golden" / "gsm8k_test_35.jsonl"


def main() -> None:
    parser = argparse.ArgumentParser(description="Build GSM8K golden eval subset")
    parser.add_argument(
        "--questions",
        type=Path,
        default=DEFAULT_QUESTIONS,
        help="Questions JSONL (no answers — for strategies)",
    )
    parser.add_argument(
        "--answers",
        type=Path,
        default=DEFAULT_ANSWERS,
        help="Answers JSONL (labels — for eval / ranking only)",
    )
    parser.add_argument(
        "--from-combined",
        type=Path,
        default=None,
        help="Split existing combined JSONL instead of re-downloading",
    )
    parser.add_argument("-n", "--count", type=int, default=35, help="Number of problems (30–40)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for subset selection")
    args = parser.parse_args()

    if args.from_combined:
        questions, answers = export_golden_split_from_combined(
            args.from_combined, args.questions, args.answers
        )
    else:
        if not 30 <= args.count <= 40:
            parser.error("count must be between 30 and 40")
        questions, answers = export_golden_split(
            args.questions,
            args.answers,
            n=args.count,
            seed=args.seed,
        )

    print(f"Wrote {len(questions)} questions -> {args.questions}")
    print(f"Wrote {len(answers)} answers   -> {args.answers}")


if __name__ == "__main__":
    main()
