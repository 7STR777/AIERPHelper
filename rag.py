import re
import time

from config import (
    COLLECTION_NAME,
    EMBEDDING_DEVICE,
    EMBEDDING_MODEL,
    QDRANT_HOST,
    QDRANT_PORT,
    RAG_MAX_CONTEXT_CHARS,
    RAG_TOP_K,
    LLM_MAX_TOKENS,
)
from embeddings import EmbeddingService
from llm_mistral import MistralLLM
from vector_db import VectorDB

NO_INFO_MARKER = "NO_INFO_IN_DB"
NO_INFO_TEXT = "\u041d\u0435\u0442 \u0438\u043d\u0444\u043e\u0440\u043c\u0430\u0446\u0438\u0438 \u0432 \u0431\u0430\u0437\u0435"


class RAGPipeline:
    def __init__(self):
        started = time.perf_counter()
        print("[RAG:init] start", flush=True)

        t = time.perf_counter()
        self.embedder = EmbeddingService(EMBEDDING_MODEL, EMBEDDING_DEVICE)
        print(f"[RAG:init] embedder ready in {time.perf_counter()-t:.2f}s", flush=True)

        t = time.perf_counter()
        self.db = VectorDB(QDRANT_HOST, QDRANT_PORT, COLLECTION_NAME)
        print(f"[RAG:init] vector db ready in {time.perf_counter()-t:.2f}s", flush=True)

        t = time.perf_counter()
        self.llm = MistralLLM()
        print(f"[RAG:init] llm ready in {time.perf_counter()-t:.2f}s", flush=True)
        print(f"[RAG:init] total {time.perf_counter()-started:.2f}s", flush=True)

    def _keyword_tokens(self, query: str) -> list[str]:
        tokens = re.findall(r"\w+", query.lower(), flags=re.UNICODE)
        return [token for token in tokens if len(token) >= 3]

    def retrieve(self, query: str, k: int = RAG_TOP_K):
        q_vec = self.embedder.embed_query(query)
        raw = self.db.search(q_vec, limit=max(k * 8, 20))
        query_tokens = self._keyword_tokens(query)
        token_set = set(query_tokens)
        token_count = max(len(token_set), 1)

        ranked = []
        for point in raw:
            text = point.payload.get("text", "")
            if not text:
                continue
            text_lower = text.lower()
            lexical_hits = sum(1 for token in token_set if token in text_lower)
            lexical_ratio = lexical_hits / token_count
            # Soft boost for chunks that cover most query terms.
            coverage_boost = 0.12 if lexical_ratio >= 0.6 else 0.0
            combined_score = float(point.score) + lexical_ratio * 0.18 + coverage_boost
            ranked.append((combined_score, text, lexical_hits))

        ranked.sort(key=lambda item: (item[0], item[2]), reverse=True)

        dedup = []
        seen_fingerprints = set()
        for _, text, _ in ranked:
            # Coarse duplicate filter for near-identical chunks.
            fingerprint = " ".join(text.lower().split())[:240]
            if fingerprint in seen_fingerprints:
                continue
            seen_fingerprints.add(fingerprint)
            dedup.append(text)
            if len(dedup) >= k:
                break
        return dedup

    def _try_extract_definition(self, query: str, docs: list[str]) -> str | None:
        q = query.strip().lower()
        patterns = [r"^что\s+такое\s+(.+?)[\?\.!\s]*$", r"^кто\s+такой\s+(.+?)[\?\.!\s]*$"]
        subject = None
        for pattern in patterns:
            match = re.match(pattern, q, flags=re.UNICODE)
            if match:
                subject = match.group(1).strip()
                break
        if not subject:
            return None

        subject_tokens = [t for t in re.findall(r"\w+", subject, flags=re.UNICODE) if len(t) >= 2]
        if not subject_tokens:
            return None

        best_sentence = None
        best_score = 0
        for doc in docs:
            for sentence in re.split(r"(?<=[\.\!\?])\s+|\n+", doc):
                s = sentence.strip()
                if len(s) < 20:
                    continue
                s_lower = s.lower()
                hits = sum(1 for token in subject_tokens if token in s_lower)
                if hits == 0:
                    continue
                score = hits * 3 + min(len(s), 220) / 220
                if score > best_score:
                    best_score = score
                    best_sentence = s

        return best_sentence if best_score >= 4 else None

    def _best_evidence_snippet(self, query: str, docs: list[str]) -> str | None:
        query_tokens = self._keyword_tokens(query)
        if not query_tokens:
            return None

        best = None
        best_score = -1.0
        for doc in docs:
            for sentence in re.split(r"(?<=[\.\!\?])\s+|\n+", doc):
                s = sentence.strip()
                if len(s) < 20:
                    continue
                s_lower = s.lower()
                hits = sum(1 for token in query_tokens if token in s_lower)
                if hits == 0:
                    continue
                coverage = hits / max(len(set(query_tokens)), 1)
                # Slight preference for concise factual sentences.
                brevity = 1.0 if len(s) <= 240 else 0.7
                score = coverage * 10 + brevity
                if score > best_score:
                    best_score = score
                    best = s

        return best if best_score >= 2.5 else None

    def _truncate_context(self, docs: list[str], max_context_chars: int) -> str:
        joined = []
        total = 0
        for doc in docs:
            remaining = max_context_chars - total
            if remaining <= 0:
                break
            piece = doc[:remaining]
            joined.append(piece)
            total += len(piece) + 2
        return "\n\n".join(joined)

    def generate(
        self,
        query: str,
        rag_top_k: int = RAG_TOP_K,
        max_context_chars: int = RAG_MAX_CONTEXT_CHARS,
        max_tokens: int | None = None,
        temperature: float | None = None,
        top_p: float | None = None,
        top_k: int | None = None,
        repeat_penalty: float | None = None,
    ):
        
        print(f"[RAG] 1. Starting generate for: {query[:50]}...")
        t0 = time.perf_counter()
        
        print(f"[RAG] 2. Retrieving documents...")
        docs = self.retrieve(query, rag_top_k)
        t1 = time.perf_counter()
        print(f"[RAG] 3. Retrieved {len(docs)} docs in {t1-t0:.2f}s")
        
        print(f"[RAG] 4. Truncating context...")
        context = self._truncate_context(docs, max_context_chars)
        t1_5 = time.perf_counter()
        print(f"[RAG] 5. Context truncated to {len(context)} chars in {t1_5-t1:.2f}s")

        print(f"[RAG] 6. Building prompt...")
        prompt = f"""Ты помощник RAG. Отвечай только по CONTEXT.
Если в контексте нет ответа, верни ровно: {NO_INFO_MARKER}
Если ответ есть:
- пиши на языке вопроса;
- дай точный ответ на 2-4 предложения (обычно не короче 20 слов);
- сначала дай определение/главный вывод, затем одну практическую деталь или шаг;
- не добавляй факты, которых нет в контексте.
- не вставляй в ответ служебные слова CONTEXT, QUESTION, ANSWER и строку {NO_INFO_MARKER}.

CONTEXT:
{context}

QUESTION:
{query}

ANSWER:"""
        
        t1_75 = time.perf_counter()
        print(f"[RAG] 7. Prompt built ({len(prompt)} chars) in {t1_75-t1_5:.2f}s")
        
        print(f"[RAG] 8. Calling LLM.generate()...")
        llm_start = time.perf_counter()
        answer = self.llm.generate(
            prompt,
            max_tokens=max_tokens if max_tokens is not None else LLM_MAX_TOKENS,
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
            repeat_penalty=repeat_penalty,
        )
        llm_end = time.perf_counter()
        print(f"[RAG] 9. LLM.generate() took {llm_end-llm_start:.2f}s")
        
        answer = self._normalize_answer(answer)
        if answer == NO_INFO_TEXT and docs:
            evidence = self._best_evidence_snippet(query, docs)
            if evidence:
                print("[RAG] 9.1 NO_INFO fallback -> evidence snippet", flush=True)
                answer = evidence
        t2 = time.perf_counter()
        
        print(f"[RAG] 10. Total time: retrieve={t1-t0:.2f}s generate={t2-t1:.2f}s total={t2-t0:.2f}s")
        
        return {"answer": answer, "contexts": docs}

    @staticmethod
    def _normalize_answer(answer: str) -> str:
        clean = answer.strip()
        if not clean:
            return NO_INFO_TEXT

        # Trim common prompt-leak artifacts.
        for stop_fragment in ("CONTEXT:", "QUESTION:", "Answer:", "ANSWER:"):
            if stop_fragment in clean:
                clean = clean.split(stop_fragment, 1)[0].strip()

        # Remove accidental marker leakage from otherwise valid answers.
        clean = clean.replace(NO_INFO_MARKER, "").strip()
        clean = re.sub(r"\s{2,}", " ", clean)

        if not clean:
            return NO_INFO_TEXT

        marker_only = {
            "",
            NO_INFO_MARKER,
            f'"{NO_INFO_MARKER}"',
            f"'{NO_INFO_MARKER}'",
            f"{NO_INFO_MARKER}.",
            f"{NO_INFO_MARKER}!",
        }
        if clean in marker_only:
            return NO_INFO_TEXT
        return clean
