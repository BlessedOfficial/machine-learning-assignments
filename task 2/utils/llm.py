import os
from dotenv import load_dotenv
from openrouter import OpenRouter
import json
import asyncio

from utils.json_parser import clean_llm_json

load_dotenv()

# Load API key once
api_key = os.getenv("OPENROUTER_API_KEY")
if not api_key:
    raise ValueError("API key not found. Make sure .env has OPENROUTER_API_KEY set.")

# Create client once
client = OpenRouter(api_key=api_key)

async def call_llm(messages, model="openrouter/free", temperature=0.7):
    for attempt in range(3):
        try:
            response = client.chat.send(
                model=model,
                messages=messages,
                temperature=temperature
            )

            if not response.choices:
                raise ValueError("No choices returned")

            content = response.choices[0].message.content

            cleaned = clean_llm_json(content)
            return cleaned if cleaned else content

        except Exception as e:
            if attempt == 2:
                raise RuntimeError(f"LLM call failed: {e}")
            await asyncio.sleep(1)