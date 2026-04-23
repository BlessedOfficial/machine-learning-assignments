import os
from dotenv import load_dotenv
from openrouter import OpenRouter
import json
import asyncio


load_dotenv()

# Load API key once
api_key = os.getenv("OPENROUTER_API_KEY")

if not api_key:
    raise ValueError("API key not found. Make sure .env has OPENROUTER_API_KEY set.")

# Create client once
client = OpenRouter(api_key=api_key)
