"""send_audio tool: the model sends a voice message via the voice module."""

from __future__ import annotations

from xfriend.tools.base import Tool, ToolResult, MediaRef

_AUDIO_DESCRIPTION = (
    "Speak a voice message to the user as a voice note / audio message. "
    "Use this when the user asks you to speak, whisper, sing, or send a voice "
    "message, or when a voice message would be more intimate than text."
)


def _make_handler(voice_module):
    def handler(args: dict) -> ToolResult:
        text = str(args.get("text", "")).strip()
        if not text:
            raise ValueError("send_audio requires text")
        result = voice_module.synthesize(
            text=text,
            voice_id=args.get("voice_id"),
            language_code=args.get("language_code"),
        )
        media = [
            MediaRef(
                type="audio",
                path=result.path,
                duration_secs=result.duration_secs,
                caption=text[:200],
            )
        ]
        summary = (
            f"Voice message sent to the user: {len(text)} characters, "
            f"{result.duration_secs if result.duration_secs is not None else 'unknown'} seconds. "
            f"Local path: {result.path}. "
            f"You should now acknowledge the voice message in your reply."
        )
        return ToolResult(content=summary, media=media)

    return handler


def send_audio_tool(voice_module) -> Tool:
    return Tool(
        name="send_audio",
        description=_AUDIO_DESCRIPTION,
        parameters={
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The exact text to speak aloud as the voice message.",
                },
                "voice_id": {
                    "type": "string",
                    "description": "Optional voice id to use for this message.",
                },
                "language_code": {
                    "type": "string",
                    "description": "Optional ISO 639-1 language code.",
                },
            },
            "required": ["text"],
        },
        handler=_make_handler(voice_module),
    )