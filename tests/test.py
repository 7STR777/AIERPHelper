
import requests
import re
from llama_cpp import Llama

BASE_URL = "http://localhost:8080"
LOGIN_URL = f"{BASE_URL}/login"
CHAT_URL = f"{BASE_URL}/chat"
LOGIN = "user"
PASSWORD = "user123"

LLM_MODEL_PATH = "rag_test/models/qwen2.5-3b-instruct-q4_k_m.gguf"

llm = Llama(
    model_path=LLM_MODEL_PATH,
    n_ctx=1536,
    n_gpu_layers=20,
    n_threads=8,
    verbose=False
)

tests = [

    # тематические вопросы
    {"query": "Что такое ДСЕ?", "topic": True},
    {"query": "Какие бывают типы ДСЕ?", "topic": True},
    {"query": "Что означает тип Изд?", "topic": True},
    {"query": "Как снять ДСЕ с производства?", "topic": True},
    {"query": "Что содержит карточка ДСЕ?", "topic": True},
    {"query": "Для чего нужен модуль Подготовка производства?", "topic": True},
    {"query": "Кто может использовать данный модуль?", "topic": True},
    {"query": "Можно ли удалить ДСЕ если она используется в сборке?", "topic": True},

    # не по теме
    {"query": "Почему трава зеленая?", "topic": False},
    {"query": "Кто такой Наполеон?", "topic": False},
    {"query": "Как сварить рис?", "topic": False},
    {"query": "Какая погода завтра?", "topic": False},
]

def get_token():
    r = requests.post(
        LOGIN_URL,
        json={"login": LOGIN, "password": PASSWORD},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["token"]


def ask_rag(question, token):
    try:
        r = requests.post(
            CHAT_URL,
            json={"query": question},
            headers={"Authorization": f"Bearer {token}"},
            timeout=60,
        )
        return r.json()["content"]

    except Exception as e:
        return f"ERROR: {e}"

def judge_answer(question, answer):
    prompt = f"""
Ты оцениваешь качество ответа базы знаний.

Вопрос:
{question}

Ответ:
{answer}

Оценка:

5 = отличный точный ответ
4 = хороший ответ
3 = частично полезный
2 = слабый
1 = плохой / неверный

Ответь только цифрой.
"""

    out = llm(
        prompt,
        max_tokens=5,
        temperature=0
    )["choices"][0]["text"].strip()

    m = re.search(r"[1-5]", out)
    if m:
        return int(m.group())

    return 0

good_scores = []
fallback_ok = 0
fallback_total = 0

print("=" * 70)
print("START RAG TEST")
print("=" * 70)

token = get_token()

for i, test in enumerate(tests, 1):

    q = test["query"]
    topic = test["topic"]

    print(f"\n{i}. QUESTION: {q}")

    answer = ask_rag(q, token)

    print("ANSWER:")
    print(answer)

    if topic:
        score = judge_answer(q, answer)
        good_scores.append(score)
        print("LLM SCORE:", score, "/5")

    else:
        fallback_total += 1

        expected = "Нет информации в базе"

        if expected.lower() in answer.lower():
            fallback_ok += 1
            print("FALLBACK: PASS")
        else:
            print("FALLBACK: FAIL")


print("\n" + "=" * 70)
print("FINAL REPORT")
print("=" * 70)

if good_scores:
    avg = sum(good_scores) / len(good_scores)
    print("AVG тематических ответов:", round(avg, 2), "/5")

if fallback_total:
    pct = fallback_ok / fallback_total * 100
    print("Нетематические запросы обработаны:", round(pct, 1), "%")

print("=" * 70)