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

git clone
cd task1
pip install -r requirements.txt
Set API keys, OPENROUTER_API_KEY=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

```

## How to Run

python main.py

```
