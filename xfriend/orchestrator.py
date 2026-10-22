"""Orchestrator: turns a CompanionConfig into a working Companion.

Wires the module families (LLM, image, voice), builds the tool set from the
enabled modules, derives LoRA hints for the persona, and constructs the
memory store + turn engine.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from xfriend.companion import Companion
from xfriend.config import CompanionConfig, load_config
from xfriend.engine.turn_engine import TurnEngine
from xfriend.memory import create_store
from xfriend.modules.llm import LLM
from xfriend.modules.secretaudio import SecretAudioVoice
from xfriend.modules.wavespeed import WavespeedImage
from xfriend.tools import build_tools


def _lora_hints(image_cfg) -> Optional[str]:
    if not image_cfg.enabled or not image_cfg.loras:
        return None
    lines = []
    for lora in image_cfg.loras:
        trigger = f" (trigger: {lora.trigger})" if lora.trigger else ""
        lines.append(f"- {lora.name}{trigger}")
    return "\n".join(lines)


def build_companion(
    config: CompanionConfig, companion_id: Optional[str] = None
) -> Companion:
    """Wire modules into a Companion.

    `companion_id` overrides the memory namespace (defaults to `config.name`),
    which lets a single deployment run many isolated sessions — e.g. one
    companion per Telegram chat or per product user.
    """
    config = config.resolved()
    if companion_id is None:
        companion_id = config.name

    llm = LLM(config.llm)

    image_module = None
    if config.image.enabled:
        base_image = config.image.base_image
        if base_image and not base_image.startswith(("http://", "https://", "data:")):
            p = Path(base_image)
            if not p.exists():
                raise ValueError(
                    f"image.base_image not found: {base_image} "
                    "(give a local path, URL, or data URI)"
                )
        image_module = WavespeedImage(
            api_key=config.image.api_key or "",
            model=config.image.model,
            base_image=config.image.base_image,
            loras=[
                {"name": l.name, "trigger": l.trigger, "url": l.url}
                for l in config.image.loras
                if l.name
            ],
            media_dir=str(Path(config.memory.dir) / "media"),
            size=config.image.size,
            seed=config.image.seed,
            output_format=config.image.output_format,
        )

    voice_module = None
    if config.voice.enabled:
        voice_module = SecretAudioVoice(
            api_key=config.voice.api_key or "",
            voice_id=config.voice.voice_id,
            model=config.voice.model,
            language_code=config.voice.language_code,
            settings=config.voice.settings,
            output_format=config.voice.output_format,
            media_dir=str(Path(config.memory.dir) / "media"),
        )

    tools = build_tools(image_module, voice_module)
    store = create_store(config.memory.store, config.memory.dir)
    engine = TurnEngine(
        config=config,
        llm=llm,
        tools=tools,
        store=store,
        companion_id=companion_id,
        lora_hints=_lora_hints(config.image),
    )
    return Companion(engine=engine, config=config)


def build_from_file(path: str) -> Companion:
    return build_companion(load_config(path))