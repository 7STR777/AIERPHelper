from sentence_transformers import SentenceTransformer

class EmbeddingService:
    def __init__(self, model_name: str):
        self.model = SentenceTransformer(model_name)

    def embed_documents(self, texts):
        texts = [f"passage: {t}" for t in texts]
        return self.model.encode(texts, normalize_embeddings=True).tolist()

    def embed_query(self, query):
        return self.model.encode([f"query: {query}"], normalize_embeddings=True)[0]