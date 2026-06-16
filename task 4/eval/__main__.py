import argparse
import asyncio

from eval.judge import run_judge_sanity_check
from eval.pairwise import run_pairwise_20
from eval.runner import run_evaluate


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate Task 4 strategies on golden math set")
    parser.add_argument(
        "--strategy",
        default="react",
        choices=["react", "plan_and_execute", "program_of_thought"],
    )
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--rel-tol", type=float, default=0.01)
    parser.add_argument("--abs-tol", type=float, default=1e-9)
    parser.add_argument("--no-judge-fallback", action="store_true")
    parser.add_argument("--judge-sanity-only", action="store_true")
    parser.add_argument("--pairwise-20", action="store_true")
    args = parser.parse_args()

    if args.judge_sanity_only:
        agreement, rows = asyncio.run(run_judge_sanity_check())
        print(f"Judge sanity agreement: {agreement:.1%}")
        for row in rows:
            marker = "PASS" if row["agree"] else "FAIL"
            print(
                f"- {row['id']}: {marker} "
                f"(judge={row['judge_is_correct']}, human={row['human_is_correct']})"
            )
        return

    if args.pairwise_20:
        result = run_pairwise_20(
            rel_tol=args.rel_tol,
            abs_tol=args.abs_tol,
            use_llm_judge=not args.no_judge_fallback,
        )
        print(f"Selected questions: {result.selected_count}")
        print("\nPer-problem outcomes (first 20):")
        for i in range(result.selected_count):
            react = result.rows_by_strategy["react"][i]
            pae = result.rows_by_strategy["plan_and_execute"][i]
            pot = result.rows_by_strategy["program_of_thought"][i]
            print(
                f"- #{react.number:02d} {react.problem_id}: "
                f"react={react.match_type}, "
                f"plan_and_execute={pae.match_type}, "
                f"program_of_thought={pot.match_type}"
            )
        print("\nPairwise win matrix (A solved, B missed):")
        header = "strategy".ljust(22) + "".join(s.rjust(22) for s in result.win_matrix)
        print(header)
        for a, row in result.win_matrix.items():
            print(a.ljust(22) + "".join(str(row[b]).rjust(22) for b in result.win_matrix))
        return

    rows, summary = run_evaluate(
        args.strategy,
        rel_tol=args.rel_tol,
        abs_tol=args.abs_tol,
        limit=args.limit,
        use_llm_judge=not args.no_judge_fallback,
    )

    print(f"Strategy: {args.strategy}")
    print(f"Total: {int(summary['total'])}")
    print(f"Exact matches: {int(summary['exact_count'])} ({summary['exact_rate']:.1%})")
    print(f"Tolerance matches: {int(summary['tolerance_count'])} ({summary['tolerance_rate']:.1%})")
    print(f"Judge fallback matches: {int(summary['judge_count'])} ({summary['judge_rate']:.1%})")
    print(f"Overall matched: {summary['overall_rate']:.1%}")

    print("\nSample results:")
    for row in rows[: min(10, len(rows))]:
        print(
            f"- #{row.number:02d} {row.problem_id}: "
            f"pred={row.prediction} expected={row.expected} "
            f"[{row.match_type}, precision={row.precision_score:.4f}]"
        )


if __name__ == "__main__":
    main()
