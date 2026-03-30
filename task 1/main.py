import os
from dotenv import load_dotenv
from openrouter import OpenRouter


load_dotenv()  

# Get the API key
api_key = os.getenv("OPENROUTER_API_KEY")
print("API key loaded:", api_key is not None)

if not api_key:
    raise ValueError("API key not found. Make sure .env has OPENROUTER_API_KEY set.")

# Create OpenRouter client
client = OpenRouter(api_key=api_key)

# Send a test request
response = client.chat.send(
    model="openrouter/free",
    messages=[{"role": "user", "content": "Write a one-sentence bedtime story about a unicorn."}]
)

# Print results
print(response.choices[0].message.content)
print("Used model:", response.model)