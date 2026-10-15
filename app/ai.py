import os
import logging
from openai import AsyncOpenAI
from cachetools import TTLCache
from . import config  # noqa: F401 — загружает .env

logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
MODEL = os.environ.get('OPENAI_MODEL', 'gpt-4o-mini')
FALLBACK_REPLY = "(NPC временно молчит — ошибка AI)"

if OPENAI_API_KEY:
    client = AsyncOpenAI(api_key=OPENAI_API_KEY)
else:
    client = None
    logger.warning("OPENAI_API_KEY не задан: ответы NPC будут заглушкой")

cache = TTLCache(maxsize=100, ttl=300)  # Кэш AI-ответов на 5 минут


async def generate_reply(system_prompt: str, history: list, user_message: str):
    """system_prompt формируется только сервером; текст пользователя передаётся отдельным сообщением user."""
    if client is None:
        return FALLBACK_REPLY
    key = (system_prompt, user_message, str(history[-3:]))
    if key in cache:
        return cache[key]
    messages = [{'role': 'system', 'content': system_prompt}]
    if history:
        messages += history[-10:]
    messages.append({'role': 'user', 'content': user_message})
    try:
        logger.debug("Запрос к OpenAI: %d сообщений", len(messages))
        response = await client.chat.completions.create(
            model=MODEL,
            messages=messages,
            max_tokens=200,
            temperature=0.8,
        )
        reply = (response.choices[0].message.content or '').strip()
        cache[key] = reply
        return reply
    except Exception as e:
        logger.error("AI error: %s", type(e).__name__)
        return FALLBACK_REPLY
