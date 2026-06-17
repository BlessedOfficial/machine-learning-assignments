"""Load golden GSM8K questions and answers from per-problem folders (1–35)."""

from __future__ import annotations

import json
from pathlib import Path

_GOLDEN_ROOT = Path(__file__).resolve().parents[2] / "data" / "golden"


def golden_root() -> Path:
    return _GOLDEN_ROOT


def list_problem_numbers() -> list[int]:
    numbers: list[int] = []
    for path in _GOLDEN_ROOT.iterdir():
        if path.is_dir() and path.name.isdigit():
            numbers.append(int(path.name))
    return sorted(numbers)


def problem_dir(number: int) -> Path:
    return _GOLDEN_ROOT / str(number)


def question_path(number: int) -> Path:
    return problem_dir(number) / "questions" / "question.json"


def answer_path(number: int) -> Path:
    return problem_dir(number) / "answers" / "answer.json"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_question_by_number(number: int) -> dict:
    path = question_path(number)
    if not path.exists():
        raise FileNotFoundError(f"No question file for number {number}: {path}")
    return _load_json(path)


def load_answer_by_number(number: int) -> dict:
    path = answer_path(number)
    if not path.exists():
        raise FileNotFoundError(f"No answer file for number {number}: {path}")
    return _load_json(path)


def _find_number_by_id(problem_id: str) -> int | None:
    for number in list_problem_numbers():
        row = load_question_by_number(number)
        if row.get("id") == problem_id:
            return number
    return None


def load_question_by_id(problem_id: str) -> dict | None:
    number = _find_number_by_id(problem_id)
    return load_question_by_number(number) if number is not None else None


def load_answer_by_id(problem_id: str) -> dict | None:
    number = _find_number_by_id(problem_id)
    return load_answer_by_number(number) if number is not None else None


def load_question(ref: str | int) -> dict | None:
    """Load question by folder number (1–35) or problem id (gsm8k-test-*)."""
    if isinstance(ref, int) or (isinstance(ref, str) and ref.isdigit()):
        number = int(ref)
        if question_path(number).exists():
            return load_question_by_number(number)
        return None
    return load_question_by_id(str(ref))


def load_answer(ref: str | int) -> dict | None:
    """Load answer by folder number (1–35) or problem id (gsm8k-test-*)."""
    if isinstance(ref, int) or (isinstance(ref, str) and ref.isdigit()):
        number = int(ref)
        if answer_path(number).exists():
            return load_answer_by_number(number)
        return None
    return load_answer_by_id(str(ref))


def load_all_questions() -> list[dict]:
    return [load_question_by_number(n) for n in list_problem_numbers()]


def load_all_answers() -> list[dict]:
    return [load_answer_by_number(n) for n in list_problem_numbers()]


def load_problem_pair(number: int) -> tuple[dict, dict]:
    return load_question_by_number(number), load_answer_by_number(number)
