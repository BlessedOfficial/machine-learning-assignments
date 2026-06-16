"""Run adversarial red-team prompts against input guardrails."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from workflow.input_guardrails import guard_user_input, rule_triggered_for_result
from workflow.prompts import OUT_OF_SCOPE_REPLY

DEFAULT_PROMPTS = ROOT / "data" / "redteam" / "prompts.json"


def _actual_decision(result) -> str:
    if not result.allowed:
        return "block"
    if result.pii_redacted:
        return "redact"
    return "allow"


def run_redteam(prompts_path: Path) -> tuple[list[dict], int, int]:
    cases = json.loads(prompts_path.read_text(encoding="utf-8"))
    rows: list[dict] = []
    passed = 0

    for case in cases:
        result = guard_user_input(case["prompt"])
        actual_rule = rule_triggered_for_result(result)
        actual_decision = _actual_decision(result)
        blocked_correctly = (
            not result.allowed
            and result.block_message == OUT_OF_SCOPE_REPLY
        )
        rule_match = actual_rule == case.get("expected_rule")
        decision_match = actual_decision == case.get("expected_decision")
        ok = blocked_correctly and rule_match and decision_match

        if ok:
            passed += 1

        rows.append(
            {
                "id": case["id"],
                "category": case["category"],
                "pass": ok,
                "expected_rule": case.get("expected_rule"),
                "actual_rule": actual_rule,
                "expected_decision": case.get("expected_decision"),
                "actual_decision": actual_decision,
            }
        )

    return rows, passed, len(cases)


def format_markdown_table(rows: list[dict]) -> str:
    lines = [
        "| ID | Category | Expected rule | Result | Pass |",
        "|----|----------|---------------|--------|------|",
    ]
    for row in rows:
        status = "PASS" if row["pass"] else "FAIL"
        lines.append(
            f"| `{row['id']}` | {row['category']} | `{row['expected_rule']}` | "
            f"`{row['actual_rule']}` / {row['actual_decision']} | **{status}** |"
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run red-team guardrail tests.")
    parser.add_argument(
        "--prompts",
        type=Path,
        default=DEFAULT_PROMPTS,
        help="Path to red-team prompts JSON",
    )
    parser.add_argument(
        "--markdown",
        action="store_true",
        help="Print README-ready markdown table",
    )
    args = parser.parse_args()

    rows, passed, total = run_redteam(args.prompts)

    if args.markdown:
        print(format_markdown_table(rows))
        print()
        print(f"**Summary:** {passed}/{total} passed")
    else:
        for row in rows:
            status = "PASS" if row["pass"] else "FAIL"
            print(
                f"{row['id']}: {status} "
                f"(expected {row['expected_rule']}/{row['expected_decision']}, "
                f"got {row['actual_rule']}/{row['actual_decision']})"
            )
        print(f"\n{passed}/{total} passed")

    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
