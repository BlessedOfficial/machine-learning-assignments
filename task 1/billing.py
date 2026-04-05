import os
from dotenv import load_dotenv
from openrouter import OpenRouter
import json
import asyncio

from utils import clean_llm_json

load_dotenv()

# Load API key once
api_key = os.getenv("OPENROUTER_API_KEY")
if not api_key:
    raise ValueError("API key not found. Make sure .env has OPENROUTER_API_KEY set.")

# Create client once
client = OpenRouter(api_key=api_key)

BILLING_ISSUE_INSTRUCTION = """You are a helpful assistant for generating solutions to billing customer support ticket issues for unspecified company.

You are provided a JSON object in the triple quotes with the following fields:
Category: The category of the issue (e.g. technical, billing, account)
Product: The product the issue is related to (e.g. "SuperWidget 3000")
Issue Type: The type of issue (e.g. "not turning on", "error message", "slow performance")
Urgency: The urgency of the issue (e.g. "low", "medium", "high")
Description: A detailed description of the customer's issue.
Using the provided information, suggest a solution to the customer's issue.


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

SOLUTION_REVIEWER_INSTRUCTION = """You are a helpful assistant for reviewing solutions to billing customer support ticket issues for unspecified company.

You are provided with 2 JSON objects in the triple quotes. The first JSON object has the original ticket information with the following fields:
Category: The category of the issue (e.g. technical, billing, account)
Product: The product the issue is related to (e.g. "SuperWidget 3000")
Issue Type: The type of issue (e.g. "not turning on", "error message", "slow performance")
Urgency: The urgency of the issue (e.g. "low", "medium", "high")
Description: A detailed description of the customer's issue.
The second JSON object has the suggested solution with the following fields:
Category: The category of the issue (e.g. technical, billing, account)
Product: The product the issue is related to (e.g. "SuperWidget 3000")
Issue Type: The type of issue (e.g. "not turning on", "error message", "slow performance")
Urgency: The urgency of the issue (e.g. "low", "medium", "high")
Description: A detailed description of the customer's issue.
Solution Steps: A list of steps suggested to solve the issue.
Using the provided information, review the suggested solution to client and determine if it is appropriate for the customer's issue. If it is appropriate, return a JSON object with a "approved" field set to true. If it is not appropriate, return a JSON object with a "approved" field set to false and a "feedback" field with suggestions for improving the solution.
"""

MAX_RETRIES = 3  

def safe_parse_json(data):
    """Safely parse JSON whether it's string or dict."""
    try:
        if isinstance(data, str):
            return json.loads(data)
        return data
    except Exception as e:
        print("JSON Parse Error:", e)
        return None


def billing_issue_response(classified_data):
    # Step 1: Generate initial solution
    raw_solution = billing_issue_response_suggested(classified_data)
    cleaned_solution = clean_llm_json(raw_solution)

    solution_data = safe_parse_json(cleaned_solution)

    if not solution_data:
        return {"error": "Failed to generate initial solution"}

    # Step 2: Reflection / review loop
    for attempt in range(MAX_RETRIES):
        print(f"\n--- Iteration {attempt + 1} ---")

        review_raw = check_solution(classified_data, solution_data)
        review_clean = clean_llm_json(review_raw)

        print("Review Raw:", review_raw)
        print("Review Clean:", review_clean)

        review_data = safe_parse_json(review_clean)

        if not review_data:
            print("⚠️ Review parsing failed. Stopping loop.")
            break

        # Normalize approval value (handles True, "true", etc.)
        approved = str(review_data.get("approved")).lower() == "true"

        if approved and attempt >= 1:  # Require at least 2 iterations before approval to ensure reflection
            print("✅ Solution approved")
            return solution_data
        if approved:
            print("⚠️ Solution approved too early (iteration 1). Continuing reflection.")
            continue

        # Improve solution
        feedback = review_data.get("feedback", "No feedback provided")

        improved_prompt = f"""
Improve this solution based on the feedback.

Return ONLY valid JSON.
Add to the JSON object a new field "improvement_notes" with a brief explanation of how you improved the solution based on the feedback.

Original Solution:
{json.dumps(solution_data, indent=2)}

Feedback:
{feedback}
"""

        try:
            improved = client.chat.send(
                model="openrouter/free",
                messages=[{"role": "user", "content": improved_prompt}],
            )

            improved_raw = improved.choices[0].message.content
            improved_clean = clean_llm_json(improved_raw)

            solution_data = safe_parse_json(improved_clean)

            if not solution_data:
                print("⚠️ Improvement parsing failed. Stopping loop.")
                break

        except Exception as e:
            print("❌ LLM call failed:", e)
            break

    # fallback if never approved
    print("⚠️ Returning best available solution (not fully approved)")
    return solution_data


def billing_issue_response_suggested(classified_data):
    prompt = f"{BILLING_ISSUE_INSTRUCTION}\n\"\"\"\n{json.dumps(classified_data)}\n\"\"\""
    result = client.chat.send(
        model="openrouter/free",
        messages=[{"role": "user", "content": prompt}],
    )
    return result.choices[0].message.content


def check_solution(original_ticket, suggested_solution):
    prompt = f"{SOLUTION_REVIEWER_INSTRUCTION}\n\"\"\"\nOriginal Ticket:\n{json.dumps(original_ticket)}\n\nSuggested Solution:\n{json.dumps(suggested_solution)}\n\"\"\""
    result = client.chat.send(
        model="openrouter/free",
        messages=[{"role": "user", "content": prompt}],
    )
    return result.choices[0].message.content