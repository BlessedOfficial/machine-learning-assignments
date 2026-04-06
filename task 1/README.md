# 🧠 Task 1 – Foundation Patterns

## 📌 Assignment Link

👉 https://github.com/BeniaDev/agents_course_tsu/blob/main/task1.md

---

## 📖 Overview

This task involves building an **automated customer support ticket processor** using core LLM patterns:

- Prompt Chaining
- Routing
- Parallelization
- Reflection

---

## ✅ Progress Tracker

| Feature            | Description                                                        | Status         |
| ------------------ | ------------------------------------------------------------------ | -------------- |
| 🔗 Prompt Chaining | 3-step pipeline (Preprocess → Classify → Respond)                  | ✅ Done        |
| 🔀 Routing         | Branch into 3+ categories (technical, billing, inquiry, complaint) | ✅ Done        |
| ⚡ Parallelization | Run 2+ tasks concurrently (e.g. sentiment + extraction)            | ✅ Done        |
| 🔁 Reflection      | Self-evaluate and improve response (2 iterations)                  | ✅ Done        |
| 📊 Dataset         | Use or create 10+ sample support tickets                           | ✅ Done        |
| 🧪 Testing         | Show example input/output                                          | ✅ Done        |
| 📝 Logs            | Display pipeline steps, routing, parallel tasks, reflection loop   | ✅ Done        |
| 📘 README          | Setup, architecture, usage                                         | 🚧 In Progress |
| 🌿 Git Flow        | Use `develop` + `main` branches properly                           | ✅ Done        |

---

## 📂 Files

```
task1/
├── README.md
├── main.py
├── api.py
├── billing.py
├── general.py
├── instructions.txt
├──technical.py
├── utils.py
├──escalation.py

```

```
## Workflow

User Input
    │
    ▼
[1] Preprocessing (Cleaning & Normalization)
    │
    ▼
[2] Parallel Tasks
    ├── Sentiment Analysis
    └── Keyword Extraction
    │
    ▼
[3] Classification (Combine Results)
    │
    ▼
[4] Routing
    ├── Technical
    ├── Billing
    ├── General Inquiry
    └── Complaint / Escalation
    │
    ▼
[5] Response Generation
    │
    ▼
[6] Reflection Loop (Improve Response)
```

## Setup

1. Clone the repository:

   ```bash
   git clone <your-repo-url>
   cd task1
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Create API keys with OpenRouter and add them to a `.env` file:

   ```env
   OPENROUTER_API_KEY=your_api_key
   ```

---

## How to Run

```bash
python main.py
```

---

## Sample Tickets

### Technical

- I can't log into my account even after resetting my password.
- The app crashes every time I open it on my phone.
- The dashboard is showing a blank screen.
- The API integration is failing with a 500 error.
- My data is not saving after I submit the form.

### Billing

- I was charged twice for my subscription this month.
- My payment went through but my account is still not upgraded.
- Can I get a refund for an accidental purchase?
- I need an invoice for my last payment.
- When does my subscription renew?

### Escalation

- I noticed suspicious activity on my account. Please respond urgently.
- My account was hacked and I can no longer access it.
- This issue is critical and affecting my business operations.
- I have contacted support multiple times and haven't received help.
- Your system deleted my data without warning. I need this resolved immediately.

### General

- How do I update my profile information?
- Do you offer a dark mode feature?
- Where can I change my notification settings?
- Can you explain how your pricing works?
- Is there a mobile app available?
