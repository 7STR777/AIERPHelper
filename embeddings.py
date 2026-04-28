from sentence_transformers import SentenceTransformer

class EmbeddingService:
    def __init__(self, model_name: str, device: str = "cpu"):
        try:
            self.model = SentenceTransformer(model_name, device=device)
            self.device = device
        except Exception:
            # Fallback for environments where CUDA is not available.
            self.model = SentenceTransformer(model_name, device="cpu")
            self.device = "cpu"

    def embed_documents(self, texts):
        texts = [f"passage: {t}" for t in texts]
        return self.model.encode(texts, normalize_embeddings=True).tolist()

    def embed_query(self, query):
        return self.model.encode([f"query: {query}"], normalize_embeddings=True)[0]
