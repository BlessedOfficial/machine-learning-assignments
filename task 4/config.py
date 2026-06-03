import os
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parent
_ENV_PATH = _ROOT / ".env"
load_dotenv(_ENV_PATH)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
SOLVER_MODEL = os.getenv("SOLVER_MODEL", "openrouter/free")
JUDGE_MODEL = os.getenv(
    "JUDGE_MODEL", "meta-llama/llama-3.2-3b-instruct:free"
)

# Paths
TRACE_LOG_DIR = Path(os.getenv("TRACE_LOG_DIR", _ROOT / "data" / "logs" / "traces"))
BASELINE_PATH = Path(os.getenv("BASELINE_PATH", _ROOT / "data" / "baseline.json"))
CODE_EXEC_TIMEOUT = float(os.getenv("CODE_EXEC_TIMEOUT", "5.0"))

GOLDEN_QUESTIONS_PATH = Path(
    os.getenv(
        "GOLDEN_QUESTIONS_PATH",
        _ROOT / "data" / "golden" / "gsm8k_test_35_questions.jsonl",
    )
)
GOLDEN_ANSWERS_PATH = Path(
    os.getenv(
        "GOLDEN_ANSWERS_PATH",
        _ROOT / "data" / "golden" / "gsm8k_test_35_answers.jsonl",
    )
)
