# City Project Backend

FastAPI-бэкенд проекта «Городской симулятор»: логика NPC, чат через WebSocket, отношения, погода, выборы. Фронтенд — репозиторий [`LastSother/city-sim-frontend`](https://github.com/LastSother/city-sim-frontend).

## Стек
- Python, FastAPI, Uvicorn
- SQLAlchemy (SQLite по умолчанию)
- OpenAI API (ответы NPC), httpx, cachetools

## Запуск локально
```bash
pip install -r requirements.txt
uvicorn app.server:app --reload
```

## Переменные окружения
- `OPENAI_API_KEY` — ключ OpenAI
- `OPENAI_MODEL` — модель (по умолчанию `gpt-4o-mini`)
- `SQLITE_URL` — строка подключения к БД (по умолчанию локальный SQLite-файл)
- `ADMIN_TOKEN` — секрет мэра; `POST /issue_law` требует заголовок `X-Admin-Token: <ADMIN_TOKEN>` (без переменной эндпоинт отключён, 503)
- `WS_TOKEN` — если задан, WebSocket принимает подключения только с `?token=<WS_TOKEN>`. Значение попадает во фронтенд, поэтому это защита от случайных клиентов, а не секрет
- `CORS_ORIGINS` — разрешённые источники через запятую (по умолчанию `http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173`)
- `AI_RATE_LIMIT_PER_MIN` — лимит запросов к ИИ на IP в минуту (по умолчанию 10)
- `WS_MAX_CONNECTIONS_PER_TOPIC`, `WS_MAX_MESSAGE_CHARS` — ограничения WebSocket (100 и 500)

Пример — в `.env.example` (файл `.env` подхватывается автоматически).

## API
- `GET /map`, `/weather` (`sunny` | `rainy` | `stormy`), `/news`, `/chat_history/{npc_id}`, `/mayor` (`{"mayor": ..., "is_player": bool}`)
- `POST /issue_law` — `{"law": "..."}` + заголовок `X-Admin-Token`
- WebSocket `/ws/news`, `/ws/map_update`, `/ws/state_update` (только чтение), `/ws/npc_<id>` (чат: `{"action": "message"|"command", "text": "..."}`)
- Игрок участвует в выборах мэра под именем `Игрок`; событие выборов содержит поля `winner` и `is_player`.
