from .utils.json_parser import clean_llm_json
from .utils.llm import call_llm
import json
from .prompts import ROUTING_PROMPT

async def classify_input(user_input, model_client):
    """
    Acts as the Domain Supervisor using an LLM to classify the query [1, 2].
    """
    # Using LLM-based classification instead of hard-coded keywords [2]
    response = await model_client.generate(
        prompt=f"{ROUTING_PROMPT}\n\nUser Query: {user_input}",
        response_format={"type": "json_object"} # Ensure structured output [3]
    )
    
    data = clean_llm_json(response.text)
    return json.loads(data)

def route_issue(classified_data):
    """
    Dispatches the query to the appropriate specialized persona based on the classification [1].
    """
    # 1. Check Guardrails first [2]
    if not classified_data.get("is_safe", False):
        return "Fallback", "Security guardrail triggered: adversarial input detected."

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
        # 3. Graceful Fallback for out-of-scope or ambiguous questions [1]
        return "Fallback", "The question is ambiguous or out-of-scope. Requesting clarification."