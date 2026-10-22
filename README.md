<div align="center">

# 💘 X/Friend

### The open-source **AI Girlfriend & AI Boyfriend** framework.

A modular engine for building **uncensored, explicit-ready AI companions** — a
swappable brain (LLM), a body that **sees** (image generation with LoRAs) and
a voice that **whispers** (audio messages). Her... or his. One config file.
Zero database lock-in. Launch your companion in minutes.

```bash
pip install xfriend
# or straight from the repo: pip install git+https://github.com/saudiodev/xfriend
```

</div>

---

## What is X/Friend?

X/Friend turns a plain text conversation into a full **AI girlfriend or AI
boyfriend experience**: your companion remembers you between sessions, carries
the scene forward when context gets long, sends you **pictures** and **voice
messages**, and adapts with **LoRAs** — including explicit/Civitai styles for
18+ roleplay.

Built for products like **Longcat-style companion apps**, anime girlfriends and
boyfriends, and NSFW roleplay bots. X/Friend is the conversation engine behind
the curtain — bring your own DB, UI, and monetization; X/Friend handles turns,
memory, and compression.

> The framework is DB-independent, model-agnostic, and drops into anything:
> a CLI bot, a web app, a Discord bot, a paid subscription service. Whether
> your companion is a *she*, a *he*, or a *they* — it's one config file.

---

## 🌟 Features

- **They speak.** Voice messages via **SecretVoice** — 29 premade voices (13
  female, 16 male) across 21 languages. ElevenLabs-compatible, so it drops
  into anything.
- **They see & create.** Image generation/editing via **Wavespeed Qwen**, with
  a fixed reference image (their look stays consistent) and **LoRA support**
  for custom styles — including Civitai 18+ LoRAs exposed by trigger word.
- **They remember.** Rolling-scene compaction ("SCENE SO FAR"), durable facts,
  and frustration cleanup — a 3-hour conversation feels as fresh as minute
  three.
- **They're open-minded.** Uncensored LLM support out of the box: **Venice**
  (default, GLM-4.7 based) plus **Grok** and **LongCat** presets. Any
  OpenAI-compatible endpoint works.
- **They're swappable.** Change providers by editing one config line. The
  persona stays byte-stable for prompt caching (faster + cheaper).
- **They have tools.** The model can call `send_image` and `send_audio` — and
  the tool list is extensible.
- **No DB required.** JSON-file persistence by default; plug in your own store
  with a 3-method protocol.

---

## 🎧 Hear them — real audio from the API

Generated live with the **candy** (her) and **blaze** (him) voices. GitHub
strips audio/video players from READMEs, so these are direct links — each one
plays in your browser.

### her, in the candy voice

- *"Hey you... I saved a spot for you right here. What are you waiting for?"* → [▶️ listen](https://github.com/saudiodev/xfriend/raw/main/examples/audio/candy-intro.mp3)
- *"Whisper my name... go on, I dare you. Do it and I'll tell you a secret."* → [▶️ listen](https://github.com/saudiodev/xfriend/raw/main/examples/audio/candy-secret.mp3)
- *"Come closer. I promise I'm not going to bite... unless you ask nicely."* → [▶️ listen](https://github.com/saudiodev/xfriend/raw/main/examples/audio/candy-comecloser.mp3)

### him, in the blaze voice

- *"Hey... I've been thinking about you all day. Come here, sit with me."* → [▶️ listen](https://github.com/saudiodev/xfriend/raw/main/examples/audio/blaze-intro.mp3)
- *"Say my name... slowly. I want to hear exactly how it sounds coming from you."* → [▶️ listen](https://github.com/saudiodev/xfriend/raw/main/examples/audio/blaze-secret.mp3)
- *"Come a little closer. I have something to tell you... and it's not for everyone else's ears."* → [▶️ listen](https://github.com/saudiodev/xfriend/raw/main/examples/audio/blaze-comecloser.mp3)

> 🎙️ Generate your own with any of the 29 voices:
> `voice: { enabled: true, voice_id: candy }` — or `velvet`, `whisper`,
> `angel`, `jade`, `titan`, `phoenix`, `duke`, `rico`...

---

## 🖼️ They send pictures, too

The companion generates images from their **fixed reference image** (their
face, their style — consistent), and can apply **LoRAs** for themed looks,
including explicit 18+ styles from **Civitai**:

```yaml
image:
  enabled: true
  base_image: ./assets/her.png       # their canonical look — never drifts
  loras:
    - name: dreamshaper              # exposed to the model by name
      trigger: dreamshaper
      url: https://civitai.com/api/download/models/12345
```

The model sees the LoRA list and can call `send_image(prompt, loras=[...])`
to generate whatever the scene calls for.

---

## ⚡ Quickstart

```bash
xfriend init luna
# edit luna/xfriend.yaml + luna/persona.md, export your API keys
xfriend run --config luna/xfriend.yaml
```

Or embed your companion in your product:

```python
from xfriend.orchestrator import build_from_file

companion = build_from_file("xfriend.yaml")
reply = companion.chat("good morning, gorgeous")
print(reply.text)
for media in reply.media:            # pictures they sent, voice notes they spoke
    print(media.type, media.url or media.path)
companion.close()                    # saves their memory + facts
```

---

## 🧠 How their memory works (no more "who are you?")

Long conversations get **compacted**, not lost:

- Context = persona (byte-stable for prompt caching) + facts + `SCENE SO FAR`
  summary + the last N verbatim turns
- When history grows past `keep_messages + compact_batch`, a background thread
  rolls the summary forward with **carry-forward rules** (names, promises,
  numbers, visual identity — the things that make them feel like they
  remember)
- **Facts** are extracted durably between sessions, so they greet you knowing
  your name, your kinks, your sister's birthday
- **Frustration cleanup** deletes the turns you pushed back on — as if they
  never happened

---

## 🧩 Modules & providers

| Family | Default provider | Swap with |
|---|---|---|
| **LLM** (the brain) | [Venice AI](https://venice.ai) — `olafangensan-glm-4.7-flash-heretic` (uncensored) | [Grok / xAI](https://x.ai), [LongCat](https://longcat.chat), any OpenAI-compatible `custom` |
| **Image** (the art) | [Wavespeed](https://wavespeed.ai) Qwen img2img + [Civitai](https://civitai.com) LoRAs | any image service |
| **Voice** (the voice) | [SecretVoice](https://secretvoice.dev) `secret-v1` (29 voices, 21 langs) | any ElevenLabs-compatible TTS |

All three speak standard protocols, so **swapping providers is a config edit**:

```yaml
llm:
  provider: grok        # venice | grok | longcat | custom
  model: grok-3
```

---

## 📄 Configuration

`xfriend init` scaffolds a commented template. The essentials:

```yaml
name: luna
persona_file: persona.md

llm:      { provider: venice, temperature: 0.7 }
image:    { enabled: true, base_image: ./assets/her.png, loras: [...] }
voice:    { enabled: true, voice_id: candy, language_code: en }
memory:   { store: json, keep_messages: 16, compact_batch: 10 }
```

API keys come from the environment:
`VENICE_INFERENCE_KEY`, `XAI_API_KEY`, `LONGCAT_API_KEY`,
`WAVESPEED_API_KEY`, `SECRETVOICE_API_KEY`.

---

## 🛠️ CLI

```
xfriend init <name>                 # scaffold a companion
xfriend run --config <path>         # interactive chat  (--once "..." for 1 turn)
xfriend doctor --config <path>      # validate keys / base_image / wiring
```

---

## 📦 Install

```bash
pip install xfriend            # from PyPI
# or from source:
pip install git+https://github.com/saudiodev/xfriend
```

---

## ⚠️ 18+ notice

This is an **explicit-ready** framework. It does not filter, censor, or
moralize — it ships with uncensored model presets and LoRA plumbing for adult
content. You are responsible for complying with your deployment platform's
content policies and your jurisdiction's laws. The sample audio clips are
flirty, not explicit — tune your persona as far as you need.

## License

MIT