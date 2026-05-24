# ── LM Studio connection ──────────────────────────────────────────────────────
LM_STUDIO_BASE_URL = "http://127.0.0.1:1234/v1"
LM_STUDIO_API_KEY  = "lm-studio"

# ── Model names (must match exactly what LM Studio shows) ────────────────────
# Load Nous-Hermes-2 in LM Studio for best results.
# If you only have Phi-3.1-mini, use that name for all three.
HERMES_MODEL  = "nous-hermes-2-mistral-7b-dpo"   # for compliance/critique agent
PLANNER_MODEL = "nous-hermes-2-mistral-7b-dpo"   # or phi-3.1-mini
GENERAL_MODEL = "nous-hermes-2-mistral-7b-dpo"   # for analysis + drafting

# ── Generation ────────────────────────────────────────────────────────────────
MAX_TOKENS   = 512
TEMPERATURE  = 0.1

# ── Orchestration ─────────────────────────────────────────────────────────────
MAX_ITERATIONS       = 3
COMPLIANCE_THRESHOLD = 0.80   # score needed to pass compliance

# ── Chunking ──────────────────────────────────────────────────────────────────
CHUNK_SIZE    = 1500
CHUNK_OVERLAP = 150

# ── Paths ─────────────────────────────────────────────────────────────────────
OUTPUTS_DIR     = "outputs"
SAMPLE_DOCS_DIR = "sample_docs"
MEMORY_FILE     = "memory/long_term_memory.json"