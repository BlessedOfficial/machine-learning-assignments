
def clean_llm_json(response: str):
    response = response.strip()

    # Remove markdown code block
    if "```" in response:
        parts = response.split("```")
        # JSON is usually in the middle
        for part in parts:
            if "{" in part:
                response = part
                break

 
    response = response.replace("json", "", 1)

    return response.strip()