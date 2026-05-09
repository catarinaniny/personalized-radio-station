from __future__ import annotations

from argparse import ArgumentParser
from pathlib import Path
import json

from .config import load_config
from .news import fetch_news
from .weather import fetch_weather


def fetch_sources(config_path: Path, limit_per_topic: int = 5) -> dict:
    config = load_config(config_path)
    news_items = fetch_news(config.news, limit_per_feed=limit_per_topic)
    weather = fetch_weather(config.weather)

    return {
        "weather": weather.to_dict(),
        "news": [item.to_dict() for item in news_items],
    }


def main() -> None:
    parser = ArgumentParser(description="Fetch news and weather sources only.")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config.yaml"),
        help="Path to config YAML.",
    )
    parser.add_argument(
        "--limit-per-topic",
        type=int,
        default=3,
        help="Maximum RSS items to keep for each Google News topic or feed.",
    )
    args = parser.parse_args()

    config_path = args.config
    if not config_path.exists() and config_path == Path("config.yaml"):
        config_path = Path("config.example.yaml")

    print(json.dumps(fetch_sources(config_path, args.limit_per_topic), indent=2))


if __name__ == "__main__":
    main()
