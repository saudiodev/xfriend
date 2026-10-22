"""Tests for compaction: trigger threshold, summary application, race guard.

Compaction counts MESSAGES (each chat turn appends 2). Threshold =
keep_messages + compact_batch. We use keep=10/batch=2 (threshold 12) and feed
turns so only ONE deterministic compaction fires.
"""

from __future__ import annotations

import time

from xfriend.engine.turn_engine import TurnEngine
from xfriend.memory import InMemoryStore
from tests.doubles import FauxLLM, make_config, say


class _SummLLM(FauxLLM):
    """FauxLLM with controllable summarizer output."""

    def __init__(self, summary="A rolling summary of the scene so far.", audit="[]", delay=0.0):
        super().__init__(script=[])
        self._summary = summary
        self._audit = audit
        self._delay = delay
        self._n = 0
        self.summarize_calls = 0

    def complete(self, messages, tools=None, **kwargs):
        # main-loop calls (one per chat turn) reply with a unique say
        self._n += 1
        return say(f"reply-{self._n}")

    def summarize(self, prompt):
        self.summarize_calls += 1
        if self._delay:
            time.sleep(self._delay)
        return self._summary

    def audit(self, prompt, max_tokens=120, temperature=0.0):
        return self._audit


def _wait_compaction(engine, timeout=5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        with engine.compactor.lock:
            if not engine.compactor.compacting and engine.compactor.summary is not None:
                return
        time.sleep(0.02)
    raise AssertionError("compaction did not complete")


def _engine(faux):
    # threshold = 12; 7 chats (14 msgs) triggers exactly once, batch = 4
    return TurnEngine(
        make_config(keep=10, batch=2), faux, [], InMemoryStore(), "luna"
    )


def test_no_trigger_below_threshold():
    faux = _SummLLM()
    eng = _engine(faux)
    for i in range(6):  # 12 messages == threshold, not above it
        eng.chat(f"message {i}")
    time.sleep(0.3)
    assert eng.compactor.summary is None
    assert faux.summarize_calls == 0


def test_trigger_and_summary_applied():
    faux = _SummLLM(summary="the scene is now cozy")
    eng = _engine(faux)
    for i in range(7):  # 14 messages > 12 -> trigger
        eng.chat(f"message {i}")
    _wait_compaction(eng)
    assert eng.compactor.summary == "the scene is now cozy"
    assert len(eng.history) == 10  # trimmed back to keep_messages


def test_race_guard_discards_stale_summary():
    """If the history is reset mid-flight, the summary must not be applied."""
    faux = _SummLLM(summary="stale summary", delay=0.3)
    eng = _engine(faux)
    for i in range(7):
        eng.chat(f"message {i}")
    # compaction thread is sleeping inside summarize(); reset mid-flight
    eng.reset()
    time.sleep(0.6)
    assert eng.compactor.summary is None


def test_frustrated_turns_removed():
    faux = _SummLLM(audit="[1]")  # assistant turn at batch index 1 is doomed
    eng = _engine(faux)
    for i in range(6):  # 12 msgs; index 1 is stable (no compaction yet)
        eng.chat(f"message {i}")
    doomed_content = eng.history[1]["content"]  # assistant reply to turn 0 ("reply-1")
    eng.chat("message 6")  # 14 msgs -> single trigger, batch includes index 1
    _wait_compaction(eng)
    remaining = [h["content"] for h in eng.history]
    assert doomed_content not in remaining
    assert len(eng.history) < 14