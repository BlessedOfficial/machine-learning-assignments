# Task 4 — GSM8K Strategy Evaluation

Compares three reasoning strategies on a golden set of grade-school math problems: **ReAct**, **plan-and-execute**, and **program-of-thought (PoT)**. Each problem lives in `data/golden/{id}/` with `questions/question.json` and `answers/answer.json`.

---

## Quick start

```powershell
cd "task 4"
uv venv && uv pip install -r requirements.txt
.\.venv\Scripts\python.exe -m eval --pairwise --no-judge-fallback
```

Requires `OPENROUTER_API_KEY` in `.env` (or environment). Use `.\.venv\Scripts\python.exe` on Windows if `python` is not on PATH.

---

## Layout

| Path | Purpose |
|------|---------|
| `strategies/` | `react`, `plan_and_execute`, `program_of_thought`, `utils/` |
| `data/golden/` | 50 problems (`1`–`50`) |
| `data/eval/` | `baseline.json`, judge sanity samples |
| `eval/` | Metrics, runner, pairwise comparison, stats |
| `Observability/` | Per-run traces (`logs/{trace_id}/`) |

---

## Scoring

Two-stage numeric metric (GSM8K-style scalar answers):

1. **Exact match** — normalized string equality (`14` ≡ `14.0`).
2. **Tolerance fallback** — `rel_tol=1%`, `abs_tol=1e-9` if exact fails.

Optional **LLM judge** when both fail (`--no-judge-fallback` to disable). Judge sanity gate: ≥70% agreement on `data/eval/judge_sanity_samples.jsonl` (`--judge-sanity-only`).

**Reporting:** accuracy as `correct/total` with **95% Wilson CI**. No winner unless lead ≥3 correct *and* top CI does not overlap runner-up.

---

## Commands

| Goal | Command |
|------|---------|
| Single strategy | `python -m eval --strategy react` |
| Pairwise (default 4 problems) | `python -m eval --pairwise --no-judge-fallback` |
| Pairwise 20 + baseline diff | `make eval` |
| Offline regression check | `make eval-diff` |
| Slice (e.g. problems 36–50) | `python -m eval --pairwise --offset 35 --pairwise-limit 15 --no-judge-fallback` |
| Extend golden set | `make extend-golden` |
| Replay a trace | `make replay TRACE_ID=<uuid> REPLAY_ARGS="--show-only"` |

Console logs: `eval/pairwise_20_console_output.txt`, `eval/pairwise_36_50_console_output.txt`. Traces: `Observability/logs/{trace_id}/`.

---

## Results (pairwise-20, no judge)

| Strategy | Accuracy (95% Wilson CI) |
|----------|--------------------------|
| react | 20/20 — 100.0% [83.9%–100.0%] |
| program_of_thought | 20/20 — 100.0% [83.9%–100.0%] |
| plan_and_execute | 18/20 — 90.0% [69.9%–97.2%] |

**Winner:** none (react ≡ PoT; plan_and_execute within 2 of leaders, below ≥3 margin).

| A \ B | react | plan_and_execute | program_of_thought |
|-------|------:|-----------------:|-------------------:|
| react | — | 2 | 0 |
| plan_and_execute | 0 | — | 0 |
| program_of_thought | 0 | 2 | — |

plan_and_execute missed **#03** (`gsm8k-test-57`, arithmetic) and **#19** (`gsm8k-test-608`, problem misread). Baseline: `data/eval/baseline.json`.

**Pairwise 36–50 (15 problems):** all strategies 14/15; shared miss **#45** (`gsm8k-test-823`).

---

## Failure taxonomy (pairwise-20)

Hand-classified from console logs and traces. Dominant category per episode.

| Category | Count | Notes |
|----------|------:|-------|
| problem_misread | 4 | e.g. compound vs simple interest (#06); discount scope (#19) |
| wrong_tool_call | 3 | ReAct format errors; often recovered |
| arithmetic_error | 1 | plan_and_execute #03 — mental subtraction slip |
| plan_abandoned | 1 | Executor format errors then lucky `finish` |
| reasoning_loop | 1 | Empty/malformed steps before recovery |

**Observations:** ReAct friction is mostly `Unrecognized action` (format), not calculator failure. plan_and_execute uses ~64% of prompt tokens vs ReAct/PoT. Tolerance grading masks modeling errors on #06 (all strategies ≈106.12 vs golden 106).

Full episode notes: see `eval/pairwise_20_console_output.txt` and traces under `Observability/logs/`.

---

## Observability & replay

Each run logs `llm_calls.jsonl`, `tool_calls.jsonl`, and `reasoning_steps.jsonl` per `trace_id`.

```powershell
python -m Observability.replay <trace_id> --show-only
python -m Observability.replay <trace_id> --strategy react --diff
```

Replay reads the original `run_start`, re-runs the problem, and writes a new trace folder.
