# КАИ — Чат-бот ERP ГСТ АУРА (Angular 17)

## Быстрый старт

### 1. Запуск фронтенда (Angular)
```powershell
cd gst-kai-chatbot
npm install
ng serve
# → http://localhost:4200
```

Войти можно с тестовыми данными: `user` / `user123`

---

### 2. Запуск бэкенда через Docker

#### Шаг 1 — Установить Docker Desktop
Скачай: https://www.docker.com/products/docker-desktop/
После установки **перезагрузи компьютер**.

#### Шаг 2 — Скачать репозиторий бэкенда
```powershell
cd C:\Users\IriyaYa\Downloads\DIPLOM
git clone -b new_features https://github.com/7STR777/AIERPHelper.git
cd AIERPHelper
```

#### Шаг 3 — Положить модель
Получи у бэкендера файл модели (`*.gguf`, ~2 ГБ) и положи его в папку:
```
AIERPHelper\rag_test\models\
```

#### Шаг 4 — Запустить
```powershell
docker compose up -d --build
```
Первый запуск: 10–20 минут (скачиваются образы, загружается модель).

#### Шаг 5 — Проверить
```powershell
curl.exe http://localhost:8080/health
```
Должно ответить что-то вроде `{"status":"ok"}`.

#### Шаг 6 — Подключить фронт к бэку
Открой `src/environments/environment.ts` и убедись что:
```typescript
apiUrl: 'http://localhost:8080',
```
Затем открой `src/app/core/services/chat-api.service.ts` и смени:
```typescript
const USE_MOCK = false;  // ← было true
```
То же самое в `src/app/core/services/auth.service.ts`:
```typescript
const USE_MOCK = false;  // ← было true
```

---

## Структура проекта

```
src/app/
├── core/
│   ├── models/chat.models.ts          ← типы данных
│   ├── services/
│   │   ├── auth.service.ts            ← JWT авторизация
│   │   ├── chat-api.service.ts        ← запросы к /login и /chat
│   │   └── chat-state.service.ts      ← состояние чата (Signals)
│   ├── interceptors/error.interceptor.ts  ← авто-добавление Bearer токена
│   └── guards/auth.guard.ts           ← редирект на /login если не авторизован
├── shared/components/
│   ├── header/                        ← шапка с логотипом и выходом
│   ├── footer/                        ← подвал
│   └── sidebar/                       ← боковая панель с историей диалогов
└── features/
    ├── auth/components/login/          ← страница входа
    └── chat/components/
        ├── chat-window/               ← главная страница чата
        ├── message-bubble/            ← пузырь сообщения + кнопки 👍 👎
        ├── message-input/             ← поле ввода
        ├── typing-indicator/          ← анимация "КАИ печатает..."
        └── quick-actions/             ← кнопки быстрых вопросов
```

## API бэкенда (после подключения Docker)

| Метод | URL | Авторизация | Описание |
|-------|-----|-------------|----------|
| POST | `/login` | нет | Получить JWT токен |
| POST | `/chat` | Bearer JWT | Задать вопрос |
| GET | `/health` | нет | Проверка связи |

**Запрос /login:**
```json
{ "login": "user", "password": "user123" }
```

**Запрос /chat:**
```json
{ "query": "Что такое ДСЕ?" }
```

**Ответ /chat:**
```json
{
  "messageID": "a1b2c3...",
  "content": "ДСЕ — деталь или сборочная единица...",
  "timestamp": "2026-05-15T12:00:00Z"
}
```
