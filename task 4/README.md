## Task 4 Evaluation Metric

For this math task, we use a **two-stage numeric metric**:

1. **Exact match first** (strict): compare normalized numeric strings (e.g. `14` equals `14.0` after normalization).
2. **Numerical tolerance fallback** (precision-aware): if exact fails, compare numeric values with tolerance:
   - relative tolerance (`rel_tol`, default `1%`)
   - absolute tolerance (`abs_tol`, default `1e-9`)

If exact match fails, we also compute a **precision score**:

`precision = max(0, 1 - relative_error)`

This fits the task because GSM8K-style outputs are scalar numbers:
- **Exact match** is the primary metric and aligns with strict grading.
- **Tolerance match** is useful for benign numeric formatting/rounding variance while still penalizing larger errors.
- **Precision score** gives graded signal on near misses rather than a hard 0/1 only.

### Why this metric fits better than text metrics

- **Not F1**: token overlap is for span/text extraction and can reward verbose wrong text.
- **Not pass@k**: pass@k fits code-generation with multiple sampled programs; here we usually produce one final numeric answer.
- **Yes numeric tolerance**: directly measures mathematical closeness.

### Run evaluation

```powershell
cd "task 4"
.\.venv\Scripts\python.exe -m eval --strategy react
.\.venv\Scripts\python.exe -m eval --strategy plan_and_execute --rel-tol 0.01
.\.venv\Scripts\python.exe -m eval --strategy program_of_thought --limit 10
```

The evaluator compares each strategy result against `answers/answer.json` for each problem folder under `data/golden`.

## LLM-as-Judge Fallback

When both programmatic checks fail (**exact** and **tolerance** miss), evaluation falls back to an **LLM judge** for brittle cases (for example, free-form answer text).

- Programmatic path remains primary.
- Judge is only used on unresolved misses.
- Judge contributes a separate metric bucket: `judge_count` / `judge_rate`.

### Judge sanity check policy

Before trusting judge-assisted numbers, we sanity-check the judge against hand labels:

- Hand-grade at least **8** examples (we use `data/eval/judge_sanity_samples.jsonl`).
- Compute simple judge-human agreement accuracy.
- If agreement is **< 70%**, fail fast and fix the rubric/prompt before using judge results.

Run sanity only:

```powershell
cd "task 4"
.\.venv\Scripts\python.exe -m eval --judge-sanity-only
```

Run eval with judge fallback (default):

```powershell
.\.venv\Scripts\python.exe -m eval --strategy react
```

Disable judge fallback:

```powershell
.\.venv\Scripts\python.exe -m eval --strategy react --no-judge-fallback
```

## Pairwise Comparison (20 questions)

For strategy-vs-strategy comparison, we run the first 20 selected golden problems across all strategies and compute a **win matrix**:

- Cell `(A, B)` = number of problems where strategy `A` solved the problem and strategy `B` did not.
- Per-problem outcomes are also logged as `exact` / `tolerance` / `miss`.

Run command:

```powershell
cd "task 4"
.\.venv\Scripts\python.exe -m eval --pairwise-20 --no-judge-fallback
```

### Current run status

The run started and produced console logs, but stopped mid-way due OpenRouter daily free-tier quota:

- Error: `Rate limit exceeded: free-models-per-day`
- Generated log file: `eval/pairwise_20_console_output.txt`

### Win matrix (pending full run)

| strategy \ strategy | react | plan_and_execute | program_of_thought |
|---|---:|---:|---:|
| react | - | pending | pending |
| plan_and_execute | pending | - | pending |
| program_of_thought | pending | pending | - |
