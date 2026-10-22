"""Wavespeed Qwen img2img module (image-to-image, LoRA support).

API (from wavespeed.ai llms.txt):
  submit:  POST https://api.wavespeed.ai/api/v3/wavespeed-ai/qwen-image/edit-2511-lora
  poll:    GET  https://api.wavespeed.ai/api/v3/predictions/{id}/result

Local reference images are uploaded as data URIs so the framework's
`base_image` (a local file) can be used without external hosting.
"""

from __future__ import annotations

import base64
import mimetypes
import time
from pathlib import Path
from typing import Any, List, Optional

import requests

from xfriend.modules.image import ImageService, ImageResult


def _to_data_uri(path_or_url: str) -> str:
    """Pass URLs through; convert local files to base64 data URIs."""
    if path_or_url.startswith("data:") or path_or_url.startswith("http"):
        return path_or_url
    p = Path(path_or_url)
    mime = mimetypes.guess_type(p.name)[0] or "image/jpeg"
    b64 = base64.b64encode(p.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{b64}"


def _format_size(size) -> str:
    """Wavespeed expects size as a 'WIDTH*HEIGHT' string, not an integer."""
    if isinstance(size, str):
        return size if "*" in size else f"{size}*{size}"
    if isinstance(size, (tuple, list)) and len(size) == 2:
        return f"{size[0]}*{size[1]}"
    return f"{size}*{size}"  # int -> square


class WavespeedImage(ImageService):
    SUBMIT_TIMEOUT = 60
    POLL_INTERVAL = 2.0
    POLL_TIMEOUT = 300
    MAX_IMAGES = 3
    MAX_LORAS = 3

    def __init__(
        self,
        api_key: str,
        model: str = "wavespeed-ai/qwen-image/edit-2511-lora",
        base_image: Optional[str] = None,
        loras: Optional[List[dict]] = None,
        media_dir: str = "xfriend_data/media",
        size: Any = 1024,
        seed: int = -1,
        output_format: str = "jpeg",
    ):
        if not api_key:
            raise ValueError(
                "no Wavespeed API key; set $WAVESPEED_API_KEY or image.api_key in xfriend.yaml"
            )
        self.api_key = api_key
        self.model = model
        self.endpoint = f"https://api.wavespeed.ai/api/v3/{model}"
        self.result_url = "https://api.wavespeed.ai/api/v3/predictions/{}/result"
        # Fixed reference image + available LoRAs, consumed by send_image tool
        self.base_image: Optional[str] = base_image
        self.loras: List[dict] = loras or []
        self.media_dir = media_dir
        # Defaults applied when the model does not pass them
        self.size: Any = size
        self.seed: int = seed
        self.output_format: str = output_format
        self._session = requests.Session()

    # ------------------------------------------------------------------

    def generate(
        self,
        prompt: str,
        images: Optional[List[str]] = None,
        loras: Optional[List[dict]] = None,
        size: Optional[int] = None,
        seed: Optional[int] = None,
        output_format: Optional[str] = None,
    ) -> ImageResult:
        payload: dict[str, Any] = {"prompt": prompt, "images": []}
        for img in (images or [])[: self.MAX_IMAGES]:
            payload["images"].append(_to_data_uri(img))
        if not payload["images"]:
            raise ValueError(
                "this Wavespeed model requires at least one reference image "
                "(the companion's base_image is used automatically)"
            )
        if loras:
            payload["loras"] = loras[: self.MAX_LORAS]
        if size is not None:
            payload["size"] = _format_size(size)
        elif self.size is not None:
            payload["size"] = _format_size(self.size)
        if seed is not None:
            payload["seed"] = seed
        elif self.seed is not None:
            payload["seed"] = self.seed
        if output_format:
            payload["output_format"] = output_format
        elif self.output_format:
            payload["output_format"] = self.output_format

        submit = self._session.post(
            self.endpoint,
            headers={"Authorization": f"Bearer {self.api_key}"},
            json=payload,
            timeout=self.SUBMIT_TIMEOUT,
        )
        submit.raise_for_status()
        data = submit.json().get("data", {})
        prediction_id = data.get("id")
        if not prediction_id:
            raise RuntimeError(f"wavespeed submit returned no prediction id: {submit.json()}")

        # Poll until completed / failed.
        deadline = time.monotonic() + self.POLL_TIMEOUT
        url = self.result_url.format(prediction_id)
        while time.monotonic() < deadline:
            time.sleep(self.POLL_INTERVAL)
            resp = self._session.get(
                url, headers={"Authorization": f"Bearer {self.api_key}"}, timeout=30
            )
            resp.raise_for_status()
            data = resp.json().get("data", {})
            status = data.get("status")
            if status == "completed":
                return ImageResult(
                    outputs=list(data.get("outputs", [])),
                    prediction_id=prediction_id,
                    raw=data,
                )
            if status in ("failed", "cancelled", "timeout", "deleted"):
                raise RuntimeError(f"wavespeed prediction {status}: {data}")
        raise TimeoutError(f"wavespeed prediction {prediction_id} timed out")