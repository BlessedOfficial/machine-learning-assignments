from config import SYNTHESIZER_MODEL
from llms.base import call_openrouter


async def call_synthesizer(messages, temperature=0.7):
    return await call_openrouter(
        messages, model=SYNTHESIZER_MODEL, temperature=temperature
    )
