# VibeFM

A tiny backend-first experiment for generating a VibeFM briefing.

Current flow:

```text
Google News + RSS/Atom feeds + Open-Meteo weather
        ↓
LiteLLM script generation
        ↓
LiteLLM TTS rendering
        ↓
episode.json + script.md + episode.mp3
```

The important part is that the AI layer is isolated in
`src/personalized_radio_station/ai.py`, so the project can switch between
OpenRouter, OpenAI, Anthropic, Ollama, or anything else LiteLLM supports. TTS is
isolated separately in `src/personalized_radio_station/tts.py`.

## Setup

```bash
uv sync
cp config.example.yaml config.yaml
cp .env.example .env
```

Set the target show length in `config.yaml`:

```yaml
duration: "5 minutes"
```

Use `"unlimited"` for an open-ended episode:

```yaml
duration: "unlimited"
```

News comes from Google News searches plus normal RSS/Atom feeds. The default
feed set includes TechCrunch, Product Hunt, and Hacker News:

```yaml
news:
  topics:
    - "artificial intelligence"
    - "startups"
    - "music technology"
  rss_feeds:
    - "https://techcrunch.com/feed/"
    - "https://www.producthunt.com/feed"
    - "https://hnrss.org/frontpage"
```

By default, `config.example.yaml` uses OpenRouter's Nitro route for
`openai/gpt-oss-20b` through LiteLLM:

```yaml
ai:
  model: "openrouter/openai/gpt-oss-20b:nitro"
  api_key_env: "OPENROUTER_API_KEY"
  max_tokens: 4000
  reasoning:
    effort: "low"
    exclude: true
```

Add the default LLM and TTS keys to `.env`:

```bash
OPENROUTER_API_KEY=...
ELEVENLABS_API_KEY=...
```

OpenRouter's model ID is `openai/gpt-oss-20b:nitro`; the config includes the
leading `openrouter/` so LiteLLM routes it through OpenRouter. The low reasoning
setting keeps enough output budget available for the final JSON script.

You can switch to a specific OpenRouter model by changing the model:

```yaml
ai:
  model: "openrouter/meta-llama/llama-3.3-70b-instruct"
  api_key_env: "OPENROUTER_API_KEY"
```

Or switch providers entirely while keeping the same application code:

```yaml
ai:
  model: "openai/gpt-4.1-mini"
  api_key_env: "OPENAI_API_KEY"
```

```yaml
ai:
  model: "anthropic/claude-3-5-haiku-latest"
  api_key_env: "ANTHROPIC_API_KEY"
```

```yaml
ai:
  model: "ollama/llama3.1"
  api_base: "http://localhost:11434"
```

Provider API keys are read from environment variables such as
`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `OPENROUTER_API_KEY`, and
`ELEVENLABS_API_KEY`.

You can validate the configured runtime before fetching anything:

```bash
uv run vibefm check
```

## Test Source Fetching

RSS/Atom and Open-Meteo fetching do not need LLM or TTS credentials:

```bash
uv run vibefm sources --limit-per-topic 2
```

That prints JSON with `weather` plus fetched `news` items. To test a copied
config explicitly:

```bash
uv run vibefm sources --config config.yaml
```

## Generate An Episode

After adding the keys to `.env`, run the whole pipeline in the foreground:

```bash
uv run vibefm generate
```

Override the target duration for one run:

```bash
uv run vibefm generate --duration 18m
uv run vibefm generate --duration unlimited
```

The CLI prints each stage as it runs:

```text
[vibefm] Fetching news RSS sources: Google News (artificial intelligence, startups, music technology); 3 RSS feeds
[vibefm] Fetching weather: Lisbon
[vibefm] Creating script targeting 18 minutes with LiteLLM model: openrouter/openai/gpt-oss-20b:nitro
[vibefm] Rendering TTS with elevenlabs: elevenlabs/eleven_multilingual_v2
[vibefm] Audio: episodes/2026-05-09-120000/episode.mp3
```

The opening is intentionally written as if the station was already on air and
you just tuned in. It should not start with a formal welcome.

Outputs are saved under `episodes/`:

```text
episodes/
  latest -> 2026-05-09-120000
  2026-05-09-120000/
    sources.json
    episode.json
    script.md
    episode.mp3
    audio/
```

## Local API + File Frontend

Run the local backend API:

```bash
uv run vibefm web
```

Then open the standalone test page directly from this repo:

```text
radio_test.html
```

The backend root at `http://127.0.0.1:8765` returns API status JSON. The UI is
not served by the backend anymore; `radio_test.html` is one self-contained HTML
file that can be opened with `file://`.

The file page has Demo and Real modes plus a duration-minutes input. Demo is
selected by default, creates an episode through `POST /api/episodes`, listens to
`GET /api/episodes/{id}/events` with Server-Sent Events, and plays each
generated audio segment through Web Audio as soon as that segment is ready. Demo
mode writes normal episode artifacts under `episodes/{episode_id}/`, but does
not call LLM, TTS, news, or weather APIs.

The file page also shows a debug timing log from the event stream. Each status,
script-ready, segment-ready, completion, or failure event includes
`elapsed_seconds`, which helps identify whether startup time is source fetching,
script generation, TTS, or audio playback scheduling.

Real mode uses the configured `config.yaml` and `.env`:

```bash
uv run vibefm web --config config.yaml --env .env
```

When the frontend sends `"mode": "real"`, the server validates runtime
requirements, fetches Google News, configured RSS/Atom feeds, and Open-Meteo weather, generates the
script with the configured LiteLLM model, renders TTS with the configured
provider, emits `segment_ready` events as each TTS segment is written, and serves
the final stitched episode audio when complete.

## Detached Runs

To start one full generation in the background:

```bash
uv run vibefm start
```

Detached runs accept the same duration override:

```bash
uv run vibefm start --duration 18m
```

The command validates credentials first, then detaches the generation process.
It writes a PID/state file and a log under `runs/`:

```text
runs/
  vibefm.pid.json
  2026-05-09-120000.log
```

Check whether the detached process is still alive:

```bash
uv run vibefm status
```

## TTS

TTS is part of the default flow. `uv run vibefm generate` fetches sources,
creates a script, and renders speech.

```yaml
tts:
  enabled: true
  provider: "elevenlabs"
  model: "elevenlabs/eleven_multilingual_v2"
  response_format: "mp3"
  api_key_env: "ELEVENLABS_API_KEY"
  single_voice: true
  primary_voice: "host"
  words_per_minute: 155
```

Add `ELEVENLABS_API_KEY` to `.env`. This goes through LiteLLM's `speech()` API.
By default every segment MP3 uses the same `primary_voice`, so stitched audio
sounds like one person speaking continuously. Voice values can be common mapped
names like `alloy`, or raw ElevenLabs voice IDs:

```yaml
tts:
  enabled: true
  provider: "elevenlabs"
  single_voice: true
  primary_voice: "host"
  voices:
    host:
      voice: "alloy"
      words_per_minute: 155
```

Duration targeting uses `words_per_minute` to estimate how many words the script
should contain. After TTS, `episode.json` stores the actual audio duration and
measured words per minute, which you can use to tune this value for your chosen
voice.

To avoid wasting tokens, the app only makes one length-correction LLM call, and
only when the first script is outside the target word range. Unlimited episodes
skip this correction.

The TTS interface is still provider-swappable. For OpenAI/Azure-style speech,
use the same LiteLLM speech path:

```yaml
tts:
  enabled: true
  provider: "litellm"
  model: "openai/gpt-4o-mini-tts"
  response_format: "wav"
  api_key_env: "OPENAI_API_KEY"
  voices:
    host:
      voice: "alloy"
      instructions: "Warm, conversational, casual morning radio host."
    anchor:
      voice: "onyx"
      instructions: "Clear, steady, professional news reader."
```

Piper is also wired as a local TTS provider:

```yaml
tts:
  enabled: true
  provider: "piper"
  piper_path: "piper"
  piper_model_path: "/path/to/voice.onnx"
```

## Cost Estimates

These are rough API-cost estimates for one 5 minute episode, last checked on
2026-05-09. Provider pricing changes, so treat this as a planning guide.

Assumptions:

- around 3,000 input tokens and 1,200 output tokens for the script
- around 750 spoken words, or 4,500-5,000 TTS characters
- no free tiers, credits, caching, Batch API discounts, taxes, or OpenRouter
  credit-purchase fees included

Simple 5 minute cost guide:

OpenAI TTS means `openai/gpt-4o-mini-tts` in the list below.

- `openai/gpt-4o-mini` + OpenAI TTS = ~$0.08 / 5 minutes. Cheap and good.
- `openai/gpt-4.1-mini` + OpenAI TTS = ~$0.08 / 5 minutes. Better script.
- `anthropic/claude-haiku-4.5` + OpenAI TTS = ~$0.08-$0.09 / 5 minutes. Better writing than most budget models.
- `anthropic/claude-sonnet-4.6` + OpenAI TTS = ~$0.10 / 5 minutes. Strong script quality.
- `openai/gpt-5.5` + OpenAI TTS = ~$0.13 / 5 minutes. Premium script, budget voice.
- `openai/gpt-4.1-mini` + ElevenLabs Flash/Turbo = ~$0.25-$0.30 / 5 minutes. Good script, better voice.
- `anthropic/claude-haiku-4.5` + ElevenLabs Flash/Turbo = ~$0.26-$0.31 / 5 minutes. Better writing, good voice.
- `anthropic/claude-sonnet-4.6` + ElevenLabs Flash/Turbo = ~$0.28-$0.33 / 5 minutes. Strong writing, good voice.
- `openai/gpt-5.5` + ElevenLabs Flash/Turbo = ~$0.30-$0.35 / 5 minutes. Premium script, good voice.
- `openai/gpt-4.1-mini` + ElevenLabs Multilingual v2/v3 = ~$0.45-$0.60 / 5 minutes. Budget script, premium voice.
- `anthropic/claude-haiku-4.5` + ElevenLabs Multilingual v2/v3 = ~$0.46-$0.61 / 5 minutes. Good balance.
- `anthropic/claude-sonnet-4.6` + ElevenLabs Multilingual v2/v3 = ~$0.48-$0.63 / 5 minutes. Premium-feeling brief.
- `openai/gpt-5.5` + ElevenLabs Multilingual v2/v3 = ~$0.50-$0.65 / 5 minutes. High-end cloud option.
- `openrouter/openrouter/auto` + ElevenLabs Multilingual v2/v3 = variable, often ~$0.46-$0.65 / 5 minutes. Check OpenRouter Activity.
- `ollama/...` + Piper = $0 API cost / 5 minutes. Local/offline; quality depends on your models.

Anthropic currently covers the script-generation side here, not TTS, so Claude
models need to be paired with OpenAI, ElevenLabs, Piper, or another speech
provider. Sources: [OpenAI pricing](https://openai.com/api/pricing/),
[OpenAI TTS model pricing](https://developers.openai.com/api/docs/models/gpt-4o-mini-tts),
[Anthropic pricing](https://platform.claude.com/docs/en/about-claude/pricing),
[ElevenLabs API pricing](https://elevenlabs.io/pricing/api/),
[Google Gemini pricing](https://ai.google.dev/gemini-api/docs/pricing), and
[OpenRouter Auto Router](https://openrouter.ai/docs/features/model-routing).

## Tests

```bash
uv run python -m unittest discover -s tests
```

Tests use internal mock LLM/TTS providers for deterministic runs. Normal CLI
runs reject those mock providers so real usage goes through LiteLLM-backed
providers such as OpenRouter, OpenAI, Anthropic, or Ollama.

## What Is Intentionally Missing

- no database
- no API server
- no queue
- no user accounts

The next backend step is to add a small API or scheduler once the CLI flow feels
good.
