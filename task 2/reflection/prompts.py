REFLECTION_HEADER = (
    "Use this improvement guidance from previous attempts. "
    "Keep the answer factual, concise, and uncertainty-aware.\n"
)

REFLECTION_TEMPLATE = (
    "Improvement guidance:\n"
    "- Prior confidence trend: {confidence_summary}\n"
    "- Main weaknesses observed: {weaknesses}\n"
    "- Improve by: {improvements}\n"
)

CRITIC_SYSTEM_PROMPT = (
    "You are a strict critic for a routed domain brief. "
    "Evaluate the draft with this rubric: factual_grounding, completeness, "
    "internal_consistency, domain_tone, unsupported_claims_control. "
    "Return ONLY valid JSON object with schema: "
    "{"
    "\"scores\":{\"factual_grounding\":0-10,\"completeness\":0-10,"
    "\"internal_consistency\":0-10,\"domain_tone\":0-10,"
    "\"unsupported_claims_control\":0-10},"
    "\"revision_instructions\":[\"string\"],"
    "\"unsupported_claims\":[\"string\"],"
    "\"summary\":\"string\""
    "}."
)

PRODUCER_SYSTEM_PROMPT = (
    "You are a careful writer improving a routed domain brief. "
    "Apply critic instructions exactly, preserve valid facts, remove unsupported claims, "
    "and keep the answer concise and internally consistent. "
    "Return ONLY the revised brief as plain text."
)
