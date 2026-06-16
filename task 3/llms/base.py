import asyncio

from openrouter import OpenRouter

from config import OPENROUTER_API_KEY
from utils.json_parser import parse_llm_response

if not OPENROUTER_API_KEY:
    raise ValueError("API key not found. Make sure .env has OPENROUTER_API_KEY set.")

client = OpenRouter(api_key=OPENROUTER_API_KEY)


async def call_openrouter(messages, model, temperature=0.7):
    for attempt in range(3):
        try:
            response = await asyncio.to_thread(
                client.chat.send,
                model=model,
                messages=messages,
                temperature=temperature,
            )

            if not response.choices:
                raise ValueError("No choices returned")

            content = response.choices[0].message.content
            return parse_llm_response(content)

        except Exception as e:
            if attempt == 2:
                raise RuntimeError(f"LLM call failed ({model}): {e}") from e
            await asyncio.sleep(1)
