import time
import json
from llama_cpp import Llama
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient

# -------------------------
# DATA
# -------------------------
with open(r"C:\Users\igorm\OneDrive\Desktop\ragproject\rag_test\chunks.json", "r", encoding="utf-8") as f:
    chunks = json.load(f)

# -------------------------
# EMBEDDINGS
# -------------------------
print("🔄 Loading embedding model...")
embed_model = SentenceTransformer("intfloat/e5-base-v2", token = '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')
print("✅ Embedding model loaded")

# -------------------------
# QDRANT
# -------------------------
client = QdrantClient("localhost", port=6333)
collection = "rag_clean"

# -------------------------
# MODELS (LOAD ONCE)
# -------------------------
print("🔄 Loading Qwen...")
qwen = Llama(
    model_path=r"C:\Users\igorm\OneDrive\Desktop\ragproject\rag_test\models\Qwen3.5-9B-Q4_K_S.gguf",
    n_ctx=2048,
    n_threads=8,
    n_gpu_layers=20,
    verbose=False
)
print("✅ Qwen loaded")

print("🔄 Loading GigaChat...")
giga = Llama(
    model_path=r"C:\Users\igorm\OneDrive\Desktop\ragproject\rag_test\models\GigaChat3.1-10B-A1.8B-q4_K_M.gguf",
    n_ctx=2048,
    n_threads=8,
    n_gpu_layers=20,
    verbose=False
)
print("✅ GigaChat loaded")

MODELS = {
    "Qwen": qwen,
    "GigaChat": giga
}

# -------------------------
# CONTEXT
# -------------------------
def get_context(query):
    print(f"🔎 Retrieving context for: {query}")

    q_emb = embed_model.encode([f"query: {query}"], normalize_embeddings=True)

    res = client.query_points(
        collection_name=collection,
        query=q_emb[0].tolist(),
        limit=2
    )

    return "\n".join([p.payload["text"] for p in res.points])

# -------------------------
# PROMPT
# -------------------------
def build_prompt(context, query):
    return f"""
Ты отвечаешь строго по контексту ERP системы.

КОНТЕКСТ:
{context}

ВОПРОС:
{query}

ОТВЕТ:
"""

# -------------------------
# INFERENCE
# -------------------------
def run_model(name, llm, prompt):
    print(f"🚀 Running model: {name}")

    start = time.time()

    out = llm.create_chat_completion(
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=0.0,
        max_tokens=200
    )

    answer = out["choices"][0]["message"]["content"]

    t = time.time() - start

    print(f"✅ Done {name} in {t:.2f}s")

    return answer, t

# -------------------------
# METRICS
# -------------------------
def hallucination(answer, context):
    ctx = set(context.lower().split())
    ans = set(answer.lower().split())
    return len(ans - ctx) / max(len(ans), 1)


def relevance(answer, query):
    q = set(query.lower().split())
    a = set(answer.lower().split())
    return len(q & a) / max(len(q), 1)

# -------------------------
# MAIN
# -------------------------
def run():
    results = []

    queries = [
        "Что такое КТНБД?",
        "Что такое ДСЕ?",
        "Чем отличается ДСЕ от ПКИ?"
    ]

    for i, q in enumerate(queries):
        print("\n" + "=" * 80)
        print(f"📌 QUERY {i+1}/{len(queries)}: {q}")

        context = get_context(q)
        prompt = build_prompt(context, q)

        row = {"query": q}

        for name, llm in MODELS.items():
            print(f"⚙️ Starting model {name}")
            ans, t = run_model(name, llm, prompt)

            row[name] = {
                "answer": ans,
                "latency": t,
                "hallucination": hallucination(ans, context),
                "relevance": relevance(ans, q)
            }

        results.append(row)

    return results

# -------------------------
# REPORT
# -------------------------
def print_report(results):
    print("\n\n📊 FINAL REPORT")

    for r in results:
        print("\n" + "=" * 80)
        print("QUERY:", r["query"])

        for name in MODELS.keys():
            m = r[name]
            print(f"\n{name}")
            print(f"latency: {m['latency']:.2f}s")
            print(f"hallucination: {m['hallucination']:.3f}")
            print(f"relevance: {m['relevance']:.3f}")
            print("answer:", m["answer"][:250])

# -------------------------
# RUN
# -------------------------
if __name__ == "__main__":
    print("🔥 STARTING A/B BENCHMARK\n")
    results = run()
    print_report(results)