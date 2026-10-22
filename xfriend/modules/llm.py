"""LLM module: an OpenAI-compatible chat completions client.

Works against any OpenAI-format endpoint: Venice (default), Grok (xAI),
LongCat, or a custom base_url. Provider-specific extras (e.g. Venice's
`venice_parameters`) ride along in `extra_body`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, List, Optional

from openai import OpenAI

from xfriend.config import LLMConfig


@dataclass
class LLMToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class LLMMessage:
    content: Optional[str]
    tool_calls: List[LLMToolCall] = field(default_factory=list)


class LLM:
    """Thin OpenAI-compatible wrapper used by the turn engine and auxiliary
    one-shot calls (compaction summary, facts, frustration audit)."""

    def __init__(self, config: LLMConfig):
        cfg = config.resolved()
        if not cfg.api_key:
            raise ValueError(
                f"no API key for LLM provider {cfg.provider!r}; "
                f"set {cfg.preset.get('env_key', 'the provider env var')} "
                "or llm.api_key in xfriend.yaml"
            )
        if not cfg.base_url:
            raise ValueError(f"no base_url for LLM provider {cfg.provider!r}")
        self.config = cfg
        self._client = OpenAI(api_key=cfg.api_key, base_url=cfg.base_url)

    # -- main call ---------------------------------------------------------

    def complete(
        self,
        messages: List[dict],
        tools: Optional[List[dict]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        frequency_penalty: Optional[float] = None,
        presence_penalty: Optional[float] = None,
    ) -> LLMMessage:
        kwargs: dict[str, Any] = {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature if temperature is None else temperature,
            "max_tokens": self.config.max_tokens if max_tokens is None else max_tokens,
            "frequency_penalty": (
                self.config.frequency_penalty if frequency_penalty is None else frequency_penalty
            ),
            "presence_penalty": (
                self.config.presence_penalty if presence_penalty is None else presence_penalty
            ),
            "stream": False,
        }
        if tools:
            kwargs["tools"] = tools
        if self.config.params:
            kwargs["extra_body"] = self.config.params

        resp = self._client.chat.completions.create(**kwargs)
        choice = resp.choices[0].message

        tool_calls: List[LLMToolCall] = []
        if getattr(choice, "tool_calls", None):
            for tc in choice.tool_calls:
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                tool_calls.append(
                    LLMToolCall(id=tc.id, name=tc.function.name, arguments=args)
                )
        return LLMMessage(content=choice.content, tool_calls=tool_calls)

    # -- auxiliary one-shot calls ------------------------------------------

    def summarize(self, prompt: str) -> Optional[str]:
        """Rolling-summary helper (low temperature, small budget)."""
        msg = self.complete(
            [{"role": "user", "content": prompt}],
            temperature=self.config.summary_temperature,
            max_tokens=self.config.summary_max_tokens,
        )
        return msg.content.strip() if msg.content else None

    def audit(self, prompt: str, max_tokens: int = 120, temperature: float = 0.0) -> str:
        """Deterministic one-shot audit (frustration cleanup, gender, etc.)."""
        msg = self.complete(
            [{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return msg.content or ""

    def extract_facts(self, prompt: str) -> str:
        """Fact extraction (append-only durable memory)."""
        msg = self.complete(
            [{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=400,
        )
        return msg.content or ""