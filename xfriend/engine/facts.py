"""Facts: append-only durable memory about the user, extracted from the
transcript (ported from the live engine's extract_facts)."""

from __future__ import annotations

import json
import re

from xfriend.engine.prompts import facts_prompt, transcript_text


def _parse_fact_list(text: str) -> list[str]:
    """Tolerantly parse a JSON array of strings from an LLM reply."""
    if not text:
        return []
    text = text.strip()
    m = re.search(r"\[[\s\S]*\]", text)
    if not m:
        return []
    try:
        parsed = json.loads(m.group(0))
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    return [str(x).strip() for x in parsed if str(x).strip()]


def extract_facts(llm, history: list[dict], existing: list[str], facts_max: int) -> list[str]:
    """Extract new facts from recent history and merge them (append-only,
    deduplicated, capped at facts_max). Runs on close/resume boundaries."""
    transcript = transcript_text(history)
    if not transcript.strip():
        return existing
    try:
        raw = llm.extract_facts(facts_prompt(transcript))
    except Exception:
        return existing  # never break persistence on a fact extraction failure
    new = _parse_fact_list(raw)
    merged = list(existing)
    seen = {f.lower() for f in merged}
    for fact in new:
        if fact.lower() not in seen:
            merged.append(fact)
            seen.add(fact.lower())
    return merged[:facts_max]