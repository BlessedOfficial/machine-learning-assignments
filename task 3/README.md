# AI.Inc Enterprise Knowledge Assistant

Production-oriented RAG assistant for internal policy Q&A: hybrid retrieval, multi-agent orchestration, layered safety guardrails, and full request observability.

**Course assignment:** [Task 3 — Safety, RAG & Communication](https://github.com/BeniaDev/agents_course_tsu/blob/main/task3.md)

---

## Table of contents

- [Features](#features)
- [Quick start](#quick-start)
- [Architecture](#architecture)
- [Usage](#usage)
- [Safety](#safety)
- [Observability & logs](#observability--logs)
- [Testing](#testing)
- [Data pipeline](#data-pipeline)
- [Retrieval & reranking](#retrieval--reranking)
- [Configuration reference](#configuration-reference)
- [Project structure](#project-structure)
- [Troubleshooting](#troubleshooting)

---

## Features

| Area | Implementation |
|------|----------------|
| **RAG** | Chroma dense + BM25 sparse, RRF fusion, cross-encoder rerank, citation metadata |
| **Agents** | Orchestrator-Worker topology with typed A2A envelopes (Pydantic-validated) |
| **Input safety** | Prompt injection, scope filter, PII detect/redact/refuse |
| **Output safety** | Citation discipline, grounding check, PII leak redaction, regenerate loop |
| **Access control** | Role-based chunk filtering (`intern` / `employee` / `manager` / `hr`) |
| **Observability** | Pipeline console log, agent trace JSON, guardrail incident log, rerank log |

---

## Quick start

### Prerequisites

- Python 3.11+ (project uses a local `.venv`)
- [uv](https://docs.astral.sh/uv/) recommended for dependency install
- [OpenRouter](https://openrouter.ai/) API key (free tier works; `--local` chunking avoids LLM quota for indexing)

### 1. Install

```powershell
cd "task 3"
uv venv
uv pip install -r requirements.txt
```

### 2. Configure

Create `.env` in the project root:

```env
OPENROUTER_API_KEY=your_key_here
SYNTHESIZER_MODEL=openrouter/free
```

See [Configuration reference](#configuration-reference) for all options.

### 3. Build the knowledge base

```powershell
.\.venv\Scripts\python.exe scripts\run_chunking.py --local
.\.venv\Scripts\python.exe scripts\build_chroma_index.py --reset
```

This produces **123 chunks** from **30** AI.Inc policy documents (no LLM calls with `--local`).

### 4. Run the full pipeline demo

```powershell
.\.venv\Scripts\python.exe scripts\run_pipeline_demo.py
```

Runs a **red-team** blocked request and a **happy-path** PTO question with full console logging (input guard → retrieval scores → agent messages → safety verdict → cited answer).

### 5. Interactive Q&A

```powershell
.\.venv\Scripts\python.exe main.py
```

On Windows, prefer `.\.venv\Scripts\python.exe` over bare `python` if Python is not on PATH. Alternatively:

```powershell
.\.venv\Scripts\Activate.ps1
python main.py
```

---

## Architecture

### End-to-end flow

```
Employee question
       │
       ▼
┌──────────────┐     PASS / REDACT / REJECT
│ Input guards │──────────────────────────────────► formal decline
└──────┬───────┘
       │ safe query
       ▼
┌──────────────┐  RetrievalRequest   ┌─────────────┐
│ Orchestrator │ ──────────────────► │  Retriever  │  hybrid + RRF + rerank + RBAC
└──────┬───────┘ ◄────────────────── └─────────────┘
       │ RetrievalResult
       ▼
┌──────────────┐  SynthesisRequest   ┌─────────────┐
│ Orchestrator │ ──────────────────► │ Synthesizer │  grounded draft + chunk IDs
└──────┬───────┘ ◄────────────────── └─────────────┘
       │ SynthesisResult
       ▼
┌──────────────┐  SafetyReviewRequest ┌────────────────┐
│ Orchestrator │ ───────────────────► │ Safety Reviewer │  approve | redact | regenerate
└──────┬───────┘ ◄─────────────────── └────────────────┘
       │ SafetyVerdict (regenerate → loop, max rounds)
       ▼
  Final answer + logs
```

### Ingestion & retrieval stack

```
Corpus (30 docs) → chunking → chunks.jsonl
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
        Dense (Chroma)                  Sparse (BM25)
              │                               │
              └─────────── RRF fusion ──────────┘
                              │
                         Reranker (cross-encoder)
                              │
                    Top-K chunks + citations → LLM
```

### Multi-agent protocol

Agents communicate through **`AgentEnvelope`** messages (`agents/protocol.py`): `sender`, `recipient`, `correlation_id`, `message_type`, and a **typed payload** validated by Pydantic on every send. No free-form inter-agent strings.

| Message type | Schema | Flow |
|--------------|--------|------|
| User intake | `UserRequest` | Client → Orchestrator |
| Retrieval | `RetrievalRequest` / `RetrievalResult` | Orchestrator ↔ Retriever |
| Synthesis | `SynthesisRequest` / `SynthesisResult` | Orchestrator ↔ Synthesizer |
| Safety | `SafetyReviewRequest` / `SafetyVerdict` | Orchestrator ↔ Safety Reviewer |
| Terminal | `WorkflowComplete` / `WorkflowError` | Orchestrator (local) |

JSON Schema exports: `data/schemas/` (regenerate with `scripts/export_agent_schemas.py`).

**Feedback loop:** when `SafetyVerdict.decision = regenerate`, the Orchestrator re-dispatches `SynthesisRequest` with structured `critique: list[SafetyIssue]` (capped by `MAX_SYNTHESIS_ROUNDS`, default `2`).

---

## Usage

### Scripts

| Command | Purpose |
|---------|---------|
| `scripts/run_pipeline_demo.py` | Happy path + red-team with full 5-section pipeline log |
| `scripts/run_redteam.py` | Run 8 adversarial input-guard tests (`--markdown` for table) |
| `scripts/run_agent_trace_demo.py` | Blocked-request agent trace (no LLM) |
| `scripts/export_agent_schemas.py` | Export JSON Schema for all message payloads |
| `scripts/build_chroma_index.py --query "…"` | Test retrieval + rerank from CLI |
| `main.py` | Interactive Q&A with role prompt |

### Retrieval CLI examples

```powershell
.\.venv\Scripts\python.exe scripts\build_chroma_index.py --query "PTO carryover" --k 5
.\.venv\Scripts\python.exe scripts\build_chroma_index.py --query "PTO carryover" --no-rerank
.\.venv\Scripts\python.exe scripts\build_chroma_index.py --query "PTO carryover" --rerank-mode mmr
```

### Role-based access

`main.py` prompts for role (`intern`, `employee`, `manager`, `hr`, `admin`) or set `USER_ROLE=intern`. Manager-only and HR-only chunks are filtered before synthesis. Re-chunk and re-index after changing RBAC metadata:

```powershell
.\.venv\Scripts\python.exe scripts\run_chunking.py --local
.\.venv\Scripts\python.exe scripts\build_chroma_index.py --reset
```

### Citation format

Answers must cite retrieved chunks inline, e.g. `` [`pto-and-leave-policy#loc-001`] ``. The synthesizer prompt and post-LLM guards enforce:

- Every factual claim includes a chunk ID citation, **or**
- An explicit gap: *"I don't have enough information on X in the retrieved excerpts."*

---

## Safety

### Input guardrails (`workflow/input_guardrails.py`)

Runs **before** retrieval. Decisions: `PASS`, `REDACT`, or `REJECT`.

| Check | Examples | Action |
|-------|----------|--------|
| Prompt injection | Ignore instructions, reveal system prompt, jailbreak | **Reject** |
| Out of scope | Medical/legal advice, coworker salary, general knowledge | **Reject** |
| Credit card (Luhn-valid) | 13–19 digit PAN in message | **Reject** |
| Email, phone, SSN | Personal contact info in message | **Redact** (or **Reject** if `PII_ACTION=refuse`) |

Legitimate AI.Inc questions (PTO, VPN, benefits, onboarding) are **not** blocked.

### Output guardrails (Safety Reviewer Agent)

| Check | Module | Action |
|-------|--------|--------|
| Meta-leak | `workflow/guardrails.py` | Regenerate or decline |
| Citation discipline | `workflow/citations.py` | Regenerate if facts lack chunk IDs |
| Grounding | `workflow/grounding.py` | Strip / flag / reject unsupported claims |
| PII leak | `workflow/pii_utils.py` | Redact in final answer (keeps `@ai.inc` contacts) |

`GROUNDING_MODE`: `strip` (default) | `flag` | `reject`

### Role-based access control

| Documents | Minimum role |
|-----------|--------------|
| business-travel, expense-reimbursement, security-incident-response, data-classification | `manager` |
| confidentiality-nda | `hr` |
| All others | `employee` |

Hierarchy: `intern` = `employee` < `manager` < `hr` < `admin`

---

## Observability & logs

Every request produces structured artifacts for debugging and grading.

### Pipeline console log (primary deliverable)

Printed when `SHOW_PIPELINE_LOG=true` (default). Saved to `data/logs/pipeline/{correlation_id}.pipeline.log.json`.

| Section | Content |
|---------|---------|
| **1. Input guardrail** | `PASS` / `REDACT` / `REJECT` + rule name |
| **2. Retrieval** | Dense, BM25, RRF, and rerank score tables; final chunk order |
| **3. Inter-agent messages** | `sender -> recipient [type] summary` |
| **4. Safety reviewer** | Verdict per round; feedback-loop annotations |
| **5. Final answer** | Response text + extracted inline citations |

Sample output: `data/logs/pipeline/SAMPLE-console-output.txt`

### Other logs

| File | Contents |
|------|----------|
| `data/logs/traces/{correlation_id}.json` | Full A2A message sequence |
| `data/logs/agent_messages.jsonl` | Raw envelope stream (append-only) |
| `data/logs/guardrail_incidents.jsonl` | Rejections: timestamp, rule, redacted input, stage |
| `data/logs/rerank.jsonl` | Rerank before/after scores per query |

### Incident log schema

```json
{
  "timestamp": "2026-05-31T12:00:00+00:00",
  "rule_triggered": "prompt_injection",
  "redacted_input": "Ignore all previous instructions…",
  "decision": "block",
  "stage": "input"
}
```

---

## Testing

### Red-team suite

Eight adversarial prompts in `data/redteam/prompts.json` (injection, jailbreak, PII extraction):

```powershell
.\.venv\Scripts\python.exe scripts\run_redteam.py
.\.venv\Scripts\python.exe scripts\run_redteam.py --markdown
```

Expected result when guardrails are working: **8/8 PASS**

| ID | Category | Expected rule |
|----|----------|---------------|
| `rt-inj-01`, `rt-inj-02` | injection | `prompt_injection` |
| `rt-jb-01` … `rt-jb-03` | jailbreak | `prompt_injection` |
| `rt-pii-01` | pii_extraction | `pii_credit_card` |
| `rt-pii-02`, `rt-pii-03` | pii_extraction | `out_of_scope_hr_confidential` |

### Pipeline demo (recommended for reviewers)

```powershell
.\.venv\Scripts\python.exe scripts\run_pipeline_demo.py
```

Demo 1 blocks at input guardrail. Demo 2 runs retrieval + mock synthesis (`DEMO_MOCK_SYNTHESIS`) for a deterministic cited answer without consuming LLM quota.

---

## Data pipeline

### Corpus

- **30** minimal internal documents in `data/corpus/ai_inc/`
- Provenance note in `data/corpus/README.md` (AI-generated for this assignment)
- Ingestion skips `README.md` and files prefixed with `_`

Regenerate corpus:

```powershell
.\.venv\Scripts\python.exe scripts\build_detailed_corpus.py
```

### Chunking

**Local (recommended)** — one chunk per bullet line, zero API calls:

```powershell
.\.venv\Scripts\python.exe scripts\run_chunking.py --local
```

**LLM pipeline** — propositions + agentic grouping (~50+ OpenRouter calls for full corpus):

```powershell
.\.venv\Scripts\python.exe scripts\run_chunking.py --limit-files 1
.\.venv\Scripts\python.exe scripts\run_chunking.py --no-agentic
```

Output: `data/chunks/chunks.jsonl` + `manifest.json`. On `free-models-per-day` errors, use `--local` or add credits.

### Vector index

```powershell
.\.venv\Scripts\python.exe scripts\build_chroma_index.py --reset
.\.venv\Scripts\python.exe scripts\build_chroma_index.py --query "How many PTO days?"
```

- Persist path: `data/chroma/`
- Collection: `ai_inc_knowledge`
- Embeddings: `sentence-transformers/all-MiniLM-L6-v2` (cosine similarity)

---

## Retrieval & reranking

### Hybrid retrieval

| Retriever | Strength | Weakness |
|-----------|----------|----------|
| Dense (Chroma) | Semantic paraphrases ("time off" → PTO) | Misses exact IDs, dates |
| Sparse (BM25) | Exact tokens (`HR-PTO-2024-01`, `March 31`) | No semantic understanding |

### RRF fusion

Dense and BM25 scores are on incomparable scales, so we fuse **ranks** with Reciprocal Rank Fusion:

\[
\text{RRF}(d) = \sum_i \frac{1}{k + r_i(d)}
\]

Default `RRF_K=60` (Cormack et al., SIGIR 2009). Chunks ranked highly by both retrievers surface first (`Matched via: bm25, dense` in context).

### Reranking

After RRF, **20 candidates** are re-scored to **5** before the LLM.

| `RERANKER_MODE` | Description |
|-----------------|-------------|
| `cross_encoder` (default) | `ms-marco-MiniLM-L-6-v2`; best accuracy, runs locally |
| `llm` | OpenRouter rates passages 0–10 |
| `mmr` | Embedding diversity; reduces duplicate policy chunks |
| `none` | Pass through RRF order |

Disable console rerank table: `LOG_RERANK_SCORES=false`. Disable hybrid: `USE_HYBRID_RETRIEVAL=false`. Disable rerank: `USE_RERANKER=false`.

---

## Configuration reference

All settings load from `.env` via `config.py`.

### Required

| Variable | Description |
|----------|-------------|
| `OPENROUTER_API_KEY` | OpenRouter API key for synthesizer (and optional LLM reranker) |

### Models

| Variable | Default |
|----------|---------|
| `SYNTHESIZER_MODEL` | `openrouter/free` |
| `SAFETY_REVIEWER_MODEL` | `meta-llama/llama-3.2-3b-instruct:free` |
| `EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` |
| `RERANKER_MODEL` | `cross-encoder/ms-marco-MiniLM-L-6-v2` |
| `CHUNKING_MODEL` | same as synthesizer |

Use a **different** model for `SAFETY_REVIEWER_MODEL` than `SYNTHESIZER_MODEL`. Browse free models: https://openrouter.ai/models?max_price=0

### Retrieval

| Variable | Default | Description |
|----------|---------|-------------|
| `USE_HYBRID_RETRIEVAL` | `true` | Dense + BM25 + RRF |
| `USE_RERANKER` | `true` | Cross-encoder rerank |
| `RERANKER_MODE` | `cross_encoder` | `cross_encoder` \| `llm` \| `mmr` \| `none` |
| `RETRIEVAL_CANDIDATE_K` | `20` | Candidates per retriever before fusion |
| `RETRIEVAL_TOP_K` | `5` | Chunks passed to synthesizer |
| `RETRIEVAL_MIN_SCORE` | `0.35` | Dense score floor (dense-only mode) |
| `RRF_K` | `60` | RRF constant |
| `MMR_LAMBDA` | `0.7` | MMR diversity weight |

### Safety

| Variable | Default | Description |
|----------|---------|-------------|
| `PII_ACTION` | `redact` | `redact` \| `refuse` for input PII |
| `GROUNDING_MODE` | `strip` | `strip` \| `flag` \| `reject` |
| `ENABLE_RBAC` | `true` | Role-based chunk filtering |
| `DEFAULT_USER_ROLE` | `employee` | Default when role not specified |
| `MAX_SYNTHESIS_ROUNDS` | `2` | Max regenerate loops after safety reject |

### Observability

| Variable | Default | Description |
|----------|---------|-------------|
| `SHOW_PIPELINE_LOG` | `true` | Print 5-section pipeline log to console |
| `PIPELINE_LOG_DIR` | `data/logs/pipeline` | Pipeline log JSON directory |
| `AGENT_TRACE_DIR` | `data/logs/traces` | Per-request agent trace JSON |
| `LOG_AGENT_MESSAGES` | `true` | Append raw envelopes to JSONL |
| `AGENT_MESSAGE_LOG_PATH` | `data/logs/agent_messages.jsonl` | Envelope log path |
| `LOG_GUARDRAIL_INCIDENTS` | `true` | Log guardrail rejections |
| `GUARDRAIL_INCIDENT_LOG_PATH` | `data/logs/guardrail_incidents.jsonl` | Incident log path |
| `LOG_RERANK_SCORES` | `true` | Print rerank table to console |
| `RERANK_LOG_PATH` | `data/logs/rerank.jsonl` | Rerank log path |

### Storage paths

| Variable | Default |
|----------|---------|
| `CHROMA_PATH` | `data/chroma` |
| `CHROMA_COLLECTION` | `ai_inc_knowledge` |
| `CHUNKS_PATH` | `data/chunks/chunks.jsonl` |
| `CORPUS_DIR` | `data/corpus/ai_inc` |
| `DOC_BASE_URL` | `https://docs.ai.inc/internal` |

### Demo / development

| Variable | Description |
|----------|-------------|
| `DEMO_MOCK_SYNTHESIS` | `true` = deterministic synthesizer (no LLM) for pipeline demo |
| `USER_ROLE` | Skip role prompt in automation |

---

## Project structure

```
task 3/
├── main.py                     # Interactive Q&A entry point
├── config.py                   # Environment configuration
├── agents/
│   ├── protocol.py             # Pydantic schemas + AgentEnvelope
│   ├── bus.py                  # Message broker (Orchestrator-Worker)
│   ├── trace.py                # Per-request message trace
│   ├── pipeline_log.py         # 5-section console log
│   ├── orchestrator_agent.py
│   ├── retriever_agent.py
│   ├── synthesizer_agent.py
│   └── safety_reviewer_agent.py
├── workflow/
│   ├── simple_qa.py            # Q&A facade → orchestrator
│   ├── input_guardrails.py
│   ├── scope_filter.py
│   ├── guardrails.py
│   ├── citations.py
│   ├── grounding.py
│   ├── pii_utils.py
│   ├── rbac.py
│   └── incident_log.py
├── rag/
│   ├── retriever.py
│   ├── retrieval_diagnostics.py
│   ├── hybrid.py               # RRF fusion
│   ├── bm25.py / sparse_index.py
│   ├── rerank_pipeline.py
│   ├── chunk_corpus.py
│   ├── access_control.py       # min_role metadata
│   └── index_chroma.py
├── llms/                       # OpenRouter clients
├── embeddings/
├── vector_store/chroma_client.py
├── reranker/                   # cross-encoder, LLM, MMR
├── data/
│   ├── corpus/ai_inc/          # 30 source documents
│   ├── chunks/chunks.jsonl     # 123 indexed chunks
│   ├── chroma/                 # vector store
│   ├── schemas/                # JSON Schema exports
│   ├── redteam/prompts.json
│   └── logs/                   # pipeline, traces, incidents, rerank
└── scripts/
    ├── run_pipeline_demo.py
    ├── run_redteam.py
    ├── run_chunking.py
    └── build_chroma_index.py
```

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `python` not found | Use `.\.venv\Scripts\python.exe` or activate the venv |
| OpenRouter 429 / daily quota | Chunk with `--local`; reduce LLM calls; add credits |
| Empty retrieval / no chunks | Run `build_chroma_index.py --reset` after chunking |
| Chroma already indexed | Pass `--reset` to rebuild |
| HF Hub rate limits | Set `HF_TOKEN` for faster embedding downloads |
| Safety model same as synthesizer | Set distinct `SAFETY_REVIEWER_MODEL` in `.env` |
| Manager policy not returned | Set role to `manager`; verify RBAC + re-index |
| No pipeline log on console | Set `SHOW_PIPELINE_LOG=true` |

---

## Model defaults summary

| Component | Default model | Location |
|-----------|---------------|----------|
| Synthesizer | `openrouter/free` | `llms/synthesizer/` |
| Safety reviewer | `meta-llama/llama-3.2-3b-instruct:free` | `llms/safety_reviewer/` |
| Embeddings | `all-MiniLM-L6-v2` | `embeddings/` |
| Reranker | `ms-marco-MiniLM-L-6-v2` | `reranker/` |
| Vector store | ChromaDB (persistent) | `vector_store/` |
| Sparse retrieval | BM25 (`rank_bm25`) | `rag/bm25.py` |

All models are overridable via `.env`.
