import json
import random
from pathlib import Path

from datasets import load_dataset

from strategies.base import Problem

GSM8K_DATASET = "openai/gsm8k"
GSM8K_CONFIG = "main"
GSM8K_TEST_SPLIT = "test"


def parse_gsm8k_answer(raw: str) -> str:
    """Extract final numeric answer after #### in GSM8K solution text."""
    if "####" in raw:
        return raw.split("####")[-1].strip()
    return raw.strip()


def _row_to_record(row: dict, *, split: str, index: int) -> dict:
    return {
        "id": f"gsm8k-{split}-{index}",
        "question": row["question"].strip(),
        "ground_truth": parse_gsm8k_answer(row["answer"]),
        "full_solution": row["answer"].strip(),
        "source_index": index,
        "split": split,
    }


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


def record_to_problem(record: dict) -> Problem:
    """Problem with labels attached (legacy / combined file)."""
    return Problem(
        id=record["id"],
        question=record["question"],
        metadata={
            "ground_truth": record["ground_truth"],
            "full_solution": record.get("full_solution", ""),
            "source_index": record.get("source_index"),
            "split": record.get("split", GSM8K_TEST_SPLIT),
        },
    )


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def split_record(record: dict) -> tuple[dict, dict]:
    question_row = {
        "id": record["id"],
        "question": record["question"],
        "source_index": record.get("source_index"),
        "split": record.get("split", GSM8K_TEST_SPLIT),
    }
    answer_row = {
        "id": record["id"],
        "ground_truth": record["ground_truth"],
        "full_solution": record.get("full_solution", ""),
    }
    return question_row, answer_row


def load_gsm8k_split(split: str = GSM8K_TEST_SPLIT, config: str = GSM8K_CONFIG):
    return load_dataset(GSM8K_DATASET, config, split=split)


def load_gsm8k_subset(
    *,
    n: int = 35,
    seed: int = 42,
    split: str = GSM8K_TEST_SPLIT,
    config: str = GSM8K_CONFIG,
) -> list[Problem]:
    ds = load_gsm8k_split(split=split, config=config)
    indices = list(range(len(ds)))
    rng = random.Random(seed)
    rng.shuffle(indices)
    chosen = sorted(indices[:n])

    return [
        record_to_question(_row_to_record(ds[idx], split=split, index=idx))
        for idx in chosen
    ]


def export_golden_jsonl(
    path: Path,
    *,
    n: int = 35,
    seed: int = 42,
    split: str = GSM8K_TEST_SPLIT,
    config: str = GSM8K_CONFIG,
) -> list[dict]:
    """Write combined golden file (legacy). Prefer export_golden_split."""
    ds = load_gsm8k_split(split=split, config=config)
    indices = list(range(len(ds)))
    rng = random.Random(seed)
    rng.shuffle(indices)
    chosen = sorted(indices[:n])

    records = [_row_to_record(ds[idx], split=split, index=idx) for idx in chosen]
    _write_jsonl(path, records)
    return records


def export_golden_split(
    questions_path: Path,
    answers_path: Path,
    *,
    n: int = 35,
    seed: int = 42,
    split: str = GSM8K_TEST_SPLIT,
    config: str = GSM8K_CONFIG,
) -> tuple[list[dict], list[dict]]:
    """Export questions and answers as separate JSONL files for held-out eval."""
    records = export_golden_jsonl(
        questions_path.with_suffix(".combined.tmp.jsonl"),
        n=n,
        seed=seed,
        split=split,
        config=config,
    )
    questions: list[dict] = []
    answers: list[dict] = []
    for record in records:
        q, a = split_record(record)
        questions.append(q)
        answers.append(a)
    _write_jsonl(questions_path, questions)
    _write_jsonl(answers_path, answers)
    tmp = questions_path.with_suffix(".combined.tmp.jsonl")
    tmp.unlink(missing_ok=True)
    return questions, answers


def export_golden_split_from_combined(
    combined_path: Path,
    questions_path: Path,
    answers_path: Path,
) -> tuple[list[dict], list[dict]]:
    """Split an existing combined golden JSONL into questions + answers."""
    records = _read_jsonl(combined_path)
    questions: list[dict] = []
    answers: list[dict] = []
    for record in records:
        q, a = split_record(record)
        questions.append(q)
        answers.append(a)
    _write_jsonl(questions_path, questions)
    _write_jsonl(answers_path, answers)
    return questions, answers


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


def load_golden_problems(path: Path) -> list[Problem]:
    """Load combined golden file (legacy)."""
    return [record_to_problem(row) for row in _read_jsonl(path)]


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
