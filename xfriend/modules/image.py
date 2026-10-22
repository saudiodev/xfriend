"""ImageService interface and result type."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional


@dataclass
class ImageResult:
    outputs: List[str] = field(default_factory=list)  # CDN URLs or base64
    prediction_id: Optional[str] = None
    raw: Optional[dict] = None


class ImageService:
    """A provider that turns prompts (+ optional reference images + LoRAs)
    into images. The framework's `send_image` tool talks to this."""

    def generate(
        self,
        prompt: str,
        images: Optional[List[str]] = None,
        loras: Optional[List[dict]] = None,
        size: Optional[int] = None,
        seed: Optional[int] = None,
        output_format: Optional[str] = None,
    ) -> ImageResult:
        raise NotImplementedError