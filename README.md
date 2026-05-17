# RAG проект на Python + ASP.NET + Qdrant

Этот проект реализует RAG-пайплайн для корпоративной информационной системы:
- `aspnet-backend` — публичный API на ASP.NET (JWT, Swagger, эндпоинты `/login` и `/chat`);
- `rag-api` — Python-воркер, выполняет поиск по векторной базе и подставляет контекст в LLM;
- `qdrant` — хранилище векторных эмбеддингов;
- `mssql` — хранилище неответов для дальнейшей обработки.

## Структура проекта

- `docker-compose.yml` — основная конфигурация для запуска всех сервисов;
- `Dockerfile` — образ для Python-воркера;
- `aspnet-backend/` — API-шлюз на .NET 8.0 (`/login`, `/chat`, Swagger);
- `ingest.py` — загрузка и индексирование текстов из `chunks.json` в Qdrant;
- `worker_http.py` — HTTP-воркер для запросов `/warmup` и `/ask`;
- `rag.py` — RAG-пайплайн с гибридным поиском (BM25 + векторный поиск + ранжирование);
- `vector_db.py` — клиент для Qdrant;
- `embeddings.py` — сервис эмбеддингов;
- `llm_qwen.py` — генерация ответов через локальную модель GGUF;
- `chunks.json` — источник текстовых фрагментов для индексации.

## Как это работает

1. Клиент получает JWT через `POST /login` (логин и пароль).
2. Клиент отправляет вопрос в `POST /chat` с заголовком `Authorization: Bearer <token>`.
3. ASP.NET пересылает запрос в Python-воркер по адресу `http://rag-api:9000/ask`.
4. Python-воркер сравнивает вопрос с документами:
   - BM25-поиск по текстам;
   - векторный поиск в Qdrant;
   - дополнительное ранжирование результатов.
5. Сформированный контекст передаётся в LLM, который генерирует ответ.
6. ASP.NET возвращает клиенту JSON с полями `messageID`, `content`, `timestamp`.
7. Если релевантной информации нет, в `content` — сообщение для техподдержки; запрос может быть сохранён в MSSQL.

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

### ASP.NET API (публичный шлюз)

Документация в Swagger UI: **http://localhost:8080/swagger**

| Метод | Путь | Авторизация | Описание |
|-------|------|-------------|----------|
| `GET` | `/` | нет | Статус сервиса |
| `GET` | `/health` | нет | Проверка связи с Python-воркером |
| `POST` | `/login` | нет | Выдача JWT по логину и паролю |
| `POST` | `/chat` | JWT (Bearer) | Запрос к RAG-движку |
| `POST` | `/rag/warmup` | нет | Прогрев воркера и загрузка модели |

#### Авторизация (JWT)

Демо-пользователи (для разработки):

| Логин | Пароль | Роль |
|-------|--------|------|
| `user` | `user123` | `user` |
| `admin` | `admin123` | `admin` |

Обе роли имеют доступ к `POST /chat`. Параметры JWT задаются в `aspnet-backend/appsettings.json` (секция `Jwt`: ключ, issuer, audience, время жизни токена).

**1. Получить токен** — `POST /login`:

```json
{
  "login": "user",
  "password": "user123"
}
```

Ответ:

```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**2. Задать вопрос** — `POST /chat` с заголовком `Authorization: Bearer <token>`:

```json
{
  "query": "Что такое ДСЕ?"
}
```

Ответ:

```json
{
  "messageID": "a1b2c3d4e5f6...",
  "content": "ДСЕ — деталь или сборочная единица...",
  "timestamp": "2026-05-15T12:00:00.0000000Z"
}
```

- `messageID` — уникальный идентификатор ответа (GUID без дефисов);
- `content` — текст ответа или сообщение «обратитесь в техподдержку», если в базе нет информации;
- `timestamp` — время ответа в UTC.

Альтернатива: передать `query` в query-string, например `POST /chat?query=Что%20такое%20ДСЕ?` (тело может быть пустым).

#### Примеры с curl (PowerShell)

Прогрев воркера:

```powershell
curl.exe -X POST http://localhost:8080/rag/warmup
```

Вход и запрос в чат:

```powershell
# Токен
$login = curl.exe -s -X POST http://localhost:8080/login `
  -H "Content-Type: application/json" `
  -d "{\"login\":\"user\",\"password\":\"user123\"}"
$token = ($login | ConvertFrom-Json).token

# Вопрос
curl.exe -X POST http://localhost:8080/chat `
  -H "Content-Type: application/json" `
  -H "Authorization: Bearer $token" `
  -d "{\"query\":\"Что такое ДСЕ?\"}"
```

#### Swagger и Postman

1. Откройте **http://localhost:8080/swagger**.
2. Выполните **POST /login**, скопируйте `token`.
3. Нажмите **Authorize**, введите `Bearer <token>` (или только токен — в зависимости от версии UI).
4. В **POST /chat** в теле запроса укажите поле `query` и выполните запрос.

В Postman: отдельный запрос на `/login`, затем на `/chat` с типом авторизации **Bearer Token**.

### Python worker API (внутренний)

- `GET /` — сервис доступен;
- `GET /health` — статус воркера;
- `POST /warmup` — запуск и прогрев RAG-пайплайна;
- `POST /ask` — запрос к генерации (вызывается из ASP.NET, не требует JWT клиента).

Формат ответа воркера (`answer`, `contexts`) преобразуется шлюзом в `messageID` / `content` / `timestamp` для внешних клиентов.

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

Если воркер не находит ответ, ASP.NET возвращает в `content` сообщение для техподдержки и при настроенной строке подключения `SupportDb` сохраняет запрос в таблицу `RagSupportRequests` в MSSQL. Это позволяет собирать вопросы для анализа и дальнейшего обучения.

Строка подключения задаётся в `aspnet-backend/appsettings.json` → `ConnectionStrings:SupportDb` или через переменные окружения в `docker-compose.yml`.

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

## Тесты

Скрипт `tests/test.py` использует `POST /login` и `POST /chat` с полем `content` в ответе. Перед запуском убедитесь, что подняты `aspnet-api` и `rag-api`.

---

При необходимости README можно дополнить примерами подготовки `chunks.json` и настройкой production-секретов JWT (не использовать демо-ключ из `appsettings.json` в проде).