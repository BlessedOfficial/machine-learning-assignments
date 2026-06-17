import json

def clean_llm_json(raw_json):
    try:
        # Attempt to parse the JSON
        return json.loads(raw_json)
    except json.JSONDecodeError as e:
        print(f"JSON decoding error: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None