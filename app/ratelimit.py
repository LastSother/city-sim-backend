import time
from collections import deque
from typing import Deque, Dict


class RateLimiter:
    """Скользящее окно: не более limit событий за window секунд на ключ."""

    def __init__(self, limit: int, window: float = 60.0, max_keys: int = 10000):
        self.limit = limit
        self.window = window
        self.max_keys = max_keys
        self.hits: Dict[str, Deque[float]] = {}

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        if len(self.hits) > self.max_keys:
            self.hits = {k: v for k, v in self.hits.items() if v and now - v[-1] < self.window}
        q = self.hits.setdefault(key, deque())
        while q and now - q[0] >= self.window:
            q.popleft()
        if len(q) >= self.limit:
            return False
        q.append(now)
        return True
