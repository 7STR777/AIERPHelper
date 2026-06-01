from sentence_transformers import SentenceTransformer

class EmbeddingService:
    def __init__(self, model_name: str, device: str = "cpu"):
        try:
            print(f"[embed] loading from local cache: {model_name} on {device}", flush=True)
            self.model = SentenceTransformer(model_name, device=device, local_files_only=True)
            self.device = device
            return
        except Exception as local_exc:
            print(f"[embed] local cache load failed: {local_exc}", flush=True)

        try:
            print(f"[embed] loading from HuggingFace: {model_name} on {device}", flush=True)
            self.model = SentenceTransformer(model_name, device=device)
            self.device = device
            return
        except Exception as remote_exc:
            print(f"[embed] gpu load failed, fallback to cpu: {remote_exc}", flush=True)

        # Final fallback for environments where CUDA is not available.
        print(f"[embed] final cpu fallback for model: {model_name}", flush=True)
        self.model = SentenceTransformer(model_name, device="cpu")
        self.device = "cpu"

    def embed_documents(self, texts):
        return self.model.encode(texts, normalize_embeddings=True).tolist()

    def embed_query(self, query):
        return self.model.encode([query], normalize_embeddings=True)[0]
