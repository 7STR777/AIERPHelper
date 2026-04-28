import os

QDRANT_HOST = os.getenv("QDRANT_HOST", "qdrant")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "new_rag_collection")

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")
EMBEDDING_DEVICE = os.getenv("EMBEDDING_DEVICE", "cuda")

MISTRAL_MODEL = os.getenv(
    "MISTRAL_MODEL_PATH",
    "/models/mistral-7b-instruct-v0.3-q4_k_m.gguf",
)
LLM_GPU_LAYERS = int(os.getenv("LLM_GPU_LAYERS", "-1"))
LLM_N_CTX = int(os.getenv("LLM_N_CTX", "4096"))
