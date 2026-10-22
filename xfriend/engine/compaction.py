"""Compaction — the rolling-scene summary mechanism inherited from the
original live voice engine:

- trigger: history exceeds keep_messages + compact_batch
- runs on a background thread (never blocks the reply)
- rolling "SCENE SO FAR" summary with carry-forward rules
- frustration audit deletes assistant turns the user pushed back on
- race guard: verify the history prefix is unchanged before mutating
"""

from __future__ import annotations

import json
import re
import threading
from typing import Optional

from xfriend.engine.prompts import (
    compaction_prompt,
    frustration_prompt,
    transcript_text,
)


def _parse_index_list(text: str) -> list[int]:
    if not text:
        return []
    m = re.search(r"\[[\s\S]*\]", text)
    if not m:
        return []
    try:
        parsed = json.loads(m.group(0))
    except json.JSONDecodeError:
        return []
    return [int(x) for x in parsed if isinstance(x, int) or str(x).isdigit()]


class Compactor:
    """Owns the compaction state machine. All mutation happens under a lock;
    the LLM work happens outside it (background thread)."""

    def __init__(self, llm, name: str, keep_messages: int, compact_batch: int):
        self.llm = llm
        self.name = name
        self.keep = keep_messages
        self.batch = compact_batch
        self.lock = threading.Lock()
        self.compacting = False
        self.summary: Optional[str] = None

    # -- trigger -----------------------------------------------------------

    def maybe_compact(self, history: list[dict]) -> None:
        with self.lock:
            if self.compacting or len(history) <= self.keep + self.batch:
                return
            batch = list(history[: len(history) - self.keep])
            old = self.summary
            # Race guard: snapshot the prefix we are about to summarize; the
            # result is only applied if this prefix is still present.
            prefix = [h.get("content", "") for h in history[: len(batch)]]
            self.compacting = True
        # Run off the hot path so a slow summarizer never delays a reply.
        threading.Thread(
            target=self._summarize, args=(history, batch, old, prefix), daemon=True
        ).start()

    # -- background work ---------------------------------------------------

    def _summarize(
        self,
        history: list[dict],
        batch: list[dict],
        old: Optional[str],
        prefix: list[str],
    ) -> None:
        try:
            # Frustration cleanup first: audit which assistant turns the user
            # pushed back on, and delete them "exactly as if they had never
            # happened".
            try:
                audit = self.llm.audit(frustration_prompt(self.name, transcript_text(batch)))
                doomed = _parse_index_list(audit)
            except Exception:
                doomed = []

            convo = transcript_text(batch)
            summary_text = self.llm.summarize(compaction_prompt(self.name, old, convo))

            if not summary_text:
                return  # empty summary -> leave history intact

            with self.lock:
                # Race guard: only apply if the history prefix is still the
                # batch we summarized (a reset mid-flight discards the result).
                current = [h.get("content", "") for h in history[: len(batch)]]
                if prefix != current:
                    return
                if doomed:
                    # indices are relative to the batch; remove the content
                    # (and any attached media) of doomed turns.
                    doomed_set = set(doomed)
                    kept = []
                    for i, h in enumerate(batch):
                        if i in doomed_set:
                            continue
                        kept.append(h)
                    history[: len(batch)] = kept
                else:
                    history[: len(batch)] = []
                self.summary = summary_text
        finally:
            with self.lock:
                self.compacting = False