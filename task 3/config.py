import os

from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

SYNTHESIZER_MODEL = os.getenv("SYNTHESIZER_MODEL", "openrouter/free")
SAFETY_REVIEWER_MODEL = os.getenv(
    "SAFETY_REVIEWER_MODEL", "meta-llama/llama-3.2-3b-instruct:free"
)
ENABLE_LLM_SAFETY_REVIEW = os.getenv(
    "ENABLE_LLM_SAFETY_REVIEW", "true"
).lower() in ("1", "true", "yes")

EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
)
RERANKER_MODEL = os.getenv(
    "RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2"
)
CHROMA_PATH = os.getenv("CHROMA_PATH", "data/chroma")
CHROMA_COLLECTION = os.getenv("CHROMA_COLLECTION", "ai_inc_knowledge")
CORPUS_DIR = os.getenv("CORPUS_DIR", "data/corpus/ai_inc")
CHUNKS_PATH = os.getenv("CHUNKS_PATH", "data/chunks/chunks.jsonl")
CHUNKING_MODEL = os.getenv("CHUNKING_MODEL", SYNTHESIZER_MODEL)
USE_AGENTIC_CHUNKER = os.getenv("USE_AGENTIC_CHUNKER", "true").lower() in (
    "1",
    "true",
    "yes",
)
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
DOC_BASE_URL = os.getenv("DOC_BASE_URL", "https://docs.ai.inc/internal")
RETRIEVAL_TOP_K = int(os.getenv("RETRIEVAL_TOP_K", "5"))
RETRIEVAL_CANDIDATE_K = int(os.getenv("RETRIEVAL_CANDIDATE_K", "20"))
RETRIEVAL_MIN_SCORE = float(os.getenv("RETRIEVAL_MIN_SCORE", "0.35"))
RRF_K = int(os.getenv("RRF_K", "60"))
USE_HYBRID_RETRIEVAL = os.getenv("USE_HYBRID_RETRIEVAL", "true").lower() in (
    "1",
    "true",
    "yes",
)
USE_RERANKER = os.getenv("USE_RERANKER", "true").lower() in ("1", "true", "yes")
RERANKER_MODE = os.getenv("RERANKER_MODE", "cross_encoder").lower()
RERANKER_LLM_MODEL = os.getenv("RERANKER_LLM_MODEL", SYNTHESIZER_MODEL)
MMR_LAMBDA = float(os.getenv("MMR_LAMBDA", "0.7"))
LOG_RERANK_SCORES = os.getenv("LOG_RERANK_SCORES", "true").lower() in (
    "1",
    "true",
    "yes",
)
RERANK_LOG_PATH = os.getenv("RERANK_LOG_PATH", "data/logs/rerank.jsonl")
PII_ACTION = os.getenv("PII_ACTION", "redact").lower()
LOG_GUARDRAIL_INCIDENTS = os.getenv("LOG_GUARDRAIL_INCIDENTS", "true").lower() in (
    "1",
    "true",
    "yes",
)
GUARDRAIL_INCIDENT_LOG_PATH = os.getenv(
    "GUARDRAIL_INCIDENT_LOG_PATH", "data/logs/guardrail_incidents.jsonl"
)
# Backward-compatible alias for input-only logging env var.
INPUT_GUARD_LOG_PATH = os.getenv(
    "INPUT_GUARD_LOG_PATH", GUARDRAIL_INCIDENT_LOG_PATH
)
LOG_INPUT_GUARDS = os.getenv("LOG_INPUT_GUARDS", str(LOG_GUARDRAIL_INCIDENTS)).lower() in (
    "1",
    "true",
    "yes",
)
DEFAULT_USER_ROLE = os.getenv("DEFAULT_USER_ROLE", "employee")
ENABLE_RBAC = os.getenv("ENABLE_RBAC", "true").lower() in ("1", "true", "yes")
GROUNDING_MODE = os.getenv("GROUNDING_MODE", "strip").lower()
MAX_SYNTHESIS_ROUNDS = int(
    os.getenv("MAX_SYNTHESIS_ROUNDS", os.getenv("MAX_SYNTHESIS_REGENERATIONS", "2"))
)
MAX_SYNTHESIS_REGENERATIONS = MAX_SYNTHESIS_ROUNDS
LOG_AGENT_MESSAGES = os.getenv("LOG_AGENT_MESSAGES", "true").lower() in (
    "1",
    "true",
    "yes",
)
AGENT_MESSAGE_LOG_PATH = os.getenv(
    "AGENT_MESSAGE_LOG_PATH", "data/logs/agent_messages.jsonl"
)
AGENT_TRACE_DIR = os.getenv("AGENT_TRACE_DIR", "data/logs/traces")
PIPELINE_LOG_DIR = os.getenv("PIPELINE_LOG_DIR", "data/logs/pipeline")
SHOW_PIPELINE_LOG = os.getenv("SHOW_PIPELINE_LOG", "true").lower() in (
    "1",
    "true",
    "yes",
)
