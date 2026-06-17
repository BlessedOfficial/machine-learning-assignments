# Agentic Reasoning Lab

Multi-strategy reasoning (ReAct, Plan-and-Execute, Self-Consistency, etc.) with a rigorous eval harness, structured traces, and replay tooling.

**Assignment:** [Task 4 — Evaluation & Advanced Reasoning](https://github.com/BeniaDev/agents_course_tsu/blob/main/task4.md)

---

## Quick start

**Prerequisites:** Python 3.11+, `.venv`, [OpenRouter](https://openrouter.ai/) API key (or local Ollama).

```powershell
cd "task 4"
uv venv && uv pip install -r requirements.txt
```

`.env` (minimum):

```env
OPENROUTER_API_KEY=your_key_here
SOLVER_MODEL=openrouter/free
JUDGE_MODEL=openrouter/free
```

Use `.\.venv\Scripts\python.exe` on Windows if `python` is not on PATH.

Ask a question (simple LLM chat):

```powershell
.\.venv\Scripts\python.exe main.py
```

Copy `.env.example` to `.env` and set `OPENROUTER_API_KEY` (same key as task 3 works).

---

## What to build

1. **Strategies** (`strategies/`) — ≥ 3 reasoning patterns behind a shared `Strategy` interface
2. **Eval** (`eval/`) — golden set (≥ 20), metrics, LLM judge, win matrix, 95% CIs, `baseline.json`
3. **Observability** (`observability/`) — JSONL traces, replay tool, failure taxonomy
4. **Tools** (`tools/`) — shared calculator / executor / retriever used fairly across strategies

---

## Project layout

```
strategies/
  base.py              # Problem, Trace, Strategy interface
  react/               # ReAct (Reason–Act–Observe)
  plan_and_execute/    # Plan-and-Execute
  program_of_thought/  # Program-of-Thought (advanced — generate & run Python)
eval/            # golden set, metrics, judge, statistical tests
observability/   # trace logger, replay, analysis
tools/           # shared tool implementations
data/            # benchmark subset, baselines, traces
```

---

## Progress

| Area | Status |
|------|--------|
| Strategy interface + stub | Done |
| ReAct (`strategies/react/`) | Scaffolded |
| Plan-and-Execute (`strategies/plan_and_execute/`) | Scaffolded |
| Program-of-Thought (`strategies/program_of_thought/`) — advanced | Scaffolded |
| Eval harness + golden set | Not started |
| Observability + replay | Not started |
| Results tables in README | Not started |
