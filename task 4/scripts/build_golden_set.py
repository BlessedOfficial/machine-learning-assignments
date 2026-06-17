"""Download GSM8K test split and write a fixed random golden subset to JSONL."""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from eval.gsm8k_loader import export_golden_jsonl

DEFAULT_PATH = ROOT / "data" / "golden" / "gsm8k_test_35.jsonl"


def main() -> None:
    parser = argparse.ArgumentParser(description="Build GSM8K golden eval subset")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=DEFAULT_PATH,
        help="Output JSONL path",
    )
    parser.add_argument("-n", "--count", type=int, default=35, help="Number of problems (30–40)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for subset selection")
    args = parser.parse_args()

    if not 30 <= args.count <= 40:
        parser.error("count must be between 30 and 40")

    records = export_golden_jsonl(args.output, n=args.count, seed=args.seed)
    print(f"Wrote {len(records)} problems to {args.output}")


if __name__ == "__main__":
    main()
