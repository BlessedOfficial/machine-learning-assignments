import json


def strip_markdown_json(raw: str) -> str:
    response = raw.strip()

    if "```" in response:
        parts = response.split("```")
        for part in parts:
            if "{" in part or "[" in part:
                response = part
                break

    response = response.replace("json", "", 1)
    return response.strip()


def parse_llm_response(content: str | dict) -> str | dict:
    if isinstance(content, dict):
        return content
    if not isinstance(content, str):
        return str(content) if content is not None else ""

    stripped = content.strip()
    if not stripped:
        return ""

    candidate = strip_markdown_json(stripped)
    if not candidate.startswith(("{", "[")):
        return stripped

    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return stripped


def clean_llm_json(raw_json):
    return parse_llm_response(raw_json)
