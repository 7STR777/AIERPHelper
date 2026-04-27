import json
from embeddings import EmbeddingService
from vector_db import VectorDB
from config import *

# load chunks (already prepared)
with open("chunks.json", "r", encoding="utf-8") as f:
    chunks = json.load(f)

embedder = EmbeddingService(EMBEDDING_MODEL)
db = VectorDB(QDRANT_HOST, QDRANT_PORT, COLLECTION_NAME)

texts = [f"passage: {c['text']}" for c in chunks]

print("Всего чанков:", len(chunks))

vectors = embedder.embed_documents(texts)

print("Размер вектора:", len(vectors[0]))

payloads = [
    {
        "text": c["text"],
        "section": c.get("section", ""),
        "id": c.get("id", "")
    }
    for c in chunks
]

db.upsert(vectors, payloads)

print("Ingestion completed")