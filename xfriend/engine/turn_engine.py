"""TurnEngine: the text conversation loop.

Each turn: user message in -> build context (persona + facts + SCENE SO FAR +
recent verbatim) -> LLM with tools -> execute any tool calls and loop -> append
assistant reply -> persist -> maybe_compact (background).

Media (images/audio) live in history entries as refs; the LLM context only
carries their text markers, and compaction summarizes them like text.
"""

from __future__ import annotations

import json
import re
import threading
import time
from dataclasses import dataclass, field
from typing import List, Optional

from xfriend.engine.compaction import Compactor
from xfriend.engine.prompts import (
    FACT_HEADER,
    media_marker,
    system_prompt,
)
from xfriend.memory.base import MemoryStore, SessionState
from xfriend.tools.base import MediaRef, Tool


@dataclass
class ChatReply:
    text: str
    media: List[MediaRef] = field(default_factory=list)
    tool_results: List[dict] = field(default_factory=list)


class TurnEngine:
    MAX_TOOL_ROUNDS = 4

    def __init__(
        self,
        config,
        llm,
        tools: List[Tool],
        store: MemoryStore,
        companion_id: str,
        lora_hints: Optional[str] = None,
    ):
        self.config = config
        self.llm = llm
        self.tools = {t.name: t for t in tools}
        self.store = store
        self.companion_id = companion_id
        self.lora_hints = lora_hints

        state = store.load(companion_id)
        self.history: List[dict] = []
        if config.memory.resume_history:
            self.history = list(state.history[-config.memory.keep_messages :])
        self.facts: List[str] = list(state.facts)
        self.media_log: List[dict] = list(state.media)

        self.compactor = Compactor(
            llm, config.name, config.memory.keep_messages, config.memory.compact_batch
        )
        self._lock = threading.Lock()

    # -- public API --------------------------------------------------------

    def chat(self, user_message: str) -> ChatReply:
        user_message = user_message.strip()
        if not user_message:
            raise ValueError("empty user message")

        self.history.append({"role": "user", "content": user_message, "media": []})

        messages = self._build_messages()
        pending_media: List[MediaRef] = []
        tool_results: List[dict] = []

        for _ in range(self.MAX_TOOL_ROUNDS):
            reply = self.llm.complete(
                messages,
                tools=[t.schema() for t in self.tools.values()] if self.tools else None,
            )
            if reply.tool_calls:
                # The model called tools: record the assistant call and run them.
                messages.append(
                    {
                        "role": "assistant",
                        "content": reply.content or "",
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.name,
                                    "arguments": json.dumps(tc.arguments),
                                },
                            }
                            for tc in reply.tool_calls
                        ],
                    }
                )
                for tc in reply.tool_calls:
                    result = self._run_tool(tc.name, tc.arguments)
                    tool_results.append(
                        {"name": tc.name, "args": tc.arguments, "result": result.content}
                    )
                    pending_media.extend(result.media)
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": result.content,
                        }
                    )
                continue
            break

        text = self._parse_say(reply.content) if reply.content else ""

        assistant_entry = {"role": "assistant", "content": text, "media": []}
        if pending_media:
            assistant_entry["media"] = [m.to_dict() for m in pending_media]
            for m in pending_media:
                self.media_log.append(m.to_dict())
        self.history.append(assistant_entry)

        self._persist()
        self.compactor.maybe_compact(self.history)
        return ChatReply(text=text, media=pending_media, tool_results=tool_results)

    def close(self) -> None:
        """Flush state and extract durable facts from the conversation."""
        from xfriend.engine.facts import extract_facts

        self.facts = extract_facts(
            self.llm, self.history, self.facts, self.config.memory.facts_max
        )
        self._persist()

    def reset(self) -> None:
        with self._lock:
            self.history.clear()
        with self.compactor.lock:
            self.compactor.summary = None
        self.store.reset(self.companion_id)

    # -- context -----------------------------------------------------------

    def _build_messages(self) -> List[dict]:
        keep = self.config.memory.keep_messages
        msgs: List[dict] = [
            {
                "role": "system",
                "content": system_prompt(
                    self.config.persona,
                    self.config.name,
                    tools_enabled=bool(self.tools),
                    lora_hints=self.lora_hints,
                ),
            }
        ]
        if self.facts:
            msgs.append({"role": "system", "content": FACT_HEADER + " " + "; ".join(self.facts)})
        if self.compactor.summary:
            msgs.append({"role": "system", "content": "SCENE SO FAR: " + self.compactor.summary})
        for h in self.history[-keep:]:
            content = h.get("content", "")
            media = h.get("media") or []
            if media:
                content += media_marker(media)
            msgs.append({"role": h.get("role", "user"), "content": content})
        return msgs

    # -- tools -------------------------------------------------------------

    def _run_tool(self, name: str, arguments: dict):
        tool = self.tools.get(name)
        if tool is None:
            return _tool_result(f"Unknown tool {name!r}; available: {', '.join(self.tools)}")
        try:
            return tool.handler(arguments)
        except Exception as exc:  # surface the error back to the model
            return _tool_result(f"Tool {name} failed: {exc}")

    # -- parsing -----------------------------------------------------------

    @staticmethod
    def _parse_say(content: str) -> str:
        """Tolerantly extract {"say": "..."} from an LLM reply."""
        content = (content or "").strip()
        if not content:
            return ""
        m = re.search(r"\{[\s\S]*\}", content)
        if m:
            try:
                obj = json.loads(m.group(0))
                if isinstance(obj, dict) and obj.get("say"):
                    return str(obj["say"]).strip()
            except json.JSONDecodeError:
                pass
        # fallback: strip markdown fences / tool noise and return raw text
        cleaned = re.sub(r"^```(json)?\s*|\s*```$", "", content).strip()
        return cleaned

    # -- persistence -------------------------------------------------------

    def _persist(self) -> None:
        with self._lock:
            state = SessionState(
                summary=self.compactor.summary,
                facts=self.facts,
                history=list(self.history),
                media=list(self.media_log),
            )
        self.store.save(self.companion_id, state)


def _tool_result(content: str):
    from xfriend.tools.base import ToolResult

    return ToolResult(content=content)