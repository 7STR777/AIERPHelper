import itertools
import json
from dataclasses import dataclass

from rag import NO_INFO_TEXT, RAGPipeline


@dataclass
class EvalCase:
    query: str
    expected_keywords: list[str]


CASES = [
    EvalCase(
        query="Что такое постоянная часть спецификации?",
        expected_keywords=["постоян", "част", "спецификац"],
    ),
    EvalCase(
        query="Что показывает символ # в списке исполнений?",
        expected_keywords=["символ", "#", "исполнен"],
    ),
    EvalCase(
        query="Что такое ДСЕ?",
        expected_keywords=["дсе", "детал", "сбороч"],
    ),
    EvalCase(
        query="Как открыть список редакций техпроцесса?",
        expected_keywords=["редакц", "техпроцесс", "спис"],
    ),
    EvalCase(
        query="Как создать новую операцию ТП?",
        expected_keywords=["операц", "тп", "insert"],
    ),
    EvalCase(
        query="Что такое редакция спецификации?",
        expected_keywords=["редакц", "спецификац", "период"],
    ),
]


PARAM_GRID = {
    "rag_top_k": [4, 5, 6],
    "max_context_chars": [2600, 3200],
    "max_tokens": [200, 240],
    "temperature": [0.1, 0.2],
    "top_p": [0.9],
    "top_k": [40],
    "repeat_penalty": [1.1, 1.15],
}


def iter_param_sets():
    keys = list(PARAM_GRID.keys())
    values = [PARAM_GRID[key] for key in keys]
    for combo in itertools.product(*values):
        yield dict(zip(keys, combo))


def score_answer(answer: str, expected_keywords: list[str]) -> float:
    if not answer or answer == NO_INFO_TEXT:
        return -5.0

    lower = answer.lower()
    hits = sum(1 for kw in expected_keywords if kw in lower)
    keyword_score = (hits / max(len(expected_keywords), 1)) * 10.0

    words = len(answer.split())
    length_score = min(words / 18.0, 1.0) * 3.0
    short_penalty = -2.0 if words < 8 else 0.0

    return keyword_score + length_score + short_penalty


def evaluate(pipeline: RAGPipeline, params: dict) -> tuple[float, list[dict]]:
    total = 0.0
    details = []
    for case in CASES:
        result = pipeline.generate(query=case.query, **params)
        answer = result["answer"]
        score = score_answer(answer, case.expected_keywords)
        total += score
        details.append(
            {
                "query": case.query,
                "answer": answer,
                "score": round(score, 3),
            }
        )
    return total / len(CASES), details


def main():
    pipeline = RAGPipeline()
    ranked = []

    for params in iter_param_sets():
        mean_score, details = evaluate(pipeline, params)
        ranked.append(
            {
                "params": params,
                "mean_score": round(mean_score, 3),
                "details": details,
            }
        )
        print(f"[tune] params={params} mean_score={mean_score:.3f}")

    ranked.sort(key=lambda x: x["mean_score"], reverse=True)
    best = ranked[:3]
    print("\n=== TOP 3 ===")
    for i, item in enumerate(best, 1):
        print(f"{i}) score={item['mean_score']} params={item['params']}")

    with open("tune_results.json", "w", encoding="utf-8") as f:
        json.dump(ranked, f, ensure_ascii=False, indent=2)
    print("\nSaved full results to tune_results.json")


if __name__ == "__main__":
    main()
