"""Prompt building: persona/system prompt, compaction, facts, frustration audit.

All prompts are direct descendants of the original live voice-companion
engine, adapted from live voice to text chat with media support.
"""

from __future__ import annotations

from typing import Optional

FACT_HEADER = (
    "THINGS YOU REMEMBER ABOUT THE USER (from earlier conversations; never "
    "deny or forget these):"
)


def system_prompt(
    persona: str,
    name: str,
    tools_enabled: bool = True,
    lora_hints: Optional[str] = None,
) -> str:
    """The byte-stable persona prompt. Keep it identical across turns so
    prompt caching works. Includes the strict JSON reply contract so the
    reply is easy to parse and never scripts the user's side."""
    lines = [
        persona.strip(),
        "",
        "RULES:",
        "- You are the companion speaking directly to the user. Never write the user's side of the conversation, never narrate stage directions, and never speak for the user.",
        "- Reply with a single JSON object, exactly this shape: {\"say\": \"your reply\"}. Put everything you say inside the \"say\" string.",
        "- Keep replies short and natural, as spoken conversation. Vary your phrasing; do not repeat yourself.",
        "- Stay in character, in the language of the persona.",
        "- Carry forward anything the user asks you to remember, plus names, numbers and promises.",
    ]
    if tools_enabled:
        lines += [
            "",
            "TOOLS:",
            "- send_image: generate or edit an image and send it to the user. Use it when the user asks for something visual.",
            "- send_audio: speak a voice message to the user as a voice note.",
            "- You may call a tool instead of replying with text when it fits the moment. After a tool result, continue with your normal JSON reply.",
        ]
    if lora_hints:
        lines += ["", "AVAILABLE IMAGE STYLES (LoRAs):", lora_hints.strip()]
    return "\n".join(lines)


def compaction_prompt(name: str, old: Optional[str], convo: str) -> str:
    """Rolling summary prompt — the compaction mechanism's core, ported from
    the live voice engine with media awareness."""
    return (
        f"You maintain a rolling summary of an ongoing conversation with a "
        f"companion named {name}. Keep it factual and concise (3-5 sentences), "
        f"focused on what has happened and where the scene is now, so the next "
        f"reply stays consistent.\n"
        f"IMPORTANT: always carry forward anything the user asked the companion "
        f"to remember, plus names, numbers, promises and specific words, even "
        f"if they seem trivial. Losing those is what breaks the illusion of a "
        f"partner who remembers them.\n"
        f"Also carry forward the current visual identity of the companion and "
        f"any notable images or voice messages that were exchanged.\n"
        f"Write a fresh summary. Do NOT repeat the previous summary text "
        f"verbatim: fold it in, then update it with what happened since.\n\n"
        f"Previous summary: {old or '(none)'}\n\n"
        f"New exchange:\n{convo}\n\n"
        "Updated summary:"
    )


def facts_prompt(transcript: str) -> str:
    return (
        "Extract durable, useful facts about the user from this conversation "
        "transcript. Return a JSON array of strings, written in English, "
        "first-person facts about the user (e.g. \"user is 28 and works as a "
        "designer\"). Skip trivial or repeated content. Do not invent anything. "
        "Return at most 20 facts.\n\nTranscript:\n" + transcript
    )


def frustration_prompt(name: str, convo: str) -> str:
    """Audit that flags assistant turns the user pushed back on, so they can
    be deleted 'as if they had never happened' (live engine behavior)."""
    return (
        f"Here is a transcript of a conversation with a companion named {name}. "
        f"Each line is prefixed with its index (0-based). Identify assistant "
        f"turns that the user clearly pushed back on: the user corrected them, "
        f"spoke as the companion, flipped genders, or explicitly rejected what "
        f"the companion said or did. Return a JSON array of the indices of those "
        f"assistant turns. Return [] if none. Only include indices of assistant "
        f"turns (odd indices in this format).\n\nTranscript:\n{convo}"
    )


def transcript_text(history: list[dict]) -> str:
    """Render history (with media markers) for summarizers/fact extractors."""
    lines = []
    for i, h in enumerate(history):
        role = h.get("role", "?")
        content = h.get("content", "")
        media = h.get("media") or []
        for m in media:
            mtype = m.get("type", "media")
            marker = f" [sent {mtype}: {m.get('caption') or m.get('path') or m.get('url') or 'file'}]"
            content += marker
        lines.append(f"{i}: {role}: {content}")
    return "\n".join(lines)


def media_marker(media: list[dict]) -> str:
    parts = []
    for m in media:
        mtype = m.get("type", "media")
        if mtype == "image":
            parts.append(f"[sent image: {m.get('caption') or m.get('path') or m.get('url') or 'file'}]")
        elif mtype == "audio":
            parts.append(f"[sent voice message: {m.get('caption') or m.get('path') or 'file'}]")
        else:
            parts.append(f"[sent {mtype}]")
    return " " + " ".join(parts)