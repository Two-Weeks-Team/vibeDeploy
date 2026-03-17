from collections import deque


class BuildQueue:
    def __init__(self) -> None:
        self._queue: deque[str] = deque()
        self._active: str | None = None

    def enqueue(self, card_id: str) -> None:
        if card_id not in self._queue:
            self._queue.append(card_id)

    def dequeue(self) -> str | None:
        if self._active is not None or not self._queue:
            return None
        self._active = self._queue.popleft()
        return self._active

    def is_building(self) -> bool:
        return self._active is not None

    def mark_complete(self, card_id: str) -> None:
        if self._active == card_id:
            self._active = None
