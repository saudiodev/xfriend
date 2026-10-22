"""Tests for xfriend.config: presets, env resolution, yaml loading."""

from __future__ import annotations

import os

import pytest

from xfriend.config import (
    LLMConfig,
    ImageConfig,
    MemoryConfig,
    VoiceConfig,
    default_config_yaml,
    load_config,
)


def test_venice_preset_applied():
    cfg = LLMConfig(provider="venice").resolved()
    assert cfg.base_url == "https://api.venice.ai/api/v1"
    assert cfg.model == "olafangensan-glm-4.7-flash-heretic"
    assert cfg.params["venice_parameters"]["disable_thinking"] is True


def test_custom_model_override():
    cfg = LLMConfig(provider="venice", model="my-model").resolved()
    assert cfg.model == "my-model"


def test_env_api_key_resolution(monkeypatch):
    monkeypatch.setenv("VENICE_INFERENCE_KEY", "sk-test")
    cfg = LLMConfig(provider="venice").resolved()
    assert cfg.api_key == "sk-test"


def test_grok_preset(monkeypatch):
    monkeypatch.setenv("XAI_API_KEY", "sk-xai")
    cfg = LLMConfig(provider="grok").resolved()
    assert cfg.base_url == "https://api.x.ai/v1"
    assert cfg.api_key == "sk-xai"


def test_yaml_roundtrip(tmp_path):
    cfg = default_config_yaml("luna")
    path = tmp_path / "xfriend.yaml"
    path.write_text(cfg, encoding="utf-8")
    loaded = load_config(str(path))
    assert loaded.name == "luna"
    assert loaded.llm.provider == "venice"
    assert loaded.llm.model == "olafangensan-glm-4.7-flash-heretic"
    assert loaded.image.enabled is False
    assert loaded.voice.enabled is False
    assert loaded.memory.keep_messages == 16
    assert loaded.memory.compact_batch == 10


def test_yaml_with_modules(tmp_path):
    yaml = """
name: luna
persona: You are Luna, a night owl.
llm:
  provider: grok
  temperature: 0.9
image:
  enabled: true
  base_image: ./assets/luna.png
  loras:
    - name: dreamshaper
      trigger: ds
      url: https://civitai.com/api/download/models/123
voice:
  enabled: true
  voice_id: whisper
memory:
  keep_messages: 20
  compact_batch: 8
"""
    path = tmp_path / "xfriend.yaml"
    path.write_text(yaml, encoding="utf-8")
    loaded = load_config(str(path))
    assert loaded.persona == "You are Luna, a night owl."
    assert loaded.llm.provider == "grok"
    assert loaded.llm.base_url == "https://api.x.ai/v1"
    assert loaded.llm.temperature == 0.9
    assert loaded.image.enabled is True
    # relative paths resolve against the config file's directory
    assert loaded.image.base_image == str((path.parent / "assets/luna.png").resolve())
    assert loaded.image.loras[0].name == "dreamshaper"
    assert loaded.image.loras[0].trigger == "ds"
    assert loaded.voice.voice_id == "whisper"
    assert loaded.memory.keep_messages == 20
    assert loaded.memory.compact_batch == 8


def test_persona_file(tmp_path):
    persona = tmp_path / "persona.md"
    persona.write_text("You are Maya, patient and playful.", encoding="utf-8")
    yaml = f"name: maya\npersona_file: {persona}\n"
    path = tmp_path / "xfriend.yaml"
    path.write_text(yaml, encoding="utf-8")
    loaded = load_config(str(path))
    assert loaded.persona == "You are Maya, patient and playful."