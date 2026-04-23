import asyncio
from routing.supervisor import classify_input
import json

async def main():
    user_input = input("Enter a user query:\n")
    classified_data = await classify_input(user_input)
    print(classified_data)

if __name__ == "__main__":
    asyncio.run(main())