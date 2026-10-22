"""send_image tool: the model generates/edits an image via the image module.

The companion's fixed `base_image` is used as the reference when the model
does not supply its own images. Available LoRA names are listed in the
system prompt so the model can trigger +18 / Civitai styles by name.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Optional

import requests

from xfriend.tools.base import Tool, ToolResult, MediaRef

_IMAGE_DESCRIPTION = (
    "Generate or edit an image and send it to the user. "
    "Use this when the user asks for a picture, an edit of the companion's "
    "look, a visual for the scene, or anything visual."
)


def _download(url: str, dest_dir: Path, tag: str) -> str:
    dest_dir.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]

    if url.startswith("data:"):
        # data URI (e.g. enable_base64_output): decode in place, no network
        import base64
        import mimetypes

        header, _, b64 = url.partition(",")
        mime = header[5:].split(";")[0] if ";" in header else "image/jpeg"
        ext = mimetypes.guess_extension(mime) or ".img"
        dest = dest_dir / f"{tag}_{digest}{ext}"
        dest.write_bytes(base64.b64decode(b64))
        return str(dest)

    ext = Path(url.split("?")[0]).suffix or ".img"
    dest = dest_dir / f"{tag}_{digest}{ext}"
    if not dest.exists():
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        dest.write_bytes(resp.content)
    return str(dest)


def _make_handler(image_module, base_image: Optional[str], loras: list[dict], media_dir: str):
    def handler(args: dict) -> ToolResult:
        prompt = str(args.get("prompt", "")).strip()
        if not prompt:
            raise ValueError("send_image requires a prompt")

        images = [str(x) for x in args.get("images", []) if x]
        if not images and base_image:
            images = [base_image]

        requested = [str(x) for x in args.get("loras", []) if x]
        lora_objs: list[dict] = []
        if requested:
            by_name = {l["name"]: l for l in loras}
            for name in requested:
                l = by_name.get(name)
                if l:
                    lora_objs.append(l)

        result = image_module.generate(
            prompt=prompt,
            images=images,
            loras=lora_objs or None,
            size=int(args["size"]) if args.get("size") else None,
            seed=int(args["seed"]) if args.get("seed") is not None else None,
            output_format=args.get("output_format"),
        )

        media: list[MediaRef] = []
        for url in result.outputs:
            path = _download(url, Path(media_dir), "image")
            media.append(
                MediaRef(type="image", path=path, url=url, caption=prompt[:200])
            )

        if not media:
            raise RuntimeError("send_image returned no outputs")
        summary = (
            f"Image sent to the user: {len(media)} image(s). "
            f"Prompt used: {prompt!r}. "
            f"Local paths: {[m.path for m in media]}. "
            f"You should now acknowledge the image in your reply."
        )
        return ToolResult(content=summary, media=media)

    return handler


def send_image_tool(image_module) -> Tool:
    config = image_module  # the module carries its own config where available
    base_image = getattr(image_module, "base_image", None)
    loras = getattr(image_module, "loras", []) or []
    media_dir = getattr(image_module, "media_dir", "xfriend_data/media") or "xfriend_data/media"

    lora_names = [l["name"] for l in loras]
    extra_desc = ""
    if lora_names:
        extra_desc = (
            " Available LoRAs (use the exact name in 'loras'): "
            + ", ".join(f"'{n}'" for n in lora_names)
            + "."
        )
    if base_image:
        extra_desc += " If the user asks for an edit of the companion's look, the fixed reference image is used automatically."

    return Tool(
        name="send_image",
        description=_IMAGE_DESCRIPTION + extra_desc,
        parameters={
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "The positive prompt describing the image to generate or edit.",
                },
                "images": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional reference image URLs (max 3). Leave empty to use the companion's reference image.",
                },
                "loras": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional LoRA names to apply (max 3)."
                    + (" Available: " + ", ".join(lora_names) + "." if lora_names else ""),
                },
                "size": {"type": "integer", "description": "Image size in pixels (256-1536)."},
                "seed": {"type": "integer", "description": "Random seed; -1 for random."},
            },
            "required": ["prompt"],
        },
        handler=_make_handler(image_module, base_image, loras, media_dir),
    )