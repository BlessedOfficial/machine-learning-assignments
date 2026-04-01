
from routing import generate_response


print("Welcome to the Customer Support Ticket System!")
user_input = input("Please describe your issue: ")
response = generate_response(user_input)


print(response)
