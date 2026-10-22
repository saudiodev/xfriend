"""Tool layer: schema + dispatch for the model's functions (extensible)."""

from xfriend.tools.base import Tool, ToolResult, MediaRef
from xfriend.tools.send_image import send_image_tool
from xfriend.tools.send_audio import send_audio_tool

__all__ = ["Tool", "ToolResult", "MediaRef", "send_image_tool", "send_audio_tool"]


def build_tools(image_module=None, voice_module=None) -> list[Tool]:
    """Build the tool set from the enabled modules. Each tool is registered
    only if its backing module is present, so the model only sees what it
    can actually do."""
    tools: list[Tool] = []
    if image_module is not None:
        tools.append(send_image_tool(image_module))
    if voice_module is not None:
        tools.append(send_audio_tool(voice_module))
    return tools