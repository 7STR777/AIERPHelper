# DIPLOM — ERP Чат-бот (Angular + RAG Backend)

Единый проект: фронтенд (`ANGULAR`) и бэкенд (`Back/AIERPHelper`) запускаются одной командой через Docker Compose.

## Структура

```
DIPLOM/
├── ANGULAR/                 # Angular 17 — UI чат-бота
├── Back/AIERPHelper/        # Python RAG + ASP.NET API + Qdrant + MSSQL
├── docker-compose.yml       # ← запуск всего стека
└── README.md
```

## Требования

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) с поддержкой Compose v2
- NVIDIA GPU + [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html) (для RAG-воркера с CUDA)
- Файл LLM-модели `*.gguf` (~2 ГБ) в каталоге:

```
Back/AIERPHelper/rag_test/models/
```

## Быстрый запуск.

```powershell
cd C:\Users\IriyaYa\Downloads\DIPLOM
docker compose up -d --build
```

Первый запуск может занять 10–20 минут (образы, зависимости, кеш HuggingFace).

### Индексация документов в Qdrant

После старта контейнеров:

```powershell
docker compose exec rag-api python3 ingest.py
```

### Прогрев RAG-модели

```powershell
curl.exe -X POST http://localhost:8080/rag/warmup
```

## Адреса сервисов

| Сервис | URL | Описание |
|--------|-----|----------|
| **Фронтенд** | http://localhost | Angular UI (nginx) |
| **API** | http://localhost:8080 | ASP.NET шлюз (`/login`, `/chat`) |
| **API через прокси** | http://localhost/api/... | Тот же API из браузера (без CORS) |
| **Swagger** | http://localhost:8080/swagger | Документация API |
| **Qdrant** | http://localhost:6333 | Векторная БД |
| **MSSQL** | localhost:1433 | Хранение неотвеченных вопросов |

## Вход в приложение

| Логин | Пароль |
|-------|--------|
| `user` | `user123` |
| `admin` | `admin123` |

В Docker-сборке mock-режим отключён автоматически (`production: true`, `apiUrl: '/api'`).

## Локальная разработка фронтенда

Бэкенд в Docker, фронтенд через `ng serve`:

```powershell
# Терминал 1 — бэкенд
cd C:\Users\IriyaYa\Downloads\DIPLOM
docker compose up -d mssql qdrant rag-api aspnet-api

# Терминал 2 — фронтенд
cd ANGULAR
npm install
ng serve
```

Открой http://localhost:4200. В `src/environments/environment.ts` указан `apiUrl: 'http://localhost:8080'`.
Для работы с реальным API установи `USE_MOCK = false` в сервисах или используй production-сборку.

## Полезные команды

```powershell
# Статус контейнеров
docker compose ps

# Логи
docker compose logs -f frontend
docker compose logs -f aspnet-api
docker compose logs -f rag-api

# Остановка
docker compose down

# Пересборка только фронта
docker compose up -d --build frontend
```

## Переменные окружения (опционально)

Создай файл `.env` в корне для переопределения GPU-настроек без GPU:

```env
EMBEDDING_DEVICE=cpu
LLM_GPU_LAYERS=0
```

> Без NVIDIA GPU образ `rag-api` может не запуститься — он собран на базе CUDA. Для CPU-only потребуется отдельная сборка Dockerfile.

## Отдельный запуск только бэкенда

Если нужен только RAG-стек без фронтенда:

```powershell
cd Back/AIERPHelper
docker compose up -d --build
```

Подробности — в `Back/AIERPHelper/README.md`.
