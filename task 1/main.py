
from chaining import generate_response


with open("input.txt", "r") as file:
    user_input = file.read()
response = generate_response(user_input)

print(response)
