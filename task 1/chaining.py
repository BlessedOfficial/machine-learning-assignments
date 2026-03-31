import os
from dotenv import load_dotenv
from openrouter import OpenRouter
import json

load_dotenv()

# Load API key once
api_key = os.getenv("OPENROUTER_API_KEY")

if not api_key:
    raise ValueError("API key not found. Make sure .env has OPENROUTER_API_KEY set.")

# Create client once
client = OpenRouter(api_key=api_key)

# Instructions
CLEAN_INSTRUCTION = """Clean and normalize the text in the triple quotes and return 
clean standardized text without any explanation. 
Fix all typos and grammatical errors. Expand all contractions and abbreviations."""

CLASSIFY_INSTRUCTION = """Information in the triple quotes is a ticket. 
Determine the ticket category and extract key entities: product name, issue type, urgency, and description. 
Return the information in a JSON object."""

GENERATE_INSTRUCTION = """Based on the ticket information in the triple quotes, generate a helpful response to the customer. 
Address the customer's issue and provide clear next steps or solutions. 
Make sure the response is concise and informative. If the issue is urgent, prioritize that in the response. 
Use a friendly and professional tone.
Avoid generic responses and tailor the answer to the specific issue described in the ticket.
Avoid asking for more information if the ticket already contains sufficient details. 
If asking for more information is necessary, provide an email address or contact method for the customer to reach out to,rather than asking for more details in the response.
If the issue is complex, break down the solution into clear steps.
If the issue is related to a specific product, provide relevant information about that product in the response.
"""

# Main pipeline
def generate_response(user_input):
    cleaned = clean_user_input(user_input)
    classified_json_text = classify_input(cleaned)
    
    # Parse JSON safely
    try:
        classified_data = json.loads(classified_json_text)
    except json.JSONDecodeError:
        # fallback if the model returned malformed JSON
        classified_data = classified_json_text
    
    response_text = generate_ticket_response(classified_data)
    return response_text

# Step 1: Clean the input
def clean_user_input(user_input):
    prompt = f"{CLEAN_INSTRUCTION}\n\"\"\"\n{user_input}\n\"\"\""
    result = client.chat.send(
        model="openrouter/free",
        messages=[{"role": "user", "content": prompt}],
    )
    return result.choices[0].message.content

# Step 2: Classify input
def classify_input(cleaned_input):
    prompt = f"{CLASSIFY_INSTRUCTION}\n\"\"\"\n{cleaned_input}\n\"\"\""
    result = client.chat.send(
        model="openrouter/free",
        messages=[{"role": "user", "content": prompt}],
    )
    return result.choices[0].message.content

# Step 3: Generate response
def generate_ticket_response(classified_data):
    # If classified_data is still a string, use as-is
    if isinstance(classified_data, dict):
        classified_text = json.dumps(classified_data)
    else:
        classified_text = str(classified_data)

    prompt = f"{GENERATE_INSTRUCTION}\n\"\"\"\n{classified_text}\n\"\"\""
    result = client.chat.send(
        model="openrouter/free",
        messages=[{"role": "user", "content": prompt}],
    )
    return result.choices[0].message.content