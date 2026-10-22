"""MemoryStore protocol — the only thing the framework requires from storage."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional


@dataclass
class SessionState:
    """Serializable state for one companion conversation."""

    summary: Optional[str] = None
    facts: List[str] = field(default_factory=list)
    history: List[dict] = field(default_factory=list)  # role/content/media dicts
    media: List[dict] = field(default_factory=list)  # all media refs ever sent


class MemoryStore:
    """Minimal persistence contract. Implementations must be safe to call
    from the compaction thread as well as the turn loop."""

    def load(self, companion_id: str) -> SessionState:
        raise NotImplementedError

    def save(self, companion_id: str, state: SessionState) -> None:
        raise NotImplementedError

    def reset(self, companion_id: str) -> None:
        raise NotImplementedError