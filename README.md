# City Project Backend

FastAPI-бэкенд проекта «Городской симулятор»: логика NPC, чат через WebSocket, отношения, погода, выборы. Фронтенд — репозиторий `LastSother/frontend`.

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
