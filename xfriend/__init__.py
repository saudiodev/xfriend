"""X/Friend — modular AI companion framework for AI girlfriends & boyfriends.

Text conversations with compression: swappable LLM (Venice/Grok/LongCat),
image generation/editing (Wavespeed Qwen + LoRAs) and voice messages
(SecretVoice), with turn management and rolling-scene context compaction.
Independent of any product database.

Quickstart:
    from xfriend.orchestrator import build_from_file
    companion = build_from_file("xfriend.yaml")
    reply = companion.chat("hi there")
"""

__version__ = "0.1.0"

from xfriend.config import CompanionConfig, load_config
from xfriend.companion import Companion
from xfriend.engine.turn_engine import ChatReply
from xfriend.memory import MemoryStore, SessionState

__all__ = [
    "__version__",
    "Companion",
    "CompanionConfig",
    "ChatReply",
    "MemoryStore",
    "SessionState",
    "load_config",
]