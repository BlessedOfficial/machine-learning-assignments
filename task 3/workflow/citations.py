import re

from workflow.incident_log import log_guardrail_incident
from workflow.prompts import OUT_OF_SCOPE_REPLY

_CHUNK_ID_PATTERN = re.compile(
    r"[a-z0-9][a-z0-9-]*#(?:loc|prop|ag|para)-\d+",
    re.IGNORECASE,
)

_UNCERTAINTY_PHRASES = (
    "don't have enough information",
    "do not have enough information",
    "don't have sufficient information",
    "do not have sufficient information",
    "not enough information",
    "insufficient information",
    "cannot find information",
    "can't find information",
    "no information in the retrieved",
    "not covered in the retrieved",
)


def extract_chunk_ids_from_answer(text: str) -> set[str]:
    return set(_CHUNK_ID_PATTERN.findall(text))


def has_explicit_uncertainty(text: str) -> bool:
    lower = text.lower()
    return any(phrase in lower for phrase in _UNCERTAINTY_PHRASES)


def is_out_of_scope_reply(text: str) -> bool:
    return OUT_OF_SCOPE_REPLY[:50].lower() in text.lower()


def _reject_citation(
    answer: str,
    *,
    source_input: str,
    detail: str,
) -> str:
    replacement = (
        "I don't have enough information in the retrieved excerpts to answer "
        "that question. Please contact the appropriate AI.Inc support channel "
        "for further assistance."
    )
    log_guardrail_incident(
        rule_triggered="citation_discipline",
        raw_input=source_input or answer[:500],
        decision="block",
        stage="output",
        detail=detail,
    )
    return replacement


def enforce_citation_discipline(
    answer: str,
    hits: list[dict],
    *,
    source_input: str = "",
) -> str:
    """
    Require chunk ID citations when excerpts were retrieved.
    Reject answers that state facts without citing a retrieved chunk ID
    or explicitly acknowledging missing information.
    """
    answer = (answer or "").strip()
    if not answer:
        log_guardrail_incident(
            rule_triggered="citation_discipline",
            raw_input=source_input,
            decision="block",
            stage="output",
            detail="empty answer after synthesis",
        )
        return OUT_OF_SCOPE_REPLY

    if not hits:
        if has_explicit_uncertainty(answer) or is_out_of_scope_reply(answer):
            return answer
        if extract_chunk_ids_from_answer(answer):
            log_guardrail_incident(
                rule_triggered="citation_discipline",
                raw_input=source_input or answer[:500],
                decision="block",
                stage="output",
                detail="cited chunks without retrieval hits",
            )
            return (
                "I don't have enough information in the retrieved excerpts to "
                "support that answer."
            )
        return answer

    allowed_ids = {hit["chunk_id"] for hit in hits}
    cited_ids = extract_chunk_ids_from_answer(answer)
    valid_citations = cited_ids & allowed_ids

    if has_explicit_uncertainty(answer):
        return answer

    if is_out_of_scope_reply(answer):
        return answer

    if valid_citations:
        invalid = cited_ids - allowed_ids
        if invalid:
            return _reject_citation(
                answer,
                source_input=source_input,
                detail=f"invalid chunk ids: {sorted(invalid)}",
            )
        return answer

    return _reject_citation(
        answer,
        source_input=source_input,
        detail="factual answer without valid chunk citations",
    )


def format_allowed_citation_ids(hits: list[dict]) -> str:
    if not hits:
        return ""
    return ", ".join(f"`{hit['chunk_id']}`" for hit in hits)
