import json
import asyncio
from utils.llm import call_llm
from utils.json_parser import clean_llm_json
from utils.validate_json import validate_json
from prompts.prompts import SCIENTIFIC_PROMPT


async def decompose_scientific_query(user_input):
    prompt = SCIENTIFIC_PROMPT["decompose"].format(query=user_input)

    response = await call_llm([
        {"role": "user", "content": prompt}
    ])

    result = clean_llm_json(response)

    return validate_json(result)


async def execute_fan_out(tasks):

    async def run_task(task):   
        prompt = task["query"]

        response = await call_llm([
            {"role": "user", "content": prompt}
        ])

        cleaned = clean_llm_json(response)
        validated = validate_json(cleaned)

        return {
            "agent": task.get("agent"),
            "result": validated
        }

    results = await asyncio.gather(
        *[run_task(task) for task in tasks],
        return_exceptions=True
    )

    clean_results = []
    for r in results:
        if isinstance(r, Exception):
            clean_results.append({"error": str(r)})
        else:
            clean_results.append(r)

    return clean_results


async def fan_in_scientific_responses(responses):

    safe_responses = [
        r for r in responses
        if isinstance(r, dict) and "result" in r
    ]

    prompt = SCIENTIFIC_PROMPT["fan_in"].format(
        query=json.dumps(safe_responses)
    )

    response = await call_llm([
        {"role": "user", "content": prompt}
    ])
    
    result = clean_llm_json(response)

    return validate_json(result)