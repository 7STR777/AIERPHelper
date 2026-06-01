import os

QDRANT_HOST = os.getenv("QDRANT_HOST", "qdrant")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "new_rag_collection")

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")
EMBEDDING_DEVICE = os.getenv("EMBEDDING_DEVICE", "cuda")

LLM_MODEL_PATH = os.getenv("LLM_MODEL_PATH", "/models/qwen2.5-3b-instruct-q4_k_m.gguf")
LLM_GPU_LAYERS = int(os.getenv("LLM_GPU_LAYERS", "20"))
LLM_N_CTX = int(os.getenv("LLM_N_CTX", "1536"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "200"))
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.1"))
LLM_TOP_P = float(os.getenv("LLM_TOP_P", "0.9"))
LLM_TOP_K = int(os.getenv("LLM_TOP_K", "40"))
LLM_REPEAT_PENALTY = float(os.getenv("LLM_REPEAT_PENALTY", "1.15"))
LLM_N_BATCH = int(os.getenv("LLM_N_BATCH", "256"))
LLM_N_UBATCH = int(os.getenv("LLM_N_UBATCH", "256"))
LLM_N_THREADS = int(os.getenv("LLM_N_THREADS", "8"))
LLM_VERBOSE = os.getenv("LLM_VERBOSE", "false").lower() == "true"
LLM_FLASH_ATTN = os.getenv("LLM_FLASH_ATTN", "true").lower() == "true"

RAG_TOP_K = int(os.getenv("RAG_TOP_K", "4"))
RAG_MAX_CONTEXT_CHARS = int(os.getenv("RAG_MAX_CONTEXT_CHARS", "2600"))

WORKER_HOST = os.getenv("WORKER_HOST", "0.0.0.0")
WORKER_PORT = int(os.getenv("WORKER_PORT", "9000"))
