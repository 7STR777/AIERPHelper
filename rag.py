from config import COLLECTION_NAME, EMBEDDING_DEVICE, EMBEDDING_MODEL, QDRANT_HOST, QDRANT_PORT
from embeddings import EmbeddingService
from llm_mistral import MistralLLM
from vector_db import VectorDB


class RAGPipeline:
    def __init__(self):
        self.embedder = EmbeddingService(EMBEDDING_MODEL, EMBEDDING_DEVICE)
        self.db = VectorDB(QDRANT_HOST, QDRANT_PORT, COLLECTION_NAME)
        self.llm = MistralLLM()

    def retrieve(self, query: str, k: int = 5):
        q_vec = self.embedder.embed_query(query)
        results = self.db.search(q_vec, limit=k)
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
        answer = self.llm.generate(prompt).strip()
        return {"answer": answer, "contexts": docs}
