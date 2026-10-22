"""Shared test doubles."""

from __future__ import annotations

from typing import Optional

from xfriend.modules.llm import LLMMessage, LLMToolCall
from xfriend.modules.image import ImageResult


class FauxLLM:
    """Scripted LLM: complete() pops from a queue of results."""

    def __init__(self, script=None):
        self.script = list(script or [])
        self.calls = []  # (messages, tools) recorded per complete() call

    def complete(self, messages, tools=None, **kwargs):
        self.calls.append((messages, tools))
        if self.script:
            return self.script.pop(0)
        return LLMMessage(content='{"say": "default reply"}')

    # auxiliary one-shots
    def summarize(self, prompt):
        return "A rolling summary of the scene so far."

    def audit(self, prompt, max_tokens=120, temperature=0.0):
        return "[]"

    def extract_facts(self, prompt):
        return '["user likes cats", "user is a developer"]'


def say(text: str) -> LLMMessage:
    import json as _json

    return LLMMessage(content=f'{{"say": {_json.dumps(text)}}}')


def tool_call(name: str, args: dict, call_id: str = "call_1") -> LLMMessage:
    return LLMMessage(
        content=None,
        tool_calls=[LLMToolCall(id=call_id, name=name, arguments=args)],
    )


class FauxImage:
    """Image module double: records prompts, returns a data-URI output so the
    framework's downloader never touches the network."""

    base_image = "base.png"
    loras = [{"name": "dreamshaper", "trigger": "ds", "url": "https://civitai/1"}]
    media_dir = "xfriend_data/media"

    def __init__(self):
        self.requests = []

    def generate(self, prompt, images=None, loras=None, **kwargs):
        self.requests.append(
            {"prompt": prompt, "images": images, "loras": loras, **kwargs}
        )
        png = __import__("base64").b64encode(b"\x89PNG\r\n\x1a\nfake").decode()
        return ImageResult(outputs=[f"data:image/png;base64,{png}"])


class FauxVoice:
    """Voice module double."""

    def synthesize(self, text, voice_id=None, language_code=None, **kwargs):
        from xfriend.modules.voice import AudioResult

        return AudioResult(path=f"xfriend_data/media/{voice_id or 'v'}.mp3", duration_secs=2.5)


def make_config(**overrides):
    from xfriend.config import (
        CompanionConfig,
        LLMConfig,
        ImageConfig,
        LoRAConfig,
        MemoryConfig,
        VoiceConfig,
    )

    llm = LLMConfig(provider="venice", api_key="sk-fake")
    image = ImageConfig(
        enabled=overrides.get("image", False),
        base_image="base.png",
        loras=[LoRAConfig(name="dreamshaper", trigger="ds", url="https://civitai/1")]
        if overrides.get("image", False)
        else [],
    )
    voice = VoiceConfig(enabled=overrides.get("voice", False))
    memory = MemoryConfig(
        store="inmemory",
        keep_messages=overrides.get("keep", 4),
        compact_batch=overrides.get("batch", 2),
        resume_history=False,
    )
    return CompanionConfig(
        name=overrides.get("name", "luna"),
        persona=overrides.get("persona", "You are Luna, a night owl. Speak in short lines."),
        llm=llm,
        image=image,
        voice=voice,
        memory=memory,
    )