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


def record_to_problem(record: dict) -> Problem:
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

    problems: list[Problem] = []
    for idx in chosen:
        row = ds[idx]
        record = _row_to_record(row, split=split, index=idx)
        problems.append(record_to_problem(record))
    return problems


def export_golden_jsonl(
    path: Path,
    *,
    n: int = 35,
    seed: int = 42,
    split: str = GSM8K_TEST_SPLIT,
    config: str = GSM8K_CONFIG,
) -> list[dict]:
    ds = load_gsm8k_split(split=split, config=config)
    indices = list(range(len(ds)))
    rng = random.Random(seed)
    rng.shuffle(indices)
    chosen = sorted(indices[:n])

    records = [
        _row_to_record(ds[idx], split=split, index=idx) for idx in chosen
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return records


def load_golden_problems(path: Path) -> list[Problem]:
    problems: list[Problem] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            problems.append(record_to_problem(json.loads(line)))
    return problems
