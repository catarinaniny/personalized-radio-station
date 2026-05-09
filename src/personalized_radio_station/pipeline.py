from __future__ import annotations

from argparse import ArgumentParser
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Callable
import json

from .config import load_config, parse_duration
from .env import load_env_file
from .news import fetch_google_news
from .runtime import assert_runtime_ready, missing_runtime_requirements
from .script import generate_script, render_markdown
from .tts import synthesize_episode
from .weather import fetch_weather


def _quiet_log(message: str) -> None:
    return None


def generate_episode(
    config_path: Path,
    output_dir: Path,
    skip_tts: bool = False,
    allow_mock: bool = False,
    duration: str | None = None,
    log: Callable[[str], None] = _quiet_log,
) -> Path:
    log(f"Loading config: {config_path}")
    config = load_config(config_path)
    if duration is not None:
        config = replace(config, duration=parse_duration(duration))
    log("Checking runtime requirements")
    assert_runtime_ready(config, include_tts=not skip_tts, allow_mock=allow_mock)

    topics = ", ".join(config.news.topics)
    log(f"Fetching Google News RSS: {topics}")
    news_items = fetch_google_news(config.news)
    log(f"Fetched {len(news_items)} news items")

    log(f"Fetching weather: {config.weather.name}")
    weather = fetch_weather(config.weather)
    log(
        "Weather fetched"
        if weather.temperature_c is None
        else f"Weather fetched: {weather.temperature_c}C in {weather.location}"
    )

    log(f"Creating script targeting {config.duration.label} with LiteLLM model: {config.ai.model}")
    episode = generate_script(news_items, weather, config)
    segment_count = len(episode.get("segments", []))
    log(f"Script created with {segment_count} segments")

    episode_dir = output_dir / datetime.now().strftime("%Y-%m-%d-%H%M%S")
    episode_dir.mkdir(parents=True, exist_ok=True)
    log(f"Saving episode artifacts: {episode_dir}")

    (episode_dir / "sources.json").write_text(
        json.dumps(
            {
                "weather": weather.to_dict(),
                "news": [item.to_dict() for item in news_items],
            },
            indent=2,
        )
        + "\n"
    )
    if not skip_tts:
        if config.tts.enabled:
            log(f"Rendering TTS with {config.tts.provider}: {config.tts.model}")
        else:
            log("TTS is disabled in config; no audio will be created")
        tts_result = synthesize_episode(episode, config, episode_dir)
        if tts_result.episode_file:
            episode["audio_file"] = tts_result.episode_file.name
            log(f"Audio created: {tts_result.episode_file}")
        elif config.tts.enabled:
            log("TTS finished, but no assembled episode audio was created")
    else:
        log("Skipping TTS by request; no audio will be created")

    (episode_dir / "episode.json").write_text(json.dumps(episode, indent=2) + "\n")
    (episode_dir / "script.md").write_text(render_markdown(episode))
    log(f"Script saved: {episode_dir / 'script.md'}")

    latest = output_dir / "latest"
    if latest.exists() or latest.is_symlink():
        latest.unlink()
    latest.symlink_to(episode_dir.name)
    log(f"Latest episode link updated: {latest}")

    return episode_dir


def main() -> None:
    parser = ArgumentParser(description="Generate a personalized radio episode script.")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config.yaml"),
        help="Path to config YAML.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("episodes"),
        help="Directory where episode artifacts are saved.",
    )
    parser.add_argument(
        "--env",
        type=Path,
        default=Path(".env"),
        help="Path to a .env file with provider API keys.",
    )
    parser.add_argument(
        "--duration",
        help="Target duration, e.g. `18m`, `18 minutes`, `1 hour`, or `unlimited`.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate config and runtime credentials without fetching sources.",
    )
    args = parser.parse_args()

    load_env_file(args.env)

    config_path = args.config
    if not config_path.exists() and config_path == Path("config.yaml"):
        config_path = Path("config.example.yaml")

    if args.check:
        config = load_config(config_path)
        missing = missing_runtime_requirements(config, include_tts=True)
        if missing:
            print("Missing runtime requirements:")
            for item in missing:
                print(f"- {item}")
            raise SystemExit(1)
        print("Runtime requirements look OK.")
        return

    episode_dir = generate_episode(
        config_path,
        args.output_dir,
        duration=args.duration,
        log=lambda message: print(f"[radio] {message}", flush=True),
    )
    print(f"Generated episode: {episode_dir}")
