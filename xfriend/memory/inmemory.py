"""In-memory MemoryStore (ephemeral, useful for tests and demos)."""

from __future__ import annotations

from xfriend.memory.base import MemoryStore, SessionState


class InMemoryStore(MemoryStore):
    def __init__(self):
        self._data: dict[str, SessionState] = {}

    def load(self, companion_id: str) -> SessionState:
        return self._data.get(companion_id, SessionState())

    def save(self, companion_id: str, state: SessionState) -> None:
        self._data[companion_id] = state

    def reset(self, companion_id: str) -> None:
        self._data.pop(companion_id, None)