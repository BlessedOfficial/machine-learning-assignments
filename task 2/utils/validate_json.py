def validate_json(result):
    if not result:
        raise ValueError("Invalid JSON returned by LLM")
    return result