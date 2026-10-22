"""JSON-file MemoryStore: one state file per companion, atomic writes."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from xfriend.memory.base import MemoryStore, SessionState


class JsonFileStore(MemoryStore):
    def __init__(self, data_dir: str = "xfriend_data"):
        self.data_dir = Path(data_dir)

    def _path(self, companion_id: str) -> Path:
        return self.data_dir / companion_id / "state.json"

    def load(self, companion_id: str) -> SessionState:
        path = self._path(companion_id)
        if not path.exists():
            return SessionState()
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return SessionState()
        return SessionState(
            summary=raw.get("summary"),
            facts=list(raw.get("facts", [])),
            history=list(raw.get("history", [])),
            media=list(raw.get("media", [])),
        )

    def save(self, companion_id: str, state: SessionState) -> None:
        path = self._path(companion_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "summary": state.summary,
            "facts": state.facts,
            "history": state.history,
            "media": state.media,
        }
        fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, ensure_ascii=False, indent=2)
            os.replace(tmp, path)
        except BaseException:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise

    def reset(self, companion_id: str) -> None:
        path = self._path(companion_id)
        if path.exists():
            path.unlink()