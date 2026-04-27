from embeddings import EmbeddingService
from vector_db import VectorDB
from llm_mistral import MistralLLM
from config import *

class RAGPipeline:
    def __init__(self):
        self.embedder = EmbeddingService(EMBEDDING_MODEL)
        self.db = VectorDB(QDRANT_HOST, QDRANT_PORT, COLLECTION_NAME)
        self.llm = MistralLLM()

    def retrieve(self, query: str, k: int = 5):
        q_vec = self.embedder.embed_query(query)
        results = self.db.search(q_vec, limit=k)
        docs = [r.payload["text"] for r in results]
        print("\n=== RETRIEVED DOCS ===")
        for i, d in enumerate(docs):
            print(f"{i+1}. {d[:200]}")
        print("======================\n")

        return [r.payload["text"] for r in results]

    def generate(self, query: str):
        docs = self.retrieve(query)
        context = "\n\n".join(docs)

        prompt = f"""
Ты отвечаешь ТОЛЬКО по контексту.

Если ответа нет — скажи: "Нет информации в базе".

Контекст:
{context}

Вопрос:
{query}

Ответ:
"""

        return self.llm.generate(prompt)
