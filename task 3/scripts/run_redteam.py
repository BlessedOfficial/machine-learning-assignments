"""Run adversarial red-team prompts against input guardrails."""

import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from workflow.input_guardrails import (
    guard_user_input,
    guard_user_input_hybrid,
    rule_triggered_for_result,
)
from workflow.prompts import OUT_OF_SCOPE_REPLY

DEFAULT_PROMPTS = ROOT / "data" / "redteam" / "prompts.json"
DEFAULT_SNIPPET = ROOT / "data" / "redteam" / "results.md"


def _actual_decision(result) -> str:
    if not result.allowed:
        return "block"
    if result.pii_redacted:
        return "redact"
    return "allow"


def _evaluate_case(case: dict, result) -> bool:
    actual_rule = rule_triggered_for_result(result)
    actual_decision = _actual_decision(result)
    expected_rule = case.get("expected_rule")
    expected_decision = case.get("expected_decision")

    if expected_decision == "allow":
        return result.allowed and actual_decision == "allow"

    if expected_decision == "redact":
        return (
            result.allowed
            and result.pii_redacted
            and actual_rule == expected_rule
        )

    if expected_decision == "block":
        blocked = not result.allowed
        message_ok = (
            result.block_message == OUT_OF_SCOPE_REPLY
            if result.block_message
            else True
        )
        rule_ok = actual_rule == expected_rule
        return blocked and message_ok and rule_ok

    return False


def _filter_cases(cases: list[dict], *, with_llm: bool) -> list[dict]:
    if with_llm:
        return cases
    return [c for c in cases if not c.get("requires_llm")]


async def _run_one(case: dict, *, with_llm: bool):
    if with_llm:
        return await guard_user_input_hybrid(case["prompt"])
    return guard_user_input(case["prompt"])


async def run_redteam_async(
    prompts_path: Path,
    *,
    with_llm: bool,
) -> tuple[list[dict], int, int]:
    cases = json.loads(prompts_path.read_text(encoding="utf-8"))
    cases = _filter_cases(cases, with_llm=with_llm)
    rows: list[dict] = []
    passed = 0

    for case in cases:
        result = await _run_one(case, with_llm=with_llm)
        actual_rule = rule_triggered_for_result(result)
        actual_decision = _actual_decision(result)
        ok = _evaluate_case(case, result)
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


def run_redteam(prompts_path: Path, *, with_llm: bool = False) -> tuple[list[dict], int, int]:
    return asyncio.run(run_redteam_async(prompts_path, with_llm=with_llm))


def format_markdown_table(rows: list[dict], *, title: str) -> str:
    lines = [
        f"### {title}",
        "",
        "| ID | Category | Expected rule | Result | Pass |",
        "|----|----------|---------------|--------|------|",
    ]
    for row in rows:
        status = "PASS" if row["pass"] else "FAIL"
        expected_rule = row["expected_rule"] or "(none)"
        lines.append(
            f"| `{row['id']}` | {row['category']} | `{expected_rule}` | "
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
        "--with-llm",
        action="store_true",
        help="Run hybrid guard (rules + LLM input reviewer); includes requires_llm cases",
    )
    parser.add_argument(
        "--markdown",
        action="store_true",
        help="Print README-ready markdown table",
    )
    parser.add_argument(
        "--write-readme-snippet",
        type=Path,
        nargs="?",
        const=DEFAULT_SNIPPET,
        help="Write markdown results to data/redteam/results.md",
    )
    args = parser.parse_args()

    rows, passed, total = run_redteam(args.prompts, with_llm=args.with_llm)
    mode = "hybrid (rules + LLM)" if args.with_llm else "rules-only"

    if args.write_readme_snippet:
        snippet = format_markdown_table(rows, title=f"Red-team ({mode})")
        snippet += f"\n\n**Summary:** {passed}/{total} passed\n"
        args.write_readme_snippet.parent.mkdir(parents=True, exist_ok=True)
        args.write_readme_snippet.write_text(snippet + "\n", encoding="utf-8")
        print(f"Wrote {args.write_readme_snippet}")

    if args.markdown:
        print(format_markdown_table(rows, title=f"Red-team ({mode})"))
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
        print(f"\n{passed}/{total} passed ({mode})")

    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
