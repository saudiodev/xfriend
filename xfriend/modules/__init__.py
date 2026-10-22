"""Module layer: swappable service interfaces and the default providers.

- LLM       — OpenAI-compatible chat completions (Venice / Grok / LongCat / custom)
- Image     — Wavespeed Qwen img2img with LoRA support
- Voice     — SecretAudio (ElevenLabs-compatible) TTS
"""

from xfriend.modules.llm import LLM, LLMMessage, LLMToolCall
from xfriend.modules.image import ImageService, ImageResult
from xfriend.modules.voice import VoiceService, AudioResult
from xfriend.modules.wavespeed import WavespeedImage
from xfriend.modules.secretaudio import SecretAudioVoice

__all__ = [
    "LLM", "LLMMessage", "LLMToolCall",
    "ImageService", "ImageResult",
    "VoiceService", "AudioResult",
    "WavespeedImage", "SecretAudioVoice",
]