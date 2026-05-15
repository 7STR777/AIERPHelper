# RAG проект на Python + ASP.NET + Qdrant

Этот проект реализует RAG-пайплайн для корпоративной информационной системы:
- `aspnet-backend` — публичный API на ASP.NET, принимает запросы от клиента;
- `rag-api` — Python-воркер, выполняет поиск по векторной базе и подставляет контекст в LLM;
- `qdrant` — хранилище векторных эмбеддингов;
- `mssql` — хранилище неответов для дальнейшей обработки.

## Структура проекта

- `docker-compose.yml` — основная конфигурация для запуска всех сервисов;
- `Dockerfile` — образ для Python-воркера;
- `aspnet-backend/` — API на .NET 8.0;
- `ingest.py` — загрузка и индексирование текстов из `chunks.json` в Qdrant;
- `worker_http.py` — HTTP-воркер для запросов `/warmup` и `/ask`;
- `rag.py` — RAG-пайплайн с гибридным поиском (BM25 + векторный поиск + ранжирование);
- `vector_db.py` — клиент для Qdrant;
- `embeddings.py` — сервис эмбеддингов;
- `llm_qwen.py` — генерация ответов через локальную модель GGUF;
- `chunks.json` — источник текстовых фрагментов для индексации.

## Как это работает

1. Клиент отправляет запрос в `aspnet-api`.
2. ASP.NET пересылает запрос в Python-воркер по адресу `http://rag-api:9000`.
3. Python-воркер сравнивает вопрос с документами:
   - BM25-поиск по текстам;
   - векторный поиск в Qdrant;
   - дополнительное ранжирование результатов.
4. Сформированный контекст передаётся в LLM, который генерирует ответ.
5. Если релевантной информации нет, возвращается `Нет информации в базе`.

## Быстрый запуск

```powershell
docker compose up -d --build
```

После старта сервисы будут доступны на портах:
- `localhost:8080` — ASP.NET API;
- `localhost:6333` — Qdrant;
- `localhost:1433` — MSSQL.

## Запуск без пересборки (dev loop)

```powershell
docker compose up -d --force-recreate rag-api aspnet-api
```

Особенности:
- `rag-api` монтирует текущую директорию в контейнер;
- `aspnet-api` запускает проект из `./aspnet-backend`;
- кеш HuggingFace сохраняется в `./hf_cache`.

## Индексирование данных

Перед запуском поиска нужно загрузить тексты в Qdrant:

```powershell
docker compose exec rag-api python3 ingest.py
```

В `ingest.py` читается `chunks.json`, строятся эмбеддинги и сохраняются точки с полем `text`, `summary`, `keywords`, `questions`, `entities`.

## API

### ASP.NET API

- `GET /health` — проверка работоспособности;
- `POST /rag/warmup` — прогрев воркера и загрузка модели;
- `POST /rag/ask` — запрос к RAG-движку.

Пример запроса:

```json
{
  "query": "Что такое ДСЕ?"
}
```

Пример с `curl.exe`:

```powershell
curl.exe -X POST http://localhost:8080/rag/warmup
curl.exe -X POST http://localhost:8080/rag/ask -H "Content-Type: application/json" -d "{\"query\":\"Что такое ДСЕ?\"}"
```

### Python worker API

- `GET /` — сервис доступен;
- `GET /health` — статус воркера;
- `POST /warmup` — запуск и прогрев RAG-пайплайна;
- `POST /ask` или `/rag/ask` — запрос к генерации.

## Переменные окружения

Настройки читаются из `config.py` и могут переопределяться через env:

- `QDRANT_HOST`, `QDRANT_PORT`, `COLLECTION_NAME`
- `EMBEDDING_MODEL`, `EMBEDDING_DEVICE`
- `LLM_MODEL_PATH`, `LLM_GPU_LAYERS`, `LLM_N_CTX`, `LLM_MAX_TOKENS`
- `LLM_TEMPERATURE`, `LLM_TOP_P`, `LLM_TOP_K`, `LLM_REPEAT_PENALTY`
- `RAG_TOP_K`, `RAG_MAX_CONTEXT_CHARS`
- `WORKER_HOST`, `WORKER_PORT`

## Локальная модель

По умолчанию модель ищется по пути:
- `/models/qwen2.5-3b-instruct-q4_k_m.gguf`

В контейнере `rag-api` локальная модель монтируется из `./rag_test/models`.
Если имя отличается, система автоматически выбирает первый `.gguf` в каталоге `/models`.

## Хранение «неотвеченных» вопросов

Если воркер не находит ответ, ASP.NET записывает запрос в базу `RagSupportRequests`.
Это позволяет собирать вопросы для анализа и дальнейшего обучения.

## Тюнинг и параметры

Проверенные значения по умолчанию:
- `LLM_N_CTX = 1536`
- `LLM_MAX_TOKENS = 200`
- `LLM_TEMPERATURE = 0.1`
- `LLM_REPEAT_PENALTY = 1.15`
- `RAG_TOP_K = 4`
- `RAG_MAX_CONTEXT_CHARS = 2600`

Запуск тюнинга параметров:

```powershell
docker compose exec rag-api python3 tune_params.py
```

Результаты сохраняются в `tune_results.json`.

## Полезные файлы

- `chunks.json` — исходные фрагменты для индексации;
- `hf_cache/` — кеш эмбеддингов HuggingFace;
- `qdrant_storage/` — постоянное хранилище Qdrant;
- `rag_test/models/` — локальный каталог моделей GGUF.

---

Если нужно, можно расширить README примерами `docker compose` для Windows и инструкциями по подготовке `chunks.json`.