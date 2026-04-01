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
| 🔀 Routing         | Branch into 3+ categories (technical, billing, inquiry, complaint) | 🚧 In Progress |
| ⚡ Parallelization | Run 2+ tasks concurrently (e.g. sentiment + extraction)            | ⏳             |
| 🔁 Reflection      | Self-evaluate and improve response (2 iterations)                  | ⏳             |
| 📊 Dataset         | Use or create 10+ sample support tickets                           | ⏳             |
| 🧪 Testing         | Show example input/output                                          | ⏳             |
| 📝 Logs            | Display pipeline steps, routing, parallel tasks, reflection loop   | ⏳             |
| 📘 README          | Setup, architecture, usage                                         | 🚧 In Progress |
| 🌿 Git Flow        | Use `develop` + `main` branches properly                           | ⏳             |

---

## 📂 Files

```
task1/
├── README.md
├── main.py
├── chaining.py
├── input.txt
```

---

> Note: `chaining.py` contains the core chaining logic. The main app imports `clean_user_input` from `chaining.py` and applies chaining in the overall pipeline:
>
> **Clean User Input → Classify → Route → Generate Response**

     ┌───────────────────┐
     │  User Input       │
     └────────┬──────────┘
              │
              ▼
     ┌───────────────────┐
     │ Clean User Input  │
     └────────┬──────────┘
              │
              ▼
     ┌───────────────────┐
     │   Classification  │
     │  (category + info)│
     └────────┬──────────┘
              │
              ▼
     ┌───────────────────┐
     │      Routing      │
     │ (technical, billing│
     │  general, escalation│
     │  unsure)          │
     └────────┬──────────┘
              │
              ▼
     ┌───────────────────┐
     │   Solution /      │
     │  Response Steps   │
     └───────────────────┘

--
