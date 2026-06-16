import os
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(_ROOT / ".env")

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
SOLVER_MODEL = os.getenv("SOLVER_MODEL", "openrouter/free")
JUDGE_MODEL = os.getenv(
    "JUDGE_MODEL", "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free"
)
CODE_EXEC_TIMEOUT = float(os.getenv("CODE_EXEC_TIMEOUT", "5.0"))
LLM_REQUEST_TIMEOUT_SEC = float(os.getenv("LLM_REQUEST_TIMEOUT_SEC", "90"))
LLM_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "8"))
LLM_RETRY_BASE_SEC = float(os.getenv("LLM_RETRY_BASE_SEC", "3"))
