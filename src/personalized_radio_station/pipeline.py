from __future__ import annotations

from argparse import ArgumentParser
from datetime import datetime
from pathlib import Path
import json

from .config import load_config
from .env import load_env_file
from .news import fetch_google_news
from .runtime import assert_runtime_ready, missing_runtime_requirements
from .script import generate_script, render_markdown
from .tts import synthesize_episode
from .weather import fetch_weather


def generate_episode(
    config_path: Path,
    output_dir: Path,
    skip_tts: bool = False,
    allow_mock: bool = False,
) -> Path:
    config = load_config(config_path)
    assert_runtime_ready(config, include_tts=not skip_tts, allow_mock=allow_mock)

    news_items = fetch_google_news(config.news)
    weather = fetch_weather(config.weather)
    episode = generate_script(news_items, weather, config)

    episode_dir = output_dir / datetime.now().strftime("%Y-%m-%d-%H%M%S")
    episode_dir.mkdir(parents=True, exist_ok=True)

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
        tts_result = synthesize_episode(episode, config, episode_dir)
        if tts_result.episode_file:
            episode["audio_file"] = tts_result.episode_file.name

    (episode_dir / "episode.json").write_text(json.dumps(episode, indent=2) + "\n")
    (episode_dir / "script.md").write_text(render_markdown(episode))

    latest = output_dir / "latest"
    if latest.exists() or latest.is_symlink():
        latest.unlink()
    latest.symlink_to(episode_dir.name)

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
        "--skip-tts",
        action="store_true",
        help="Generate the script but skip speech rendering.",
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
        missing = missing_runtime_requirements(config, include_tts=not args.skip_tts)
        if missing:
            print("Missing runtime requirements:")
            for item in missing:
                print(f"- {item}")
            raise SystemExit(1)
        print("Runtime requirements look OK.")
        return

    episode_dir = generate_episode(config_path, args.output_dir, skip_tts=args.skip_tts)
    print(f"Generated episode: {episode_dir}")
