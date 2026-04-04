from technical import tech_issue_response

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

#Prompts

CLEAN_INSTRUCTION = """
You are a helpful assistant for cleaning and normalizing customer support tickets.
Clean and normalize the text in the triple quotes and return 
clean standardized text without any explanation. 
Fix all typos and grammatical errors. Expand all contractions and abbreviations.
Return JSON object in the following format:
{
    "cleaned_text": "cleaned and normalized text"
}
"""
GENERATE_SENTIMENT_INSTRUCTION = """
You are a helpful assistant for analyzing customer support tickets.
Information in the triple quotes is cleaned customer support ticket given in JSON format with a "cleaned_text" field.
Analyze the sentiment of the customer's message and determine if it is positive, negative, or neutral.
Return the sentiment in a JSON object.

Return a JSON object in the following format:
{
    "sentiment": "positive" | "negative" | "neutral"
}
"""

EXTRACT_KEYWORDS_INSTRUCTION = """
You are a helpful assistant for extracting keywords from customer support tickets.
Information in the triple quotes is cleaned customer support ticket given in JSON format with a "cleaned_text" field.
Extract the most important keywords from the customer's message that are relevant to understanding their issue.
Return the keywords in a JSON object.

Return a JSON object in the following format:
{
    "keywords": ["keyword 1", "keyword 2", "keyword 3"]
}
"""

CLASSIFY_INSTRUCTION = """
You are a helpful assistant for classifying customer support tickets.
You are provided 2 JSON objects in the triple quotes. The first JSON object has a "cleaned_text" field with the cleaned customer support ticket.
The second JSON object has a "sentiment" field and a "keywords" field with the sentiment and keywords extracted from the ticket.


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

#Functions

def clean_user_input(user_input):
    prompt = f"{CLEAN_INSTRUCTION}\n\"\"\"\n{user_input}\n\"\"\""
    result = client.chat.send(
        model="openrouter/free",
        messages=[{"role": "user", "content": prompt}],
    )
    return result.choices[0].message.content

async def generate_sentiment(user_input):
    prompt = f"{GENERATE_SENTIMENT_INSTRUCTION}\n\"\"\"\n{user_input}\n\"\"\""
    
    result = await asyncio.to_thread(
        client.chat.send,
        model="openrouter/free",
        messages=[{"role": "user", "content": prompt}],
    )

    return result.choices[0].message.content


async def extract_keywords(user_input):
    prompt = f"{EXTRACT_KEYWORDS_INSTRUCTION}\n\"\"\"\n{user_input}\n\"\"\""
    
    result = await asyncio.to_thread(
        client.chat.send,
        model="openrouter/free",
        messages=[{"role": "user", "content": prompt}],
    )

    return result.choices[0].message.content

async def generate_sentiment_and_keywords(cleaned_input):
    
    

    sentiment_result, keywords_result = await asyncio.gather(
        generate_sentiment(cleaned_input),
        extract_keywords(cleaned_input)
    )
  
    sentiment_clean = clean_llm_json(sentiment_result)
    keywords_clean = clean_llm_json(keywords_result)

    sentiment_data = json.loads(sentiment_clean)
    keywords_data = json.loads(keywords_clean)
  
    combined_result = {
        "sentiment": sentiment_data["sentiment"],
        "keywords": keywords_data["keywords"]
    }

    return combined_result





def classify_input(cleaned_input, sentiments_and_keywords):
    prompt = f"{CLASSIFY_INSTRUCTION}\n\"\"\"\n{cleaned_input} + {json.dumps(sentiments_and_keywords)}\n\"\"\""
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

#Each function on seperate page to implement Reflection
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

