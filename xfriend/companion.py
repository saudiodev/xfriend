"""High-level API: Companion(config).chat("...") -> ChatReply."""

from __future__ import annotations

from xfriend.config import CompanionConfig
from xfriend.engine.turn_engine import ChatReply, TurnEngine


class Companion:
    """A configured companion. Context-manager friendly: `close()` extracts
    durable facts and persists state."""

    def __init__(self, engine: TurnEngine, config: CompanionConfig):
        self.engine = engine
        self.config = config

    # -- conversation ------------------------------------------------------

    def chat(self, message: str) -> ChatReply:
        return self.engine.chat(message)

    def close(self) -> None:
        self.engine.close()

    def reset(self) -> None:
        self.engine.reset()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False

    # -- introspection -----------------------------------------------------

    @property
    def history(self):
        return self.engine.history

    @property
    def summary(self):
        return self.engine.compactor.summary

    @property
    def facts(self):
        return list(self.engine.facts)

    def __repr__(self):
        modules = []
        if self.config.llm:
            modules.append(f"llm={self.config.llm.provider}")
        if self.config.image.enabled:
            modules.append("image=wavespeed")
        if self.config.voice.enabled:
            modules.append(f"voice={self.config.voice.provider}")
        return f"<Companion {self.config.name!r} [{', '.join(modules)}]>"