"""Tool abstraction: an OpenAI-style function schema plus a handler."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class MediaRef:
    type: str  # "image" | "audio"
    path: str
    url: Optional[str] = None
    caption: Optional[str] = None
    duration_secs: Optional[float] = None

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "path": self.path,
            "url": self.url,
            "caption": self.caption,
            "duration_secs": self.duration_secs,
        }


@dataclass
class ToolResult:
    content: str  # what the LLM sees after the tool runs
    media: List[MediaRef] = field(default_factory=list)


Handler = Callable[[Dict[str, Any]], ToolResult]


@dataclass
class Tool:
    name: str
    description: str
    parameters: Dict[str, Any]  # JSON-schema properties + required
    handler: Handler

    def schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": self.parameters.get("properties", {}),
                    "required": self.parameters.get("required", []),
                },
            },
        }