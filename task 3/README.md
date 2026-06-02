# AI.Inc Enterprise Knowledge Assistant

RAG-based internal policy Q&A with hybrid retrieval, multi-agent orchestration, and input/output guardrails.

| Task | Summary | Spec |
|------|---------|------|
| [Task 2](../task%202/README.md) | Routed research + Reflexion (Best-of-N, fan-in, critic loop) | [task2.md](https://github.com/BeniaDev/agents_course_tsu/blob/main/task2.md) |
| **Task 3** (here) | RAG + safety + Orchestrator–Worker agents + RBAC + logging | [task3.md](https://github.com/BeniaDev/agents_course_tsu/blob/main/task3.md) |

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

## Logs & samples

| Artifact | Path |
|----------|------|
| Pipeline log (guard, retrieval scores, messages, verdict, answer) | `data/logs/pipeline/{correlation_id}.pipeline.log.json` |
| Agent message trace | `data/logs/traces/{correlation_id}.json` |
| Guardrail rejections | `data/logs/guardrail_incidents.jsonl` |
| Sample console output | `data/logs/pipeline/SAMPLE-console-output.txt` |

Set `SHOW_PIPELINE_LOG=true` (default) to print the pipeline log in the terminal.

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
