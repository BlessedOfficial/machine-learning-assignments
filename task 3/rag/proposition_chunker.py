import json
import re

from langchain_openai import ChatOpenAI

from config import CHUNKING_MODEL, OPENROUTER_API_KEY, OPENROUTER_BASE_URL
from rag.hub_prompts import get_proposal_indexing_prompt
from rag.schemas import PropositionList
from utils.json_parser import parse_llm_response
from utils.openrouter_retry import invoke_with_retry

_proposition_chain = None


def _get_llm() -> ChatOpenAI:
    if not OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY is required for LLM chunking.")
    return ChatOpenAI(
        model=CHUNKING_MODEL,
        api_key=OPENROUTER_API_KEY,
        base_url=OPENROUTER_BASE_URL,
        temperature=0,
        max_retries=2,
        timeout=120,
    )


def get_proposition_chain():
    global _proposition_chain
    if _proposition_chain is None:
        prompt = get_proposal_indexing_prompt()
        llm = _get_llm()
        try:
            structured_llm = llm.with_structured_output(PropositionList)
            _proposition_chain = prompt | structured_llm
        except Exception:
            _proposition_chain = prompt | llm
    return _proposition_chain


def _parse_propositions_from_text(content: str) -> list[str]:
    parsed = parse_llm_response(content)
    if isinstance(parsed, dict) and "sentences" in parsed:
        return [s.strip() for s in parsed["sentences"] if s and s.strip()]
    if isinstance(parsed, list):
        return [str(s).strip() for s in parsed if str(s).strip()]

    match = re.search(r"\[.*\]", content, re.DOTALL)
    if match:
        try:
            items = json.loads(match.group())
            if isinstance(items, list):
                return [str(s).strip() for s in items if str(s).strip()]
        except json.JSONDecodeError:
            pass

    return [line.strip() for line in content.splitlines() if line.strip()]


def extract_propositions(paragraph: str) -> list[str]:
    chain = get_proposition_chain()
    result = invoke_with_retry(
        chain, {"input": paragraph}, label="Proposition extraction"
    )

    if isinstance(result, PropositionList):
        sentences = result.sentences or []
        return [s.strip() for s in sentences if s and s.strip()]
    if hasattr(result, "sentences"):
        sentences = result.sentences or []
        return [s.strip() for s in sentences if s and s.strip()]

    content = result.content if hasattr(result, "content") else str(result)
    propositions = _parse_propositions_from_text(content)
    return propositions if propositions else [paragraph.strip()]
