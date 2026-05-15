# ingest.py

import json

from embeddings import EmbeddingService
from vector_db import VectorDB

from config import (
    COLLECTION_NAME,
    EMBEDDING_DEVICE,
    EMBEDDING_MODEL,
    QDRANT_HOST,
    QDRANT_PORT,
)


with open("chunks.json", "r", encoding="utf-8") as f:
    chunks = json.load(f)

print(f"[ingest] loaded chunks: {len(chunks)}")

embedder = EmbeddingService(
    EMBEDDING_MODEL,
    EMBEDDING_DEVICE
)

db = VectorDB(
    QDRANT_HOST,
    QDRANT_PORT,
    COLLECTION_NAME
)

texts_for_embedding = []
payloads = []

for c in chunks:
    text = str(c.get("text", ""))
    summary = str(c.get("summary", ""))

    keywords = c.get("keywords", [])
    questions = c.get("questions", [])
    entities = c.get("entities", [])

    if not isinstance(keywords, list):
        keywords = []

    if not isinstance(questions, list):
        questions = []

    if not isinstance(entities, list):
        entities = []

    searchable_text = " ".join([
        text,
        summary,
        " ".join(map(str, keywords)),
        " ".join(map(str, questions)),
        " ".join(map(str, entities)),
    ])

    texts_for_embedding.append(searchable_text)

    payloads.append({
        "id": c.get("id", ""),
        "section": c.get("section", ""),
        "subsection": c.get("subsection", ""),
        "type": c.get("type", ""),
        "text": text,
        "summary": summary,
        "keywords": keywords,
        "questions": questions,
        "entities": entities
    })

print("[ingest] embedding...")

vectors = embedder.embed_documents(
    texts_for_embedding
)

print(f"[ingest] vectors: {len(vectors)}")
print(f"[ingest] dim: {len(vectors[0])}")

db.upsert(vectors, payloads)

print("[ingest] done")