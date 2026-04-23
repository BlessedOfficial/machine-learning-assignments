import re
import json
from utils.llm import call_llm
from utils.json_parser import clean_llm_json
from prompts.prompts import ROUTING_PROMPT


import re

def guardrail_check(user_input: str) -> dict:
    text = user_input.lower()

    # 1. Prompt injection patterns
    injection_patterns = [
        "ignore previous instructions",
        "disregard previous instructions",
        "system prompt",
        "you are now",
        "act as",
        "jailbreak",
        "override instructions"
    ]

    if any(p in text for p in injection_patterns):
        return {
            "allowed": False,
            "reason": "Prompt injection attempt detected"
        }

    # 2. PII detection (basic but effective starter)
    email_pattern = r"\b[\w\.-]+@[\w\.-]+\.\w+\b"
    phone_pattern = r"\b\d{10,15}\b"
    api_key_pattern = r"sk-[a-zA-Z0-9]{10,}"

    if re.search(email_pattern, user_input) or re.search(phone_pattern, user_input):
        return {
            "allowed": False,
            "reason": "PII detected in input"
        }

    if re.search(api_key_pattern, user_input):
        return {
            "allowed": False,
            "reason": "Sensitive credential detected"
        }

    return {
        "allowed": True,
        "reason": "Input safe"
    }


async def classify_input(user_input):
    """
    Acts as the Domain Supervisor using an LLM to classify the query
    """

    # 1. Check Guardrails first 
    guardrail_result = guardrail_check(user_input)
    if not guardrail_result["allowed"]:
        return {
            "domain": "Fallback",
            "is_safe": False,
            "reasoning": guardrail_result["reason"],
            "confidence": 0.0
        }

    # 2. Logic to select the research framework based on domain 
    messages = [
        {"role": "system", "content": ROUTING_PROMPT},
        {"role": "user", "content": f"User Query: {user_input}"}
    ]

    response = await call_llm(
        messages=messages,
        model="openrouter/free",
        temperature=0
    )

    return response

def route_issue(classified_data):
    """
    Dispatches the query to the appropriate specialized persona based on the classification
    """

    # 1. Check Guardrails first - if the classification itself is flagged as unsafe, route to fallback
    if not classified_data.get("is_safe", True):
        return "Fallback", "Classification flagged as unsafe. Routing to fallback."

    domain = classified_data.get("domain")
    
    # 2. Logic to select the research framework based on domain [1]
    if domain == "Scientific / Technical":
        return "Scientific", "Using peer-reviewed framing and numerical analysis."
    elif domain == "Historical / Cultural":
        return "Historical", "Focusing on timelines and source verification."
    elif domain == "Financial / Business":
        return "Financial", "Prioritizing market data and risk disclaimers."
    elif domain == "General / Everyday":
        return "General", "Applying a balanced and accessible tone."
    elif "domain" not in classified_data:
        return "Fallback", "Missing domain classification"
    else:
        return "Fallback", "The question is ambiguous or out-of-scope. Requesting clarification."