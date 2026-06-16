from config import SAFETY_REVIEWER_MODEL, SYNTHESIZER_MODEL
from llms.base import call_openrouter

SAFETY_FALLBACK_MODELS = list(
    dict.fromkeys(
        [
            SAFETY_REVIEWER_MODEL,
            "meta-llama/llama-3.2-3b-instruct:free",
        ]
    )
)


async def call_safety_reviewer(messages, temperature=0.0):
    last_error = None

    for model in SAFETY_FALLBACK_MODELS:
        if model == SYNTHESIZER_MODEL:
            continue

        try:
            return await call_openrouter(
                messages, model=model, temperature=temperature
            )
        except Exception as e:
            last_error = e
            print(f"  Warning: safety model '{model}' unavailable ({e})")

    raise RuntimeError(
        "No safety reviewer model available. Set SAFETY_REVIEWER_MODEL in .env "
        "to a different OpenRouter model than SYNTHESIZER_MODEL."
    ) from last_error
