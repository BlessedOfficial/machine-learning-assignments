# Agentic Reasoning Lab

Multi-strategy reasoning (ReAct, Plan-and-Execute, Self-Consistency, etc.) with a rigorous eval harness, structured traces, and replay tooling.

**Assignment:** [Task 4 — Evaluation & Advanced Reasoning](https://github.com/BeniaDev/agents_course_tsu/blob/main/task4.md)

---

## Quick start

**Prerequisites:** Python 3.11+, `.venv`, 

```powershell
cd "task 4"
uv venv && uv pip install -r requirements.txt
```

### GSM8K golden set (35 problems)


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
eval/            # metrics, ranking, stats, judge, baseline
observability/   # JSONL trace logger, replay
llms/            # solver + judge (dual LLM)
tools/           # subprocess code executor (PoT sandbox)
data/
  golden/
    gsm8k_test_35_questions.jsonl
    gsm8k_test_35_answers.jsonl
```

---
## Progress

| Area | Status |
|------|--------|
| Strategy interface + stub | Done |
| ReAct (`strategies/react/`) | Scaffolded |
| Plan-and-Execute (`strategies/plan_and_execute/`) | Scaffolded |
| Program-of-Thought (`strategies/program_of_thought/`) — advanced | Scaffolded |
| GSM8K golden set (questions + answers split) | Done |
| Accuracy / letter grades / ranking (`eval/ranking.py`) | Done |
| Solver + judge LLMs (dual-model anti-collusion) | Done |
| JSONL tracing + replay (`observability/`) | Done |
| Stats (Wilson CI, bootstrap, McNemar) | Done |
| LLM-as-judge + sanity check hook (`eval/judge.py`) | Done |
| Full eval harness (run all strategies, baseline) | Not started |
