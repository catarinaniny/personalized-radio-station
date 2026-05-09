# Personalized Radio Station

A tiny backend-first experiment for generating a personal radio briefing.

Current flow:

```text
Google News RSS + Open-Meteo weather
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

By default, `config.example.yaml` uses OpenRouter through LiteLLM:

```yaml
ai:
  model: "openrouter/openrouter/auto"
  api_key_env: "OPENROUTER_API_KEY"
```

That model string is a little funny on purpose: LiteLLM uses the first
`openrouter/` as the provider prefix, and OpenRouter's Auto Router model ID is
`openrouter/auto`.

Add the default LLM and TTS keys to `.env`:

```bash
OPENROUTER_API_KEY=...
ELEVENLABS_API_KEY=...
```

You can switch to a specific OpenRouter model by changing the model:

```yaml
ai:
  model: "openrouter/meta-llama/llama-3.3-70b-instruct"
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
uv run radio check
```

## Test Source Fetching

Google News RSS and Open-Meteo fetching do not need LLM or TTS credentials:

```bash
uv run radio sources --limit-per-topic 2
```

That prints JSON with `weather` plus fetched `news` items. To test a copied
config explicitly:

```bash
uv run radio sources --config config.yaml
```

## Generate An Episode

After adding the keys to `.env`, run the whole pipeline in the foreground:

```bash
uv run radio generate
```

The CLI prints each stage as it runs:

```text
[radio] Fetching Google News RSS: artificial intelligence, startups, music technology
[radio] Fetching weather: Lisbon
[radio] Creating script with LiteLLM model: openrouter/openrouter/auto
[radio] Rendering TTS with elevenlabs: elevenlabs/eleven_multilingual_v2
[radio] Audio: episodes/2026-05-09-120000/episode.mp3
```

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

## Detached Runs

To start one full generation in the background:

```bash
uv run radio start
```

The command validates credentials first, then detaches the generation process.
It writes a PID/state file and a log under `runs/`:

```text
runs/
  radio.pid.json
  2026-05-09-120000.log
```

Check whether the detached process is still alive:

```bash
uv run radio status
```

## TTS

TTS is part of the default flow. `uv run radio generate` fetches sources,
creates a script, and renders speech.

```yaml
tts:
  enabled: true
  provider: "elevenlabs"
  model: "elevenlabs/eleven_multilingual_v2"
  response_format: "mp3"
  api_key_env: "ELEVENLABS_API_KEY"
```

Add `ELEVENLABS_API_KEY` to `.env`. This goes through LiteLLM's `speech()` API.
Voice values can be common mapped names like `alloy`/`onyx`, or raw ElevenLabs
voice IDs:

```yaml
tts:
  enabled: true
  provider: "elevenlabs"
  voices:
    host:
      voice: "alloy"
    anchor:
      voice: "onyx"
```

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
