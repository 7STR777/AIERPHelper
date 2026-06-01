# RAG проект на Python + ASP.NET + Qdrant

Этот проект реализует RAG-пайплайн для корпоративной информационной системы:
- `aspnet-backend` — публичный API на ASP.NET (JWT, Swagger, `/login`, `/chat`);
- `rag-api` — Python-воркер, выполняет поиск по векторной базе и подставляет контекст в LLM;
- `qdrant` — хранилище векторных эмбеддингов;
- `mssql` — хранилище всех вопросов, на которые модель не смогла ответить;
- `ANGULAR` — фронтенд-приложение проекта, клиентская часть чата.

## Фронтенд (ANGULAR)

Папка `ANGULAR` содержит Angular-приложение, которое работает как веб-интерфейс для чата.

Основные команды запуска фронтенда из папки `ANGULAR`:

```powershell
cd ANGULAR
npm install
npm start
```

По умолчанию приложение доступно на `http://localhost:4200`.

Перед запуском убедитесь, что в `src/environments/environment.ts` указан бэкенд:

```typescript
apiUrl: 'http://localhost:8080',
```

В `ANGULAR/src/app/core/services/chat-api.service.ts` и `ANGULAR/src/app/core/services/auth.service.ts` должен быть отключён мок-сервер (`USE_MOCK = false`).

## Быстрая последовательность действий

1. Конвертируйте PDF в Markdown через модуль `convert_into_md`.
2. Запустите семантическое чанкирование в модуле `ingestion`.
3. Создайте эмбеддинги и загрузите данные в Qdrant командой:
   - `docker compose exec -e RECREATE_COLLECTION=true rag-api python3 ingest.py`
4. Соберите контейнеры:
   - `docker compose up -d --build`
5. Запустите сервисы:
   - `docker compose up`

> Рабочая директория для команд должна быть `Back/`.

## 1. Конвертация PDF → Markdown

Файлы для конвертации находятся в папке `Back/convert_into_md`.

Пример текущего скрипта:
- `Back/convert_into_md/convert_from_pdf_to_md.py`

Он конвертирует PDF в Markdown и сохраняет результат как `.md`.

Запуск:

```powershell
cd Back
python convert_into_md/convert_from_pdf_to_md.py
```

Если в скрипте указан путь к PDF и MD, замените их на нужные файлы.

## 2. Семантическое чанкирование

Модуль `Back/ingestion/semantic_chunker.py` берет сгенерированный Markdown и разбивает его на семантические чанки.

Запуск:

```powershell
cd Back
python ingestion/semantic_chunker.py
```

После выполнения будет создан файл:
- `Back/chunks_output_v2.json`

Этот файл содержит сегменты текста, готовые для дальнейшей обработки и индексации.

## 3. Создание эмбеддингов в Qdrant

После генерации `chunks_output_v2.json` нужно загрузить данные в Qdrant.

Запустите из папки `Back`:

```powershell
docker compose exec -e RECREATE_COLLECTION=true rag-api python3 ingest.py
```

Эта команда:
- пересоздает коллекцию в Qdrant,
- строит эмбеддинги для чанков,
- сохраняет точки в векторную базу.

## 4. Сборка контейнеров

Для полной пересборки сервисов выполните:

```powershell
docker compose up -d --build
```

Это собирает и запускает контейнеры в фоне.

## 5. Запуск сервисов

После сборки запустите сервисы (без пересборки):

```powershell
docker compose up
```

## Порты сервисов

После запуска сервисы доступны на следующих портах:
- `localhost:8080` — ASP.NET API (`aspnet-api`);
- `localhost:6333` — Qdrant (`qdrant`);
- `localhost:1433` — MSSQL (`mssql`);
- `rag-api` слушает `9000` внутри Docker-кластера.
- `localhost:80` — веб-интерфейс 

## Что сохраняется в MSSQL

Все вопросы, на которые модель не смогла дать ответ, сохраняются в MSSQL. Это позволяет анализировать и обрабатывать неотвеченные запросы позже.

Строка подключения к MSSQL указывается в `aspnet-backend/appsettings.json` и в `Back/docker-compose.yml` как `ConnectionStrings__SupportDb`.

## Запуск и проверка

1. Убедитесь, что PDF преобразован в `.md`.
2. Убедитесь, что был выполнен `semantic_chunker.py`.
3. Выполните `docker compose exec -e RECREATE_COLLECTION=true rag-api python3 ingest.py`.
4. Соберите контейнеры: `docker compose up -d --build`.
5. Запустите сервисы: `docker compose up`.
6. Проверьте Swagger:
   - `http://localhost:8080/swagger`
   или
   - `http://localhost:80/chat`

## Основные файлы

- `Back/docker-compose.yml` — конфигурация сервисов `rag-api`, `aspnet-api`, `qdrant`, `mssql`.
- `Back/ingest.py` — загрузка и индексирование текстов в Qdrant.
- `Back/worker_http.py` — HTTP-воркер, отвечающий на запросы `/warmup` и `/ask`.
- `Back/convert_into_md/convert_from_pdf_to_md.py` — конвертация PDF → Markdown.
- `Back/ingestion/semantic_chunker.py` — семантическое чанкирование Markdown.
- `Back/rag.py` — RAG-пайплайн с поиском и ранжированием.
- `Back/aspnet-backend/` — ASP.NET API-шлюз.

---

Если нужно, могу также добавить пример запуска запроса через `curl` или данные по точному формату `chunks_output_v2.json`.

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
 - `https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF` — ссылка на скачивание модели Qwen2.5-3B-Instruct-GGUF

## Тесты

Скрипт `tests/test.py` использует `POST /login` и `POST /chat` с полем `content` в ответе. Перед запуском убедитесь, что подняты `aspnet-api` и `rag-api`.

