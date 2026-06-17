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

### Accuracy and 95% confidence intervals

Report accuracy as **correct/total with a 95% Wilson interval** (binomial proportion). Example:

`90.0% [95% CI: 69.9%–97.2%]`

We use Wilson (not a normal approximation) because n is small (20 in pairwise runs). A 1000-sample bootstrap gives similar intervals; Wilson is the default.

**Winner policy:** do **not** declare a winner unless:
- the lead is **≥3 correct answers** on the comparable set (a 2-point lead on 20 examples is noise), and
- the top strategy's 95% CI **does not overlap** the runner-up's.

The win matrix still shows head-to-head problem counts, but matrix cells alone are not enough to crown a winner.

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

## Pairwise Comparison

For strategy-vs-strategy comparison, we run the same golden subset across all strategies and compute a **win matrix**:

- Cell `(A, B)` = number of problems where strategy `A` solved the problem and strategy `B` did not.
- Per-problem outcomes are also logged as `exact` / `tolerance` / `miss`.
- Default subset size is **4** problems for smoke tests (`--pairwise-limit`).
- Each solve writes traces under `Observability/logs/{trace_id}/`.
- Console is mirrored to `eval/pairwise_20_console_output.txt`.
- If tokens/quota run out, each strategy stops early and the matrix uses completed runs.

Run command (token-friendly default):

```powershell
cd "task 4"
.\.venv\Scripts\python.exe -m eval --pairwise --no-judge-fallback
```

Larger run (20 problems):

```powershell
.\.venv\Scripts\python.exe -m eval --pairwise-20 --no-judge-fallback --compare-baseline
```

### Baseline and regression diff

Reference accuracy is in `data/eval/baseline.json`. Compare a new run without re-reading the README:

```powershell
# Offline: diff last console log vs baseline (no API calls)
.\.venv\Scripts\python.exe -m eval --diff-baseline-log
make eval-diff

# Full rerun + delta
make eval
```

Update baseline after an intentional change: `make write-baseline`

### Results (20-question run, `--no-judge-fallback`)

| Strategy | Accuracy (95% Wilson CI) |
|----------|--------------------------|
| react | 20/20 = 100.0% [83.9%–100.0%] |
| plan_and_execute | 18/20 = 90.0% [69.9%–97.2%] |
| program_of_thought | 20/20 = 100.0% [83.9%–100.0%] |

**Declared winner:** none — react and program_of_thought tie at 20/20 (overlapping CIs); plan_and_execute is only 2 behind (18 vs 20), which is below the ≥3 margin threshold.

Win matrix (A solved, B missed):

| strategy \ strategy | react | plan_and_execute | program_of_thought |
|---|---:|---:|---:|
| react | - | 2 | 0 |
| plan_and_execute | 0 | - | 0 |
| program_of_thought | 0 | 2 | - |

(plan_and_execute missed #03 and #19; react and program_of_thought each solved all 20.)

## Failure mode taxonomy (pairwise-20, hand-classified)

We reviewed console logs and traces for **10 failure episodes** across strategies (2 graded misses, 3 tolerance-only modeling errors, 5 recovered-but-wrong-process cases). Categories are not mutually exclusive; each row picks the **dominant** cause.

### Categories used

| Category | Meaning |
|----------|---------|
| **arithmetic_error** | Correct plan, wrong intermediate number (often mental math without calculator). |
| **problem_misread** | Wrong reading of problem structure (discount scope, interest model, etc.). |
| **wrong_tool_call** | Malformed `Action:` line or invalid executor verb; tool never runs. |
| **plan_abandoned** | Executor stops following the plan after errors and guesses `finish[…]`. |
| **reasoning_loop** | Multiple consecutive steps with no new computation (format errors or empty turns). |

*Not observed in this run:* judge disagreement (judge disabled), PoT sandbox crashes, or true infinite loops (all runs hit `finish` within step limits).

### Classified failures

**1. plan_and_execute · #03 `gsm8k-test-57` → arithmetic_error (graded miss: 16 vs 83)**  
Plan is sound: subtract truck weight, divide by 15, floor. Executor writes `5000 − 3755 = 245` in a `step_done` **without calling the calculator**, then divides 245/15 → 16. The error is a single digit slip in subtraction (1245→245). ReAct and PoT both computed 1245 explicitly and got 83.

**2. plan_and_execute · #19 `gsm8k-test-608` → problem_misread (graded miss: −2.5 vs 8)**  
Golden applies 30% off the **combined** $60 outfit. The plan discounts **only the shirt** ($25→$17.50), adds full-price shorts ($35), gets $52.50 > $50, and answers −2.5. The arithmetic is consistent with a wrong story problem model, not a slip.

**3–5. All strategies · #06 `gsm8k-test-187` → problem_misread (tolerance: 106.12 vs 106)**  
Golden uses **simple** interest: $2/month × 3 = $6 → $106. All three strategies model **compound** growth `100 × 1.02³ ≈ 106.12`. Tool/code math is internally correct; the failure is choosing the wrong financial model. Tolerance grading masks this as a “win.”

**6. react · #04 `gsm8k-test-66` → wrong_tool_call (recovered, exact)**  
`calculator[(2*5+2*1)*4]` returns 48 on step 1, but the model emits no valid `finish[48]`—the next three steps are `Error: Unrecognized action`. It recovers on step 5 with `finish[48]` without re-verifying. Correct answer, fragile path.

**7. react · #01 `gsm8k-test-15` → wrong_tool_call (recovered, exact)**  
Step 2 packs `calculator[…] Observation: 125 finish[125]` into one line. Parser rejects it; steps 3–4 are format errors. Shows ReAct format brittleness under rate-limit retries.

**8. react · #05 `gsm8k-test-176` → reasoning_loop (recovered, exact)**  
Step 1 is an empty/malformed action (immediate format error). Model reasons correctly in step 2 and `finish[100]` without ever using the calculator.

**9. plan_and_execute · #14 `gsm8k-test-479` → plan_abandoned (recovered, exact)**  
After `calculator[5000*2]=10000`, the next three executor turns are format errors. Plan step 4 jumps to `finish[15400]` with no hotel-cost calculation in the trace—yet 15400 is correct. Likely lucky synthesis/hallucination rather than executed reasoning.

**10. react · #06 `gsm8k-test-187` → reasoning_loop (tolerance)**  
Three consecutive `Unrecognized action` observations (steps 1–3) before a valid `calculator[100*(1.02)**3]` on step 4. Rate-limit retries correlate with empty generations; wasted steps before the modeling error in #3–5.

### Distribution (10 episodes, dominant category)

| Category | Count | Graded wrong | Recovered / tolerance |
|----------|------:|-------------:|----------------------:|
| problem_misread | 4 | 1 (#19) | 3 (#06 ×3 strategies) |
| wrong_tool_call | 3 | 0 | 3 (#01, #04, partial #06) |
| arithmetic_error | 1 | 1 (#03) | 0 |
| plan_abandoned | 1 | 0 | 1 (#14 lucky) |
| reasoning_loop | 1 | 0 | 1 (#05) |

**Takeaways:** plan_and_execute’s two misses split cleanly into **arithmetic** vs **problem misread**. The dominant cross-strategy noise is **action-format parsing** (ReAct and executor), which often recovers but burns steps and API calls. **Tolerance** hides systematic **modeling** errors on #06—all strategies “pass” with the wrong interest interpretation. PoT had no sandbox failures in this slice; its failures, when they occur, would likely cluster under problem_misread in code logic rather than tool format.

## Trace observations (pairwise-20 logs)

From **72 traced runs** (`Observability/logs/`, 24 per strategy):

**ReAct “failures” are almost never the calculator.** Across all ReAct traces, **69% of observation steps** (22/32) are error strings—not numeric tool output. **21 of 22** are `Error: Unrecognized action` (malformed `Thought:`/`Action:` lines, often after rate-limit retries). The calculator tool failed only **once** in the entire log set. So ReAct friction is **format compliance**, not bad arithmetic from tools.

**plan_and_execute dominates token spend.** It consumed **~64% of prompt tokens** across all three strategies (114k vs 41k ReAct, 24k PoT) despite the same problem count—**~7.3 LLM calls per problem** on average (max 10) vs **~2.3** for ReAct and **1.0** for PoT (one generation + execute per problem). Most of that overhead is planner + per-plan-step executor turns, including **~17% of executor observations** that are format errors (`Use calculator[expr], step_done[result], or finish[number]`).

## Replayability

Re-run a single golden problem from any saved trace folder under `Observability/logs/{trace_id}/`:

```powershell
cd "task 4"

# Inspect original trace (no API calls)
.\.venv\Scripts\python.exe -m Observability.replay 0c7685f5-8cba-4acd-84e1-9c1a91391e05 --show-only

# Re-run with same strategy/model (new trace ID)
.\.venv\Scripts\python.exe -m Observability.replay 0c7685f5-8cba-4acd-84e1-9c1a91391e05

# Override strategy and/or model
.\.venv\Scripts\python.exe -m Observability.replay 0c7685f5-8cba-4acd-84e1-9c1a91391e05 --strategy react
.\.venv\Scripts\python.exe -m Observability.replay 0c7685f5-8cba-4acd-84e1-9c1a91391e05 --model openrouter/free --diff
```

The replay reads `run_start` from `reasoning_steps.jsonl` (question, problem ID, strategy), resolves golden text if needed, and writes a **new** trace folder. `--diff` compares final answers and event counts vs the original.


