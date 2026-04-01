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

# Step 2: Classify input
def classify_input(cleaned_input):
    prompt = f"{CLASSIFY_INSTRUCTION}\n\"\"\"\n{cleaned_input}\n\"\"\""
    result = client.chat.send(
        model="openrouter/free",
        messages=[{"role": "user", "content": prompt}],
    )
    return result.choices[0].message.content