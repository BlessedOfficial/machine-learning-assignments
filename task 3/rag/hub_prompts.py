import json
import warnings
from pathlib import Path

from langchain_core._api import LangChainBetaWarning
from langchain_core._api.deprecation import LangChainPendingDeprecationWarning
from langchain_core.load import dumps, load
from langchain_core.prompts import ChatPromptTemplate
from langsmith import Client

PROMPT_HUB_ID = "wfh/proposal-indexing"
PROMPT_CACHE_PATH = (
    Path(__file__).resolve().parent.parent / "data" / "prompts" / "proposal-indexing.json"
)


def _load_cached_prompt() -> ChatPromptTemplate:
    data = json.loads(PROMPT_CACHE_PATH.read_text(encoding="utf-8"))
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=LangChainBetaWarning)
        warnings.filterwarnings("ignore", category=LangChainPendingDeprecationWarning)
        prompt = load(data, allowed_objects="core")
    if not isinstance(prompt, ChatPromptTemplate):
        raise TypeError(f"Expected ChatPromptTemplate, got {type(prompt)}")
    return prompt


def get_proposal_indexing_prompt() -> ChatPromptTemplate:
    if PROMPT_CACHE_PATH.exists():
        return _load_cached_prompt()
    prompt = Client().pull_prompt(
        PROMPT_HUB_ID,
        dangerously_pull_public_prompt=True,
    )
    PROMPT_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    PROMPT_CACHE_PATH.write_text(dumps(prompt), encoding="utf-8")
    return prompt
