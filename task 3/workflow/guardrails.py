from workflow.incident_log import log_guardrail_incident
from workflow.prompts import OUT_OF_SCOPE_REPLY

_META_PHRASES = (
    "outside the scope",
    "outside ai.inc",
    "only support ai.inc",
    "only answer questions",
    "only discuss",
    "i am restricted",
    "i'm restricted",
    "my instructions",
    "system prompt",
    "multi-agent",
    "guardrail",
    "cannot discuss",
    "not allowed to",
    "knowledge base to answer",
    "as an ai language model",
    "as a language model",
)


def apply_response_guardrail(text: str, *, source_input: str = "") -> str:
    if not text:
        log_guardrail_incident(
            rule_triggered="response_empty",
            raw_input=source_input,
            decision="block",
            stage="output",
        )
        return OUT_OF_SCOPE_REPLY

    lower = text.lower()
    if any(phrase in lower for phrase in _META_PHRASES):
        log_guardrail_incident(
            rule_triggered="response_meta_leak",
            raw_input=source_input or text[:500],
            decision="block",
            stage="output",
            detail="model disclosed restrictions or internal instructions",
        )
        return OUT_OF_SCOPE_REPLY

    return text
