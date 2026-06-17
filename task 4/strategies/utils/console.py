"""Structured console output for strategy runs."""

from strategies.utils.answer import normalize_numeric_answer

_WIDTH = 60


def _safe_console_text(text: str) -> str:
    # Keep console logging robust on cp1252 terminals.
    return text.encode("ascii", errors="replace").decode("ascii")


def log_run_header(*, strategy: str, problem_id: str, question: str) -> None:
    print(f"\n{'=' * _WIDTH}", flush=True)
    print(f"Strategy: {strategy}", flush=True)
    if problem_id:
        print(f"Problem ID: {problem_id}", flush=True)
    print(f"Question: {_safe_console_text(question)}", flush=True)
    print("=" * _WIDTH, flush=True)


def log_phase(title: str) -> None:
    print(f"\n--- {title} ---", flush=True)


def log_plan(steps: list[str]) -> None:
    print("Plan:", flush=True)
    for index, step in enumerate(steps, start=1):
        print(f"  {index}. {_safe_console_text(step)}", flush=True)


def log_step(step_num: int, label: str, content: str) -> None:
    line = content.strip().replace("\n", " ")
    if len(line) > 240:
        line = line[:240] + "..."
    print(f"Step {step_num} ({label}): {_safe_console_text(line)}", flush=True)


def log_final_answer(raw_answer: str) -> str:
    normalized = normalize_numeric_answer(raw_answer)
    print(f"\nFinal Answer: {normalized}", flush=True)
    print("=" * _WIDTH + "\n", flush=True)
    return normalized
