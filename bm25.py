from rank_bm25 import BM25Okapi
import re


class BM25Retriever:
    def __init__(self, chunks: list[str]):
        self.chunks = chunks
        self.tokenized = [self._tokenize(c) for c in chunks]
        self.bm25 = BM25Okapi(self.tokenized)

    def _tokenize(self, text: str):
        return re.findall(r"\w+", text.lower())

    def search(self, query: str, k: int = 10):
        tokens = self._tokenize(query)
        scores = self.bm25.get_scores(tokens)

        ranked = sorted(
            enumerate(scores),
            key=lambda x: x[1],
            reverse=True
        )[:k]

        return [(self.chunks[i], float(score)) for i, score in ranked]