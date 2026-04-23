import os
from dotenv import load_dotenv
from openrouter import OpenRouter
import json
import asyncio

from json_parser import clean_llm_json

load_dotenv()

# Load API key once
api_key = os.getenv("OPENROUTER_API_KEY")
if not api_key:
    raise ValueError("API key not found. Make sure .env has OPENROUTER_API_KEY set.")

# Create client once
client = OpenRouter(api_key=api_key)

async def call_llm(messages, model, temperature=0.7):
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature
        )
        content = response.choices[0].message.content
        return clean_llm_json(content)
    except Exception as e:
        print(f"Error calling LLM: {e}")
        return None