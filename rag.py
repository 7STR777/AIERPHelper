import re
import time
from typing import List

from config import *
from embeddings import EmbeddingService
from vector_db import VectorDB
from llm_qwen import QwenLLM

from bm25 import BM25Retriever
from reranker import Reranker


NO_INFO = "Нет информации в базе"


class RAGPipeline:
    def __init__(self, chunks: list[str]):
        print("[RAG+] init")

        self.embedder = EmbeddingService(EMBEDDING_MODEL, EMBEDDING_DEVICE)
        self.db = VectorDB(QDRANT_HOST, QDRANT_PORT, COLLECTION_NAME)
        self.llm = QwenLLM()

        self.bm25 = BM25Retriever(chunks)
        self.reranker = Reranker()

        self.chunks = chunks

    def _tokens(self, text: str):
        return re.findall(r"\w+", text.lower())

    def _vector_search(self, query: str, k: int = 20):
        q_vec = self.embedder.embed_query(query)
        return self.db.search(q_vec, limit=k)

    def retrieve(self, query: str, k: int = 20):
        # BM25
        bm25_docs = self.bm25.search(query, k=10)
        bm25_texts = [d for d, _ in bm25_docs]

        # Vector
        vector_hits = self._vector_search(query, k=k)
        vector_texts = [r.payload["text"] for r in vector_hits if "text" in r.payload]

        # merge
        merged = bm25_texts + vector_texts

        # dedup
        seen = set()
        unique = []
        for m in merged:
            fp = m[:200]
            if fp in seen:
                continue
            seen.add(fp)
            unique.append(m)

        return unique[:20]

    def _is_relevant(self, query: str, docs: list[str]) -> bool:
        if not docs:
            return False

        q = self._tokens(query)
        q = [t for t in q if len(t) > 2]

        if not q:
            return True

        text = " ".join(docs).lower()

        hits = sum(1 for t in q if t in text)
        ratio = hits / len(q)

        return hits >= 1 or ratio >= 0.10

    def _build_context(self, docs: list[str], max_chars: int):
        out, total = [], 0

        for d in docs:
            if total >= max_chars:
                break
            cut = d[: max_chars - total]
            out.append(cut)
            total += len(cut)

        return "\n\n".join(out)

    def _prompt(self, context: str, query: str):
        return f"""<|im_start|>system
Ты - корпоративный ассистент. Отвечай СТРОГО на основе предоставленного контекста. Если в контексте нет ответа, скажи: {NO_INFO}. Отвечай только на русском языке.<|im_end|>
<|im_start|>user
Контекст:
{context}

Вопрос: {query}

Дай краткий ответ (1-5 предложений), используя только информацию из контекста.<|im_end|>
<|im_start|>assistant
"""

    def _clean(self, text: str):
        if not text:
            return NO_INFO
        
        # Remove system/user/assistant markers
        text = re.sub(r'<\|im_start\|>.*?<\|im_end\|>', '', text, flags=re.DOTALL)
        
        # Remove common artifacts
        text = text.strip()
        
        # Stop at first occurrence of instruction-like phrases
        stop_phrases = [
            "CONTEXT:", "QUESTION:", "ANSWER:", 
            "НЕ ДОБАВЛЯЙ", "НЕДОБАВЛЯЙ",
            "<|im_start|>", "<|im_end|>",
            "\n\n\n", "```"
        ]
        
        for phrase in stop_phrases:
            idx = text.find(phrase)
            if idx != -1:
                text = text[:idx].strip()
        
        # If text is too short or just contains garbage
        if len(text) < 10:
            return NO_INFO
        
        # Remove repeated words (common LLM hallucination)
        words = text.split()
        if len(words) > 3 and len(set(words)) / len(words) < 0.3:  # High repetition
            return NO_INFO
        
        return text

    def generate(self, query: str):
        t0 = time.perf_counter()

        docs = self.retrieve(query, k=10)

        docs = docs[:10]
        docs = self.reranker.rank(query, docs, top_k=5)

        if not self._is_relevant(query, docs):
            return {"answer": NO_INFO, "contexts": docs}

        context = self._build_context(docs, 1200)

        prompt = self._prompt(context, query)

        answer = self.llm.generate(
            prompt,
            max_tokens=100,
            temperature=0.1,
            top_p=0.8
            )

        answer = self._clean(answer)

        t1 = time.perf_counter()
        print(f"[RAG+] total={t1-t0:.2f}s")

        return {
            "answer": answer,
            "contexts": docs
        }