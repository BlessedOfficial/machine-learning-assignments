import json
from pathlib import Path

from strategies.base import Problem

GSM8K_TEST_SPLIT = "test"


def parse_gsm8k_answer(raw: str) -> str:
    """Extract final numeric answer after #### in GSM8K solution text."""
    if "####" in raw:
        return raw.split("####")[-1].strip()
    return raw.strip()


def record_to_question(record: dict) -> Problem:
    """Problem for strategy inference — no answers in metadata."""
    return Problem(
        id=record["id"],
        question=record["question"],
        metadata={
            "source_index": record.get("source_index"),
            "split": record.get("split", GSM8K_TEST_SPLIT),
        },
    )


def _read_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def load_golden_questions(path: Path) -> list[Problem]:
    return [record_to_question(row) for row in _read_jsonl(path)]


def load_golden_answers(path: Path) -> dict[str, dict]:
    """Map problem id -> {ground_truth, full_solution}. For eval / ranking only."""
    return {row["id"]: row for row in _read_jsonl(path)}


def align_questions_and_answers(
    questions: list[Problem],
    answers: dict[str, dict],
) -> list[tuple[Problem, dict]]:
    """Pair each question with its label; raises if ids mismatch."""
    pairs: list[tuple[Problem, dict]] = []
    for q in questions:
        if q.id not in answers:
            raise KeyError(f"Missing answer for question id: {q.id}")
        pairs.append((q, answers[q.id]))
    return pairs
