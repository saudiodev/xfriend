"""Tests for the TurnEngine: turn loop, tool dispatch, media, parsing."""

from __future__ import annotations

from xfriend.engine.turn_engine import TurnEngine
from xfriend.memory import InMemoryStore
from xfriend.tools import send_audio_tool, send_image_tool
from tests.doubles import FauxImage, FauxLLM, FauxVoice, make_config, say, tool_call


def _engine(faux, config=None, image=None, voice=None):
    tools = []
    if image is not None:
        tools.append(send_image_tool(image))
    if voice is not None:
        tools.append(send_audio_tool(voice))
    cfg = config or make_config()
    eng = TurnEngine(cfg, faux, tools, InMemoryStore(), cfg.name)
    return eng


def test_plain_turn_no_tools():
    faux = FauxLLM(script=[say("Hey there!")])
    eng = _engine(faux)
    reply = eng.chat("hello")
    assert reply.text == "Hey there!"
    assert reply.media == []
    assert len(eng.history) == 2
    assert eng.history[0]["role"] == "user"
    assert eng.history[1]["role"] == "assistant"
    # tools not advertised when no modules are enabled
    _, tools = faux.calls[0]
    assert tools is None


def test_tool_loop_send_image():
    image = FauxImage()
    faux = FauxLLM(
        script=[
            tool_call("send_image", {"prompt": "a cat in a top hat"}),
            say("Here is your picture!"),
        ]
    )
    eng = _engine(faux, image=image)
    reply = eng.chat("draw me a cat")
    assert image.requests[0]["prompt"] == "a cat in a top hat"
    assert image.requests[0]["images"] == ["base.png"]  # fixed base image injected
    assert reply.text == "Here is your picture!"
    assert len(reply.media) == 1
    assert reply.media[0].type == "image"
    assert eng.history[1]["media"]  # media attached to assistant entry
    # the tool result was fed back into the LLM context
    messages, tools = faux.calls[1]
    assert messages[-1]["role"] == "tool"
    assert "Image sent" in messages[-1]["content"]


def test_send_image_with_loras():
    image = FauxImage()
    faux = FauxLLM(
        script=[
            tool_call("send_image", {"prompt": "nude art", "loras": ["dreamshaper"]}),
            say("Done!"),
        ]
    )
    eng = _engine(faux, image=image)
    eng.chat("make it artistic")
    assert image.requests[0]["loras"] == [
        {"name": "dreamshaper", "trigger": "ds", "url": "https://civitai/1"}
    ]


def test_send_audio():
    voice = FauxVoice()
    faux = FauxLLM(
        script=[
            tool_call("send_audio", {"text": "Goodnight, sweetheart."}),
            say("I whispered it to you."),
        ]
    )
    eng = _engine(faux, voice=voice)
    reply = eng.chat("say goodnight to me")
    assert len(reply.media) == 1
    assert reply.media[0].type == "audio"
    assert reply.media[0].path.endswith(".mp3")


def test_unknown_tool_error_roundtrips():
    faux = FauxLLM(
        script=[
            tool_call("bogus_tool", {}),
            say("I don't have that ability yet."),
        ]
    )
    eng = _engine(faux)
    reply = eng.chat("do the thing")
    assert reply.text == "I don't have that ability yet."
    messages, _ = faux.calls[1]
    assert "Unknown tool" in messages[-1]["content"]


def test_parse_say_variants():
    assert TurnEngine._parse_say('{"say": "hi"}') == "hi"
    assert TurnEngine._parse_say('```json\n{"say": "hello world"}\n```') == "hello world"
    assert TurnEngine._parse_say("Just a plain sentence.") == "Just a plain sentence."
    assert TurnEngine._parse_say("") == ""


def test_close_extracts_facts():
    faux = FauxLLM(script=[say("hi!")])
    cfg = make_config()
    eng = _engine(faux, config=cfg)
    eng.chat("hello")
    eng.close()
    assert "user likes cats" in eng.facts
    assert "user is a developer" in eng.facts