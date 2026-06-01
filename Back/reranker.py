from sentence_transformers import CrossEncoder


class Reranker:
    def __init__(self):
        print("[reranker] loading model")
        self.model = CrossEncoder(
            "BAAI/bge-reranker-base",
            device="cuda"
        )

    def rank(self, query: str, docs: list[str], top_k: int = 5):
        if not docs:
            return []

        pairs = [(query, d) for d in docs]

        scores = self.model.predict(
            pairs,
            batch_size=8,   # 🔥 FIX
            show_progress_bar=False
        )

        ranked = sorted(
            zip(docs, scores),
            key=lambda x: x[1],
            reverse=True
        )

        return [d for d, _ in ranked[:top_k]]