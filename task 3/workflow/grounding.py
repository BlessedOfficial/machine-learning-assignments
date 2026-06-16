"""Verify factual claims in answers are supported by cited chunks."""

import re

from config import GROUNDING_MODE
from workflow.citations import (
    extract_chunk_ids_from_answer,
    has_explicit_uncertainty,
    is_out_of_scope_reply,
)
from workflow.incident_log import log_guardrail_incident

_CHUNK_ID_INLINE = re.compile(
    r"[`\[]?([a-z0-9][a-z0-9-]*#(?:loc|prop|ag|para)-\d+)[`\]]?",
    re.IGNORECASE,
)
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
_STOPWORDS = frozenset(
    "a an the is are was were be been being have has had do does did "
    "will would could should may might must shall can to of in for on "
    "at by with from as and or but not no it its this that these those "
    "you your we our they their i me my".split()
)
_BOILERPLATE_PREFIXES = (
    "sources:",
    "**sources:**",
    "i don't have enough information",
    "i do not have enough information",
    "unfortunately, i do not have access",
)


def _content_tokens(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return {w for w in words if len(w) > 2 and w not in _STOPWORDS}


def _strip_citations(text: str) -> str:
    cleaned = _CHUNK_ID_INLINE.sub("", text)
    return re.sub(r"\s+", " ", cleaned).strip(" .,")


def _grounding_overlap(claim: str, chunk_texts: list[str]) -> float:
    claim_tokens = _content_tokens(claim)
    if not claim_tokens:
        return 1.0

    corpus_tokens: set[str] = set()
    for chunk in chunk_texts:
        corpus_tokens |= _content_tokens(chunk)

    if not corpus_tokens:
        return 0.0

    matched = claim_tokens & corpus_tokens
    return len(matched) / len(claim_tokens)


def _citations_in_sentence(sentence: str) -> set[str]:
    return set(_CHUNK_ID_INLINE.findall(sentence))


def _is_boilerplate(sentence: str) -> bool:
    lower = sentence.lower().strip()
    return any(lower.startswith(prefix) for prefix in _BOILERPLATE_PREFIXES)


def _looks_factual(sentence: str) -> bool:
    if _is_boilerplate(sentence):
        return False
    claim = _strip_citations(sentence)
    if len(claim) < 20:
        return False
    if re.search(r"\d", claim):
        return True
    return len(_content_tokens(claim)) >= 4


def apply_grounding_check(
    answer: str,
    hits: list[dict],
    *,
    source_input: str = "",
) -> str:
    """
    Verify cited claims overlap retrieved chunk text.
    Unsupported factual sentences are stripped (default) or flagged.
    """
    answer = (answer or "").strip()
    if not answer or not hits:
        return answer

    if has_explicit_uncertainty(answer) or is_out_of_scope_reply(answer):
        return answer

    chunk_text = {hit["chunk_id"]: hit["text"] for hit in hits}
    min_overlap = 0.25

    kept: list[str] = []
    stripped = 0

    for sentence in _SENTENCE_SPLIT.split(answer):
        sentence = sentence.strip()
        if not sentence:
            continue

        sent_citations = _citations_in_sentence(sentence)
        claim = _strip_citations(sentence)

        if not sent_citations:
            if _is_boilerplate(sentence) or not _looks_factual(sentence):
                kept.append(sentence)
            else:
                stripped += 1
            continue

        valid_ids = [cid for cid in sent_citations if cid in chunk_text]
        if not valid_ids:
            stripped += 1
            continue

        overlap = _grounding_overlap(
            claim, [chunk_text[cid] for cid in valid_ids]
        )
        if overlap >= min_overlap:
            kept.append(sentence)
        else:
            stripped += 1

    reject_message = (
        "I don't have enough information in the retrieved excerpts to "
        "support a fully verified answer. Please contact the appropriate "
        "AI.Inc support channel for further assistance."
    )

    if GROUNDING_MODE == "reject" and stripped > 0:
        log_guardrail_incident(
            rule_triggered="grounding_reject",
            raw_input=source_input or answer[:500],
            decision="block",
            stage="output",
            detail=f"{stripped} unsupported sentence(s)",
        )
        return reject_message

    if not kept:
        cited = extract_chunk_ids_from_answer(answer)
        if cited:
            log_guardrail_incident(
                rule_triggered="grounding_reject",
                raw_input=source_input or answer[:500],
                decision="block",
                stage="output",
                detail="no verifiable sentences remained after grounding",
            )
            return reject_message
        return answer

    result = " ".join(kept)
    if stripped > 0 and GROUNDING_MODE == "flag":
        result += (
            "\n\n(Note: Some statements were omitted because they could not be "
            "verified against the cited retrieved excerpts.)"
        )
    return result
