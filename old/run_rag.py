import time
from pathlib import Path
from vector_db import QdrantClient
from sentence_transformers import SentenceTransformer
from llama_cpp import Llama
from FlagEmbedding import FlagReranker

MODEL_PATH = r"D:\ragproject\rag_test\models\mistral-7b-instruct-v0.3-q4_k_m.gguf"

print("=" * 70)
print("🚀 RAG PRO SYSTEM 'ОЛИМП'")
print("=" * 70)

# Проверка модели
if not Path(MODEL_PATH).exists():
    print("❌ Модель не найдена")
    exit(1)

# Qdrant
qdrant = QdrantClient(host="localhost", port=6333)
collection = "production_preparation_chunks_full"

# Эмбеддер
embedder = SentenceTransformer('all-MiniLM-L6-v2')

# Reranker
print("🔄 Загрузка reranker...")
reranker = FlagReranker('BAAI/bge-reranker-base')

# LLM
print("🔄 Загрузка LLM...")
llm = Llama(
    model_path=MODEL_PATH,
    n_ctx=4096,
    n_gpu_layers=-1,
    n_threads=6,
    verbose=False
)

print("✅ Готово!\n")

# ---------------------------
# 🧠 Intent classifier
# ---------------------------
def classify_query(q: str):
    q = q.lower()
    if "что такое" in q:
        return "definition"
    if "как" in q:
        return "function"
    if "расчет" in q or "себестоимость" in q:
        return "calculation"
    return "general"


# ---------------------------
# 🔍 SEARCH (улучшенный)
# ---------------------------
def search(query, limit=10):
    intent = classify_query(query)

    # 🔥 embedding с questions бустом
    query_vec = embedder.encode(query).tolist()

    results = qdrant.query_points(
        collection_name=collection,
        query=query_vec,
        limit=limit,
        with_payload=True
    ).points

    # 👉 фильтр по intent (soft)
    if intent != "general":
        filtered = []
        for r in results:
            if r.payload.get("intent") == intent:
                filtered.append(r)
        if len(filtered) >= 3:
            results = filtered

    return results


# ---------------------------
# 🔥 RERANK
# ---------------------------
def rerank(query, docs):
    pairs = []

    for d in docs:
        text = d.payload.get("text", "")
        questions = " ".join(d.payload.get("questions", []))
        pairs.append([query, text + " " + questions])

    scores = reranker.compute_score(pairs)

    ranked = sorted(zip(docs, scores), key=lambda x: x[1], reverse=True)

    return [r[0] for r in ranked]


# ---------------------------
# 🧱 CONTEXT BUILDER
# ---------------------------
def build_context(docs, max_chars=3000):
    context = ""

    for i, d in enumerate(docs):
        text = d.payload.get("text", "")
        doc_id = d.payload.get("id", "unknown")

        block = f"[DOC {i+1} | {doc_id}]\n{text}\n\n"

        if len(context) + len(block) > max_chars:
            break

        context += block

    return context


# ---------------------------
# 🤖 ASK
# ---------------------------
def ask(question):
    print(f"\n🤔 {question}")
    print("-" * 70)

    # 1. search
    results = search(question)

    if not results:
        print("❌ Нет результатов")
        return

    # 2. rerank
    results = rerank(question, results)

    # 3. context
    context = build_context(results[:5])

    # 4. prompt
    prompt = f"""<s>[INST] Ты эксперт по ERP системе «Олимп».

Используй только информацию из контекста.

Контекст:
{context}

Вопрос: {question}

Правила:
- отвечай кратко и по делу
- ссылайся на DOC ID
- не выдумывай

Ответ: [/INST]"""

    # 5. LLM
    response = llm(
        prompt,
        max_tokens=400,
        temperature=0.2,
        top_p=0.9,
        stop=["</s>"]
    )

    answer = response['choices'][0]['text'].strip()

    print(f"\n💡 ОТВЕТ:\n{answer}")

    print("\n📚 ИСТОЧНИКИ:")
    for i, r in enumerate(results[:5], 1):
        print(f"{i}. {r.payload.get('id')} | score={r.score:.3f}")


# ---------------------------
# 💬 CHAT
# ---------------------------
def chat():
    print("\n🤖 RAG PRO CHAT")
    print("Введите /exit для выхода\n")

    while True:
        q = input("💬 Вы: ").strip()

        if q == "/exit":
            break

        ask(q)


if __name__ == "__main__":
    chat()