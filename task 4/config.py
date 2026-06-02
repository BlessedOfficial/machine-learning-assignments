import os
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parent
_ENV_PATH = _ROOT / ".env"
load_dotenv(_ENV_PATH)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
SOLVER_MODEL = os.getenv("SOLVER_MODEL", "openrouter/free")
JUDGE_MODEL = os.getenv("JUDGE_MODEL", "meta-llama/llama-3.2-3b-instruct:free")

GOLDEN_SET_PATH = Path(
    os.getenv("GOLDEN_SET_PATH", _ROOT / "data" / "golden" / "gsm8k_test_35.jsonl")
)
GSM8K_SUBSET_SIZE = int(os.getenv("GSM8K_SUBSET_SIZE", "35"))
GSM8K_SUBSET_SEED = int(os.getenv("GSM8K_SUBSET_SEED", "42"))
