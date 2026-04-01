import os
from dotenv import load_dotenv
from openrouter import OpenRouter
import json

from chaining import clean_user_input

load_dotenv()

# Load API key once
api_key = os.getenv("OPENROUTER_API_KEY")

if not api_key:
    raise ValueError("API key not found. Make sure .env has OPENROUTER_API_KEY set.")

# Create client once
client = OpenRouter(api_key=api_key)

# =========================
# 1. CLASSIFICATION
# =========================

CLASSIFY_INSTRUCTION = """Information in the triple quotes is a support ticket.

Determine the ticket category and extract key entities.

Categories must be one of:
- technical
- billing
- general
- escalation
- unsure

Return the information in a JSON object with the following format:
{
    "category": "technical | billing | general | escalation | unsure",
    "product": "product name",
    "issue_type": "issue type",
    "urgency": "low | medium | high",
    "description": "cleaned and concise description"
}
"""


# =========================
# 2. ROUTING BRANCHES
# =========================

TECHNICAL_ISSUE_INSTRUCTION = """Information in the triple quotes is a support ticket related to a technical issue.

Using the provided information, suggest a solution.

Return a JSON object in the following format:
{
    "category": "technical",
    "product": "...",
    "issue_type": "...",
    "urgency": "...",
    "description": "...",
    "solution_steps": [
        "step 1",
        "step 2",
        "step 3"
    ]
}
"""


BILLING_ISSUE_INSTRUCTION = """Information in the triple quotes is a support ticket related to a billing issue.

Using the provided information, determine if the user is eligible for a refund or billing correction and suggest next steps.

Return a JSON object in the following format:
{
    "category": "billing",
    "product": "...",
    "issue_type": "...",
    "urgency": "...",
    "description": "...",
    "solution_steps": [
        "step 1",
        "step 2",
        "step 3"
    ]
}
"""


GENERAL_ISSUE_INSTRUCTION = """Information in the triple quotes is a support ticket related to a general inquiry.

Provide a helpful and informative response.

Return a JSON object in the following format:
{
    "category": "general",
    "product": "...",
    "issue_type": "...",
    "urgency": "...",
    "description": "...",
    "solution_steps": [
        "step 1",
        "step 2",
        "step 3"
    ]
}
"""


ESCALATION_INSTRUCTION = """Information in the triple quotes is a support ticket that requires escalation.

Provide an empathetic response and include clear escalation steps.

Return a JSON object in the following format:
{
    "category": "escalation",
    "product": "...",
    "issue_type": "...",
    "urgency": "...",
    "description": "...",
    "solution_steps": [
        "acknowledge the issue empathetically",
        "explain escalation process",
        "list required details for escalation",
        "provide expected response time"
    ]
}
"""


UNSURE_ISSUE_INSTRUCTION = """Information in the triple quotes is a support ticket that is unclear.

Ask the user for clarification.

Return a JSON object in the following format:
{
    "category": "unsure",
    "message": "Politely ask the user to clarify their issue",
    "clarification_questions": [
        "question 1",
        "question 2"
    ]
}
"""


def classify_input(cleaned_input):
    prompt = f"{CLASSIFY_INSTRUCTION}\n\"\"\"\n{cleaned_input}\n\"\"\""
    result = client.chat.send(
        model="openrouter/free",
        messages=[{"role": "user", "content": prompt}],
    )
    content = result.choices[0].message.content
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        print("⚠️ Failed to parse JSON, returning 'unsure'")
        print("Raw output:", content)
        return {"category": "unsure"}


def tech_issue_response(classified_data):
    prompt = f"{TECHNICAL_ISSUE_INSTRUCTION}\n\"\"\"\n{json.dumps(classified_data)}\n\"\"\""
    result = client.chat.send(
        model="openrouter/free",
        messages=[{"role": "user", "content": prompt}],
    )
    return result.choices[0].message.content

def billing_issue_response(classified_data):
    prompt = f"{BILLING_ISSUE_INSTRUCTION}\n\"\"\"\n{json.dumps(classified_data)}\n\"\"\""
    result = client.chat.send(
        model="openrouter/free",
        messages=[{"role": "user", "content": prompt}],
    )
    return result.choices[0].message.content

def general_issue_response(classified_data):
    prompt = f"{GENERAL_ISSUE_INSTRUCTION}\n\"\"\"\n{json.dumps(classified_data)}\n\"\"\""
    result = client.chat.send(
        model="openrouter/free",
        messages=[{"role": "user", "content": prompt}],
    )
    return result.choices[0].message.content

def escalation_response(classified_data):
    prompt = f"{ESCALATION_INSTRUCTION}\n\"\"\"\n{json.dumps(classified_data)}\n\"\"\""
    result = client.chat.send(
        model="openrouter/free",
        messages=[{"role": "user", "content": prompt}],
    )
    return result.choices[0].message.content

def unsure_response(classified_data):
    prompt = f"{UNSURE_ISSUE_INSTRUCTION}\n\"\"\"\n{json.dumps(classified_data)}\n\"\"\""
    result = client.chat.send(
        model="openrouter/free",
        messages=[{"role": "user", "content": prompt}],
    )
    return result.choices[0].message.content

# =========================
# 2. ROUTING LOGIC
# =========================

def route_issue(classified_data):
    category = classified_data.get("category", "unsure")  # safer access
    if category == "technical":
        return tech_issue_response(classified_data)
    elif category == "billing":
        return billing_issue_response(classified_data)
    elif category == "general":
        return general_issue_response(classified_data)
    elif category == "escalation":
        return escalation_response(classified_data)
    else:
        return unsure_response(classified_data)


def generate_response(user_input):
    cleaned = clean_user_input(user_input)
    classified_data = classify_input(cleaned)
    response_text = route_issue(classified_data)
    return response_text