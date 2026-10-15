import os
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


def _int(name, default):
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        logger.warning("Некорректное значение %s, используется %s", name, default)
        return default


# Токен администратора (мэра) для POST /issue_law. Если не задан, эндпоинт отключён.
ADMIN_TOKEN = os.environ.get('ADMIN_TOKEN', '')
# Токен для подключения к WebSocket (?token=...). Если не задан, проверка отключена.
WS_TOKEN = os.environ.get('WS_TOKEN', '')
# Разрешённые источники CORS через запятую.
CORS_ORIGINS = [o.strip() for o in os.environ.get(
    'CORS_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173'
).split(',') if o.strip()]
# Лимит запросов к ИИ на одного клиента (IP) в минуту.
AI_RATE_LIMIT_PER_MIN = _int('AI_RATE_LIMIT_PER_MIN', 10)
# Ограничения WebSocket.
WS_MAX_CONNECTIONS_PER_TOPIC = _int('WS_MAX_CONNECTIONS_PER_TOPIC', 100)
WS_MAX_MESSAGE_CHARS = _int('WS_MAX_MESSAGE_CHARS', 500)
# Имя игрока в выборах мэра.
PLAYER_NAME = 'Игрок'
