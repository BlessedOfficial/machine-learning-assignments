import asyncio
from routing.supervisor import classify_input, route_issue

import json

async def main():
    user_input = input("Enter a user query:\n")
    classified_data = await classify_input(user_input)
    print("\nClassified Data:", classified_data)
    response = route_issue(classified_data)
    print("\nResponse:", response)
    

if __name__ == "__main__":
    asyncio.run(main())