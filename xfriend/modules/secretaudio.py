"""SecretAudio TTS module (ElevenLabs-compatible, drop-in).

API (from secretvoice.dev llms-full.txt):
  POST https://api.secretvoice.dev/v1/text-to-speech/{voice_id}?output_format=mp3_44100_128
  headers: xi-api-key / X-API-Key / Authorization: Bearer
  body:    {text, model_id, language_code, voice_settings}
  response: audio file; X-Duration header = billed audio-seconds.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import requests

from xfriend.modules.voice import VoiceService, AudioResult


class SecretAudioVoice(VoiceService):
    BASE_URL = "https://api.secretvoice.dev"

    def __init__(
        self,
        api_key: str,
        voice_id: str = "velvet",
        model: str = "secret-v1",
        language_code: str = "en",
        settings: Optional[dict[str, Any]] = None,
        output_format: str = "mp3_44100_128",
        media_dir: str = "xfriend_data/media",
    ):
        if not api_key:
            raise ValueError(
                "no SecretVoice API key; set $SECRETVOICE_API_KEY or voice.api_key in xfriend.yaml"
            )
        self.api_key = api_key
        self.voice_id = voice_id
        self.model = model
        self.language_code = language_code
        self.settings = settings or {}
        self.output_format = output_format
        self.media_dir = Path(media_dir)
        self._session = requests.Session()

    # ------------------------------------------------------------------

    def synthesize(
        self,
        text: str,
        voice_id: Optional[str] = None,
        model: Optional[str] = None,
        language_code: Optional[str] = None,
        settings: Optional[dict[str, Any]] = None,
        output_format: Optional[str] = None,
    ) -> AudioResult:
        voice = voice_id or self.voice_id
        url = f"{self.BASE_URL}/v1/text-to-speech/{voice}"
        params = {"output_format": output_format or self.output_format}
        body: dict[str, Any] = {
            "text": text,
            "model_id": model or self.model,
            "language_code": language_code or self.language_code,
            "voice_settings": {**self.settings, **(settings or {})},
        }
        resp = self._session.post(
            url,
            params=params,
            headers={"xi-api-key": self.api_key},
            json=body,
            timeout=120,
        )
        if resp.status_code != 200:
            raise RuntimeError(
                f"secretaudio {resp.status_code}: {resp.text[:300]}"
            )

        self.media_dir.mkdir(parents=True, exist_ok=True)
        # derive a stable-ish filename: timestamp + hash of the text
        import hashlib

        digest = hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]
        ext = "mp3" if "mp3" in (output_format or self.output_format) else "wav"
        path = self.media_dir / f"{voice}_{digest}.{ext}"
        path.write_bytes(resp.content)

        duration = None
        if "X-Duration" in resp.headers:
            try:
                duration = float(resp.headers["X-Duration"])
            except (TypeError, ValueError):
                duration = None

        return AudioResult(
            path=str(path),
            duration_secs=duration,
            voice_id=voice,
            request_id=resp.headers.get("X-Request-Id"),
        )