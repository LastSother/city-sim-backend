import json
import logging
from typing import Dict, List
from fastapi import WebSocket
from .config import WS_MAX_CONNECTIONS_PER_TOPIC

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        self.topics: Dict[str, List[WebSocket]] = {}

    async def connect(self, topic: str, ws: WebSocket) -> bool:
        conns = self.topics.setdefault(topic, [])
        if len(conns) >= WS_MAX_CONNECTIONS_PER_TOPIC:
            await ws.close(code=1013)
            if not conns:
                self.topics.pop(topic, None)
            return False
        await ws.accept()
        conns.append(ws)
        return True

    def disconnect(self, topic: str, ws: WebSocket):
        conns = self.topics.get(topic)
        if conns and ws in conns:
            conns.remove(ws)
        if conns is not None and not conns:
            self.topics.pop(topic, None)

    async def send_personal(self, ws: WebSocket, message: dict):
        await ws.send_text(json.dumps(message, ensure_ascii=False))

    async def broadcast(self, topic: str, message: dict):
        text = json.dumps(message, ensure_ascii=False)
        for ws in list(self.topics.get(topic, [])):
            try:
                await ws.send_text(text)
            except Exception:
                logger.info("Удаляю мёртвое соединение из темы %s", topic)
                self.disconnect(topic, ws)


manager = ConnectionManager()
