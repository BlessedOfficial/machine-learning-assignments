import argparse
import asyncio
from pathlib import Path

from eval.baseline import (
    DEFAULT_BASELINE_PATH,
    load_baseline,
    print_baseline_diff,
    record_from_console_log,
    record_from_pairwise_result,
    save_baseline,
)
from eval.console_log import tee_console
from eval.judge import run_judge_sanity_check
from eval.pairwise import run_pairwise
from eval.runner import run_evaluate
from eval.stats import accuracy_ci

_PAIRWISE_CONSOLE_LOG = Path(__file__).resolve().parent / "pairwise_20_console_output.txt"
_TRACE_ROOT = Path(__file__).resolve().parents[1] / "Observability" / "logs"


def _pairwise_log_path(offset: int, limit: int) -> Path:
    start = offset + 1
    end = offset + limit
    return Path(__file__).resolve().parent / f"pairwise_{start:02d}_{end:02d}_console_output.txt"


def _print_pairwise_result(result, *, console_log: Path, trace_root: Path) -> None:
    print(f"Requested questions: {result.requested_count}")
    print(f"Comparable questions: {result.selected_count}")
    print("\nCompleted per strategy:")
    for strategy, count in result.completed_by_strategy.items():
        aborted = result.aborted_by_strategy.get(strategy, False)
        suffix = " (stopped early — quota/tokens)" if aborted else ""
        print(f"- {strategy}: {count}/{result.requested_count}{suffix}")
    if any(result.aborted_by_strategy.values()):
        print("\nAbort reasons:")
        for strategy, reason in result.abort_reasons.items():
            if result.aborted_by_strategy.get(strategy) and reason:
                print(f"- {strategy}: {reason[:200]}")

    print("\nAccuracy with 95% Wilson CI:")
    for strategy in result.accuracy_by_strategy:
        acc = result.accuracy_by_strategy[strategy]
        print(
            f"- {strategy}: {acc.correct}/{acc.total} = {acc.format_rate()} "
            f"({acc.method})"
        )
    if result.winner:
        print(f"\nDeclared winner: {result.winner}")
    else:
        print(
            "\nDeclared winner: none "
            "(need >=3 correct margin and non-overlapping 95% CIs; "
            "a 2-point lead on 20 examples is not enough)"
        )

    print(f"\nPer-problem outcomes ({result.selected_count}):")
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

    trace_ids = sorted(
        {
            row.trace_id
            for rows in result.rows_by_strategy.values()
            for row in rows
            if row.trace_id
        }
    )
    print(f"\nTraces: {len(trace_ids)} run(s) under {trace_root}")
    print(f"Console log: {console_log}")
    if trace_ids:
        print("Sample trace folders:")
        for trace_id in trace_ids[:5]:
            print(f"- {trace_root / trace_id}")
        if len(trace_ids) > 5:
            print(f"- ... and {len(trace_ids) - 5} more")


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate Task 4 strategies on golden math set")
    parser.add_argument(
        "--strategy",
        default="react",
        choices=["react", "plan_and_execute", "program_of_thought"],
    )
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument(
        "--offset",
        type=int,
        default=0,
        help="Skip the first N golden problems (0-based folder order)",
    )
    parser.add_argument("--rel-tol", type=float, default=0.01)
    parser.add_argument("--abs-tol", type=float, default=1e-9)
    parser.add_argument("--no-judge-fallback", action="store_true")
    parser.add_argument("--judge-sanity-only", action="store_true")
    parser.add_argument(
        "--pairwise",
        action="store_true",
        help="Run all strategies on the same golden subset and print a win matrix",
    )
    parser.add_argument(
        "--pairwise-limit",
        type=int,
        default=4,
        help="Number of golden problems for --pairwise (default: 4)",
    )
    parser.add_argument(
        "--pairwise-20",
        action="store_true",
        help="Alias for --pairwise --pairwise-limit 20",
    )
    parser.add_argument(
        "--compare-baseline",
        action="store_true",
        help="After pairwise eval, print delta vs data/eval/baseline.json",
    )
    parser.add_argument(
        "--diff-baseline-log",
        nargs="?",
        const=str(_PAIRWISE_CONSOLE_LOG),
        default=None,
        metavar="LOG",
        help="Diff baseline against per-problem outcomes in a console log (no API calls)",
    )
    parser.add_argument(
        "--write-baseline",
        nargs="?",
        const=str(DEFAULT_BASELINE_PATH),
        default=None,
        metavar="PATH",
        help="Write baseline.json from --diff-baseline-log source or last pairwise run",
    )
    args = parser.parse_args()

    if args.diff_baseline_log is not None:
        log_path = Path(args.diff_baseline_log)
        current = record_from_console_log(log_path)
        if args.write_baseline is not None:
            out = save_baseline(current, Path(args.write_baseline))
            print(f"Wrote baseline: {out}")
            return
        baseline = load_baseline()
        print_baseline_diff(baseline, current, baseline_label=str(DEFAULT_BASELINE_PATH))
        return

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

    if args.pairwise or args.pairwise_20:
        pairwise_limit = 20 if args.pairwise_20 else args.pairwise_limit
        console_log = (
            _pairwise_log_path(args.offset, pairwise_limit)
            if args.offset or pairwise_limit != 4
            else _PAIRWISE_CONSOLE_LOG
        )
        with tee_console(console_log):
            result = run_pairwise(
                limit=pairwise_limit,
                offset=args.offset,
                rel_tol=args.rel_tol,
                abs_tol=args.abs_tol,
                use_llm_judge=not args.no_judge_fallback,
                stop_on_quota=True,
            )
            if args.offset:
                print(f"Golden slice: offset={args.offset} limit={pairwise_limit}")
            _print_pairwise_result(
                result,
                console_log=console_log,
                trace_root=_TRACE_ROOT,
            )
            if args.write_baseline is not None:
                record = record_from_pairwise_result(result)
                record["label"] = f"pairwise-{pairwise_limit}"
                record["run"]["use_llm_judge"] = not args.no_judge_fallback
                record["run"]["rel_tol"] = args.rel_tol
                record["run"]["abs_tol"] = args.abs_tol
                out = save_baseline(record, Path(args.write_baseline))
                print(f"\nWrote baseline: {out}")
            elif args.compare_baseline:
                baseline = load_baseline()
                current = record_from_pairwise_result(result)
                print_baseline_diff(baseline, current, baseline_label=str(DEFAULT_BASELINE_PATH))
        return

    rows, summary = run_evaluate(
        args.strategy,
        rel_tol=args.rel_tol,
        abs_tol=args.abs_tol,
        limit=args.limit,
        offset=args.offset,
        use_llm_judge=not args.no_judge_fallback,
    )

    print(f"Strategy: {args.strategy}")
    print(f"Total: {int(summary['total'])}")
    print(f"Exact matches: {int(summary['exact_count'])} ({summary['exact_rate']:.1%})")
    print(f"Tolerance matches: {int(summary['tolerance_count'])} ({summary['tolerance_rate']:.1%})")
    print(f"Judge fallback matches: {int(summary['judge_count'])} ({summary['judge_rate']:.1%})")
    overall = accuracy_ci(
        [
            row.match_type in ("exact", "tolerance")
            or (row.judge_used and row.judge_is_correct)
            for row in rows
        ]
    )
    print(f"Overall matched: {overall.format_rate()} ({overall.method})")

    print("\nSample results:")
    for row in rows[: min(10, len(rows))]:
        print(
            f"- #{row.number:02d} {row.problem_id}: "
            f"pred={row.prediction} expected={row.expected} "
            f"[{row.match_type}, precision={row.precision_score:.4f}]"
        )


if __name__ == "__main__":
    main()
