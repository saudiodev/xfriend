"""xfriend configuration: dataclasses, provider presets, and the YAML loader.

The orchestrator configurator reads a single `xfriend.yaml` that wires the
three module families (LLM, image, voice) plus memory/compaction tuning.
Secrets are resolved from environment variables when not set in the file.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml

# ---------------------------------------------------------------------------
# Provider presets (all LLMs are OpenAI-compatible chat completions)
# ---------------------------------------------------------------------------

#: name -> preset (base_url, default model, extra body params, env key)
LLM_PRESETS: dict[str, dict[str, Any]] = {
    "venice": {
        "base_url": "https://api.venice.ai/api/v1",
        "model": "olafangensan-glm-4.7-flash-heretic",
        "params": {
            "venice_parameters": {
                "disable_thinking": True,
                "include_venice_system_prompt": False,
            }
        },
        "env_key": "VENICE_INFERENCE_KEY",
    },
    "grok": {
        "base_url": "https://api.x.ai/v1",
        "model": "grok-3",
        "params": {},
        "env_key": "XAI_API_KEY",
    },
    "longcat": {
        "base_url": "https://api.longcat.chat/openai/v1",
        "model": "LongCat-2.5-Preview",
        "params": {},
        "env_key": "LONGCAT_API_KEY",
    },
}

# ---------------------------------------------------------------------------
# Module configs
# ---------------------------------------------------------------------------


@dataclass
class LLMConfig:
    provider: str = "venice"  # venice | grok | longcat | custom
    model: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None  # falls back to the provider's env var
    params: dict[str, Any] = field(default_factory=dict)  # extra body params
    temperature: float = 0.7
    max_tokens: int = 150
    frequency_penalty: float = 0.6
    presence_penalty: float = 0.3
    # Sampling settings for auxiliary one-shot calls (summary, facts, audit)
    summary_max_tokens: int = 140
    summary_temperature: float = 0.3

    def resolved(self) -> "LLMConfig":
        """Fill defaults from the provider preset and the environment."""
        preset = LLM_PRESETS.get(self.provider, {})
        out = LLMConfig(
            provider=self.provider,
            model=self.model or preset.get("model"),
            base_url=self.base_url or preset.get("base_url"),
            api_key=self.api_key,
            params=dict(preset.get("params", {}), **self.params),
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            frequency_penalty=self.frequency_penalty,
            presence_penalty=self.presence_penalty,
            summary_max_tokens=self.summary_max_tokens,
            summary_temperature=self.summary_temperature,
        )
        if out.provider != "custom":
            out.api_key = out.api_key or os.environ.get(preset.get("env_key", ""))
        return out

    @property
    def preset(self) -> dict[str, Any]:
        return LLM_PRESETS.get(self.provider, {})


@dataclass
class LoRAConfig:
    name: str
    trigger: str = ""
    url: Optional[str] = None


@dataclass
class ImageConfig:
    enabled: bool = False
    provider: str = "wavespeed"
    model: str = "wavespeed-ai/qwen-image/edit-2511-lora"
    base_image: Optional[str] = None  # fixed reference image (local path or URL)
    loras: list[LoRAConfig] = field(default_factory=list)
    size: int = 1024
    seed: int = -1
    output_format: str = "jpeg"
    api_key: Optional[str] = None  # falls back to WAVESPEED_API_KEY
    #: the reference image is fixed on purpose — rolling references degrade output
    base_image_fixed: bool = True

    def resolved(self) -> "ImageConfig":
        out = ImageConfig(
            enabled=self.enabled,
            provider=self.provider,
            model=self.model,
            base_image=self.base_image,
            loras=self.loras,
            size=self.size,
            seed=self.seed,
            output_format=self.output_format,
            api_key=self.api_key or os.environ.get("WAVESPEED_API_KEY"),
            base_image_fixed=True,
        )
        return out


@dataclass
class VoiceConfig:
    enabled: bool = False
    provider: str = "secretaudio"
    voice_id: str = "velvet"
    model: str = "secret-v1"
    language_code: str = "en"
    settings: dict[str, Any] = field(
        default_factory=lambda: {"stability": 0.5, "similarity_boost": 0.75, "speed": 1.0}
    )
    output_format: str = "mp3_44100_128"
    api_key: Optional[str] = None  # falls back to SECRETVOICE_API_KEY

    def resolved(self) -> "VoiceConfig":
        return VoiceConfig(
            enabled=self.enabled,
            provider=self.provider,
            voice_id=self.voice_id,
            model=self.model,
            language_code=self.language_code,
            settings=self.settings,
            output_format=self.output_format,
            api_key=self.api_key or os.environ.get("SECRETVOICE_API_KEY"),
        )


@dataclass
class MemoryConfig:
    store: str = "json"  # json | inmemory
    dir: str = "xfriend_data"
    keep_messages: int = 16
    compact_batch: int = 10
    facts_max: int = 40
    resume_history: bool = True  # carry recent verbatim turns across sessions
    token_trigger: Optional[int] = None  # optional token-based compaction trigger


@dataclass
class CompanionConfig:
    name: str = "xfriend"
    persona: str = ""
    persona_file: Optional[str] = None
    llm: LLMConfig = field(default_factory=LLMConfig)
    image: ImageConfig = field(default_factory=ImageConfig)
    voice: VoiceConfig = field(default_factory=VoiceConfig)
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    config_path: Optional[str] = None

    def resolved(self) -> "CompanionConfig":
        """Deep-resolve: presets, env keys, and inline/file persona."""
        persona = self.persona
        if not persona and self.persona_file:
            try:
                persona = Path(self.persona_file).read_text(encoding="utf-8")
            except OSError:
                persona = ""  # tolerate a missing persona file (doctor mode)
        if not persona:
            persona = f"You are {self.name}, a warm and attentive companion."
        out = CompanionConfig(
            name=self.name,
            persona=persona,
            persona_file=self.persona_file,
            llm=self.llm.resolved(),
            image=self.image.resolved(),
            voice=self.voice.resolved(),
            memory=self.memory,
            config_path=self.config_path,
        )
        return out


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def _dict_to_dataclass(dc_type: type, data: dict[str, Any]) -> Any:
    """Best-effort mapping of a raw yaml dict onto a dataclass, tolerating
    missing keys and unknown provider-specific fields."""
    if data is None:
        return dc_type()
    known = {f.name for f in dc_type.__dataclass_fields__.values()}
    kwargs: dict[str, Any] = {}
    for key, value in data.items():
        if key not in known:
            continue
        field_def = dc_type.__dataclass_fields__[key]
        if key == "loras" and isinstance(value, list):
            kwargs[key] = [_dict_to_dataclass(LoRAConfig, v) for v in value]
        elif field_def.type == dict and isinstance(value, dict):
            kwargs[key] = dict(value)
        else:
            kwargs[key] = value
    return dc_type(**kwargs)


def load_config(path: str | os.PathLike) -> CompanionConfig:
    """Load and resolve an xfriend.yaml config file.

    Relative paths (persona_file, image.base_image, memory.dir) resolve
    against the config file's directory, so a companion can live anywhere.
    """
    path = Path(path).resolve()
    base = path.parent
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    persona_file = raw.get("persona_file")
    if persona_file:
        persona_file = str((base / persona_file).resolve())

    image_raw = _dict_to_dataclass(ImageConfig, raw.get("image") or {})
    if image_raw.base_image and not image_raw.base_image.startswith(("http://", "https://", "data:")):
        image_raw.base_image = str((base / image_raw.base_image).resolve())

    memory_raw = _dict_to_dataclass(MemoryConfig, raw.get("memory") or {})
    if memory_raw.dir:
        memory_raw.dir = str((base / memory_raw.dir).resolve())

    cfg = CompanionConfig(
        name=raw.get("name", "xfriend"),
        persona=raw.get("persona", ""),
        persona_file=persona_file,
        llm=_dict_to_dataclass(LLMConfig, raw.get("llm") or {}),
        image=image_raw,
        voice=_dict_to_dataclass(VoiceConfig, raw.get("voice") or {}),
        memory=memory_raw,
        config_path=str(path),
    )
    return cfg.resolved()


def default_config_yaml(name: str) -> str:
    """Template emitted by `xfriend init`."""
    return f"""\
# {name} — xfriend companion configuration
name: {name}
persona_file: persona.md

llm:
  provider: venice        # venice | grok | longcat | custom
  # model: olafangensan-glm-4.7-flash-heretic   # override preset default
  # base_url: https://api.venice.ai/api/v1
  temperature: 0.7
  max_tokens: 150
  frequency_penalty: 0.6
  presence_penalty: 0.3
  # API key: env $VENICE_INFERENCE_KEY (or $XAI_API_KEY / $LONGCAT_API_KEY)

image:
  enabled: false          # set true to let the model send images
  provider: wavespeed
  model: wavespeed-ai/qwen-image/edit-2511-lora
  base_image: ./assets/base.png   # fixed reference image Qwen edits
  size: 1024
  seed: -1
  output_format: jpeg
  loras:                  # exposed to the model as +18/Civitai style tools
    - name: example-lora
      trigger: trigger_word
      url: https://civitai.com/api/download/models/XXXX
  # API key: env $WAVESPEED_API_KEY

voice:
  enabled: false          # set true to let the model send audio
  provider: secretaudio
  voice_id: velvet        # 13 female / 16 male premade voices
  model: secret-v1
  language_code: en
  settings: {{ stability: 0.5, similarity_boost: 0.75, speed: 1.0 }}
  # API key: env $SECRETVOICE_API_KEY

memory:
  store: json             # json | inmemory
  dir: xfriend_data
  keep_messages: 16       # verbatim turns kept in context
  compact_batch: 10       # compaction fires at keep_messages + compact_batch
  facts_max: 40
  resume_history: true
"""