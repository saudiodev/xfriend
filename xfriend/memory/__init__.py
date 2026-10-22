"""Memory layer: the framework persists through a MemoryStore protocol, so it
is fully independent of any product database. JSON files ship by default;
SQLite/CockroachDB/etc. can implement the same protocol later.
"""

from xfriend.memory.base import MemoryStore, SessionState
from xfriend.memory.json_store import JsonFileStore
from xfriend.memory.inmemory import InMemoryStore

__all__ = ["MemoryStore", "SessionState", "JsonFileStore", "InMemoryStore"]


def create_store(kind: str, data_dir: str = "xfriend_data") -> MemoryStore:
    if kind == "json":
        return JsonFileStore(data_dir)
    if kind == "inmemory":
        return InMemoryStore()
    raise ValueError(f"unknown memory store: {kind!r}")