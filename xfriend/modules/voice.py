"""VoiceService interface and result type (outbound TTS only)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class AudioResult:
    path: str  # local file path of the rendered audio
    duration_secs: Optional[float] = None
    voice_id: str = ""
    request_id: Optional[str] = None


class VoiceService:
    """A TTS provider. The framework's `send_audio` tool talks to this."""

    def synthesize(
        self,
        text: str,
        voice_id: Optional[str] = None,
        model: Optional[str] = None,
        language_code: Optional[str] = None,
        settings: Optional[dict[str, Any]] = None,
        output_format: Optional[str] = None,
    ) -> AudioResult:
        raise NotImplementedError