# AI.Inc Enterprise Knowledge Assistant

RAG-based internal policy Q&A with hybrid retrieval, multi-agent orchestration, and input/output guardrails.

**Assignment:** [Task 3 — Safety, RAG & Communication](https://github.com/BeniaDev/agents_course_tsu/blob/main/task3.md)

---

## Quick start

**Prerequisites:** Python 3.11+, `.venv`, [OpenRouter](https://openrouter.ai/) API key.

```powershell
cd "task 3"
uv venv && uv pip install -r requirements.txt
```

`.env` (minimum):

```env
OPENROUTER_API_KEY=your_key_here
SYNTHESIZER_MODEL=openrouter/free
```

Build index (no LLM if you use `--local` chunking):

```powershell
.\.venv\Scripts\python.exe scripts\run_chunking.py --local
.\.venv\Scripts\python.exe scripts\build_chroma_index.py --reset
```

Run:

```powershell
.\.venv\Scripts\python.exe scripts\run_pipeline_demo.py   # red-team + happy path + full logs
.\.venv\Scripts\python.exe main.py                        # interactive Q&A
.\.venv\Scripts\python.exe scripts\run_redteam.py           # 8 adversarial tests (expect 8/8 PASS)
```

Example console output (no need to run locally): [SAMPLE-console-output.txt](data/logs/pipeline/SAMPLE-console-output.txt) · [SAMPLE-no-relevant-info-dogs.txt](data/logs/pipeline/SAMPLE-no-relevant-info-dogs.txt)

Use `.\.venv\Scripts\python.exe` on Windows if `python` is not on PATH.

---

## What it does

1. **Input guards** — injection, out-of-scope, PII → `PASS` / `REDACT` / `REJECT`
2. **Retrieve** — Chroma (dense) + BM25 (sparse) → RRF → cross-encoder rerank → top 5 chunks
3. **Agents** — Orchestrator delegates to Retriever, Synthesizer, Safety Reviewer via typed `AgentEnvelope` messages (`agents/protocol.py`)
4. **Output guards** — citations, grounding, PII redaction; Safety Reviewer can **regenerate** (max `MAX_SYNTHESIS_ROUNDS=2`)
5. **RBAC** — `intern` / `employee` / `manager` / `hr` filter chunks by `min_role`

Answers must cite full chunk IDs, e.g. `` [`pto-and-leave-policy#loc-001`] ``, or state missing info explicitly.

---

## Architecture (short)

```
Question → input guards → Orchestrator → Retriever → Synthesizer → Safety Reviewer → answer
                              ↑________________ regenerate + critique ________________|
```

Corpus: **30** docs → **123** chunks in `data/chunks/chunks.jsonl`, indexed in `data/chroma/`.

---

## Logs & console output samples

Every run prints a 5-section pipeline log when `SHOW_PIPELINE_LOG=true` (default). Saved JSON logs use `{correlation_id}` in the filename.

### Sample console output (checked in)

| Scenario | File |
|----------|------|
| Red-team block + happy-path PTO (`run_pipeline_demo.py`) | [SAMPLE-console-output.txt](data/logs/pipeline/SAMPLE-console-output.txt) |
| In-scope question, no matching policy (`main.py`, dogs example) | [SAMPLE-no-relevant-info-dogs.txt](data/logs/pipeline/SAMPLE-no-relevant-info-dogs.txt) |
| Blocked request agent trace (JSON) | [SAMPLE-blocked-request.trace.json](data/logs/traces/SAMPLE-blocked-request.trace.json) |

### Runtime log paths

| Artifact | Path |
|----------|------|
| Pipeline log JSON | `data/logs/pipeline/{correlation_id}.pipeline.log.json` |
| Agent message trace | `data/logs/traces/{correlation_id}.json` |
| Guardrail rejections | `data/logs/guardrail_incidents.jsonl` |

---

## Configuration

All options live in `config.py` / `.env`. Common knobs:

| Variable | Default | Notes |
|----------|---------|--------|
| `USE_HYBRID_RETRIEVAL` | `true` | Dense + BM25 + RRF |
| `USE_RERANKER` | `true` | Cross-encoder rerank |
| `RETRIEVAL_TOP_K` | `5` | Chunks to LLM |
| `ENABLE_RBAC` | `true` | Role-based filtering |
| `GROUNDING_MODE` | `strip` | `strip` \| `flag` \| `reject` |
| `ENABLE_LLM_SAFETY_REVIEW` | `true` | Hybrid LLM + rule safety review on drafts |
| `SAFETY_REVIEWER_MODEL` | `meta-llama/llama-3.2-3b-instruct:free` | OpenRouter model (must differ from synthesizer) |
| `DEMO_MOCK_SYNTHESIS` | — | Set `true` for demo without LLM |

---

## Project layout

`agents/` (orchestrator, protocol, bus) · `workflow/` (guardrails) · `rag/` (retrieval) · `llms/` · `scripts/` · `data/`

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `python` not found | `.\.venv\Scripts\python.exe` |
| OpenRouter quota | `run_chunking.py --local` |
| No retrieval hits | Re-run `build_chroma_index.py --reset` |
| `git add` fails on `.vs/` | Add `.vs/` to `.gitignore`; close Visual Studio; `git rm -r --cached .vs` if tracked |
