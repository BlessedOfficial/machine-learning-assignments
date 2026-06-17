C:\Users\bless\Desktop\machine-learning-assignments\task 1>python main.py
Enter a customer support ticket:
My account was hacked and I can no longer access it.

Processing ticket...

User input: My account was hacked and I can no longer access it.

Cleaning input...

Cleaned Input: {
    "cleaned_text": "My account was hacked and I cannot access it."
}

Generating sentiment and keywords...

Sentiment and Keywords: {'sentiment': 'negative', 'keywords': ['account', 'hacked', 'access']}

Classifying input...

Classified Data: {'category': 'escalation', 'product': 'account', 'issue_type': 'security breach', 'urgency': 'high', 'description': 'Account was hacked and user cannot access it.'}

Generating response...

--- Iteration 1 ---
Review Raw: {
  "approved": true
}
Review Clean: {
  "approved": true
}
⚠️ Solution approved too early (iteration 1). Continuing reflection.

--- Iteration 2 ---
Review Raw: 

{"approved": true}
Review Clean: {"approved": true}
✅ Solution approved

Response: {'category': 'escalation', 'product': 'account', 'issue_type': 'security breach', 'urgency': 'high', 'description': 'Account was hacked and user cannot access it.', 'solution_steps': ['Immediately reset the account password to a strong, unique one and check for any unauthorized changes to account details.', "Verify the user's identity through alternative contact methods or security questions to restore access and lock out any unauthorized users.", 'Instruct the user to review recent account activity for suspicious transactions, enable two-factor authentication, and monitor for further issues; offer to escalate to security team if needed.']}

C:\Users\bless\Desktop\machine-learning-assignments\task 1>