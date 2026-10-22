# xfriend

Modular AI companion framework. Text conversations with **compression**: a
swappable LLM, image generation/editing with LoRA support, and voice messages
— all wired through one orchestrator config. Independent of any product
database.

Inspired by the proven callclimax voice engine (rolling-scene compaction,
durable facts, byte-stable prompts for caching) and Pipecat's service-swap
philosophy.

```bash
pip install git+https://github.com/saudiodev/xfriend
```

## Quickstart

```bash
xfriend init luna
# edit luna/xfriend.yaml, luna/persona.md, export your API keys
xfriend run --config luna/xfriend.yaml
```

Or in code:

```python
from xfriend.orchestrator import build_from_file

companion = build_from_file("xfriend.yaml")
reply = companion.chat("draw me something cute")
print(reply.text)
for media in reply.media:          # the companion sent images / voice notes
    print(media.type, media.url or media.path)

companion.close()                  # extracts durable facts + persists state
```

## Modules

| Family | Interface | Default | Swappable with |
|---|---|---|---|
| **LLM** | OpenAI-compatible chat completions | **Venice** `olafangensan-glm-4.7-flash-heretic` | Grok (`api.x.ai`), LongCat (`api.longcat.chat`), any `custom` base_url |
| **Image** | img2img with LoRAs | **Wavespeed Qwen** `wavespeed-ai/qwen-image/edit-2511-lora` | any image service |
| **Voice** | TTS → audio file | **SecretAudio** (`secret-v1`, 29 voices) | any ElevenLabs-compatible endpoint |

All LLMs speak the OpenAI chat-completions protocol, so switching providers is
a config change:

```yaml
llm:
  provider: grok            # venice | grok | longcat | custom
  # model: grok-3
```

## The two model functions

The companion's model gets two tools (extensible via the `Tool` registry):

- **`send_image(prompt, loras?, size?, seed?)`** — generates/edits an image.
  The companion's fixed `base_image` is the reference; **LoRAs** (e.g.
  Civitai +18 styles) are listed in the config and exposed to the model by
  name.
- **`send_audio(text, voice_id?, language_code?)`** — speaks a voice message
  through SecretAudio.

Each tool is registered only when its module is enabled, so the model never
sees a tool it can't use.

## Compaction (the memory engine)

Ported from callclimax's live-call engine, adapted for text:

- Trigger when history exceeds `keep_messages + compact_batch` (default 16+10)
- **Background thread** — never blocks a reply; race guard prevents stale
  summaries from clobbering a reset conversation
- Rolling **"SCENE SO FAR"** summary with carry-forward rules (names, numbers,
  promises, visual identity)
- **Frustration cleanup**: a deterministic audit deletes assistant turns the
  user pushed back on
- **Facts**: append-only durable memory extracted on `close()`
- Context = persona (byte-stable for prompt caching) + facts + summary + last
  N verbatim turns
- Media (images/audio) are summarized as text markers, so long conversations
  stay compact

## Memory independence

The framework persists through a tiny `MemoryStore` protocol
(`load` / `save` / `reset`). JSON files ship by default; SQLite, your own
database, or CockroachDB plug in with a handful of methods.

```python
from xfriend.memory import MemoryStore

class MyStore(MemoryStore):
    def load(self, companion_id): ...
    def save(self, companion_id, state): ...
    def reset(self, companion_id): ...
```

## Configuration

Full reference: `xfriend init` emits a commented template. Key points:

```yaml
image:
  enabled: true
  base_image: ./assets/luna.png     # fixed reference — never rolls
  loras:
    - name: dreamshaper
      trigger: ds
      url: https://civitai.com/api/download/models/123
voice:
  enabled: true
  voice_id: velvet
memory:
  store: json                       # json | inmemory
  keep_messages: 16
  compact_batch: 10
```

API keys come from the environment: `VENICE_INFERENCE_KEY`,
`XAI_API_KEY`, `LONGCAT_API_KEY`, `WAVESPEED_API_KEY`, `SECRETVOICE_API_KEY`
(or inline in the config).

## CLI

```
xfriend init <name>                 # scaffold a companion
xfriend run --config <path>         # interactive chat (--once "msg" for one turn)
xfriend doctor --config <path>      # validate keys, base_image, wiring
```

## License

MIT