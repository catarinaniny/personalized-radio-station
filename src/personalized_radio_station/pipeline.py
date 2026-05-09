from __future__ import annotations

from argparse import ArgumentParser
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Callable
import json

from .audio import audio_duration_seconds
from .config import load_config, parse_duration
from .env import load_env_file
from .news import fetch_google_news
from .runtime import assert_runtime_ready, missing_runtime_requirements
from .script import generate_script, render_markdown
from .timing import count_episode_words, effective_words_per_minute, format_duration, word_budget
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
    script_words = count_episode_words(episode)
    budget = word_budget(config)
    episode["timing"] = _timing_metadata(config, script_words)
    if budget:
        log(
            f"Script created with {segment_count} segments and {script_words} words "
            f"(target {budget.min_words}-{budget.max_words})"
        )
    else:
        log(f"Script created with {segment_count} segments and {script_words} words")

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
            _add_audio_timing(episode, tts_result.episode_file, script_words, config)
            log(f"Audio created: {tts_result.episode_file}")
            audio_label = episode.get("timing", {}).get("audio_duration_label")
            if audio_label:
                target_label = episode.get("timing", {}).get("target_duration")
                delta_label = episode.get("timing", {}).get("target_delta_label")
                if delta_label and target_label != "unlimited":
                    log(f"Audio duration: {audio_label} (target {target_label}, delta {delta_label})")
                else:
                    log(f"Audio duration: {audio_label}")
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


def _timing_metadata(config, script_words: int) -> dict:
    budget = word_budget(config)
    return {
        "target_duration": config.duration.label,
        "target_minutes": config.duration.minutes,
        "estimated_words_per_minute": effective_words_per_minute(config),
        "target_words": budget.target_words if budget else None,
        "target_word_range": (
            {"min": budget.min_words, "max": budget.max_words}
            if budget
            else None
        ),
        "script_words": script_words,
    }


def _add_audio_timing(episode: dict, audio_file: Path, script_words: int, config) -> None:
    audio_seconds = audio_duration_seconds(audio_file)
    if audio_seconds is None:
        return

    timing = episode.setdefault("timing", {})
    timing["audio_duration_seconds"] = round(audio_seconds, 3)
    timing["audio_duration_label"] = format_duration(audio_seconds)
    if audio_seconds > 0:
        timing["measured_words_per_minute"] = round(script_words / (audio_seconds / 60), 1)

    if config.duration.minutes is not None:
        target_seconds = config.duration.minutes * 60
        delta_seconds = audio_seconds - target_seconds
        timing["target_delta_seconds"] = round(delta_seconds, 3)
        timing["target_delta_label"] = _format_signed_duration(delta_seconds)
        timing["target_delta_percent"] = round((delta_seconds / target_seconds) * 100, 1)


def _format_signed_duration(seconds: float) -> str:
    sign = "+" if seconds >= 0 else "-"
    label = format_duration(abs(seconds)) or "0:00"
    return f"{sign}{label}"


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
