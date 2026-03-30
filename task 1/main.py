from openrouter import OpenRouter

client = OpenRouter(api_key="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")

response = client.chat.send(
    model="openrouter/free",                  
    messages=[
        {"role": "user", "content": "Write a one-sentence bedtime story about a unicorn."}
    ],
)

print(response.choices[0].message.content)       
print("Used model:", response.model)          