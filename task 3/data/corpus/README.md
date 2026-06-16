# AI.Inc Corpus — Source Notice (Assignment Metadata)

**For graders / repository readers only.** This file is **not** ingested into the RAG index. Employee-facing answers must not cite this file.

## Provenance

| Field | Value |
|-------|--------|
| Company (fictional) | AI.Inc |
| Document count | **30** minimal internal markdown files in `ai_inc/` |
| Generation | **AI-generated** synthetic corpus for Machine Learning coursework (Task 3) |
| Purpose | Enterprise Knowledge Assistant — RAG, guardrails, multi-agent communication |
| Author intent | Simulate HR, IT, security, onboarding, engineering, finance, legal, and workplace policies |

## Ingestion rule

When building the vector store, load **only** `ai_inc/*.md`. Do **not** chunk or embed:

- `data/corpus/README.md` (this file)
- Any file whose name starts with `_`

## Eval hint

Each document uses stable facts (numbers, SLAs, contact aliases) suitable for citation and retrieval evaluation.
