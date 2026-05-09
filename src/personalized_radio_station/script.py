from __future__ import annotations

from datetime import datetime
import json

from .ai import generate_text
from .config import AppConfig
from .news import NewsItem
from .weather import WeatherReport


def generate_script(
    news_items: list[NewsItem], weather: WeatherReport, config: AppConfig
) -> dict:
    messages = [
        {
            "role": "system",
            "content": (
                "You are a radio producer writing spoken-word scripts. "
                "Use only the provided news and weather context. "
                "Return valid JSON only."
            ),
        },
        {
            "role": "user",
            "content": _build_prompt(news_items, weather, config),
        },
    ]

    raw = generate_text(messages, config.ai)
    return _parse_episode(raw)


def render_markdown(episode: dict) -> str:
    lines = [f"# {episode.get('title', 'Personalized Radio Briefing')}", ""]

    for segment in episode.get("segments", []):
        segment_type = segment.get("type", "segment").title()
        voice = segment.get("voice", "host")
        text = segment.get("text", "").strip()
        lines.extend([f"## {segment_type} ({voice})", "", text, ""])

    return "\n".join(lines).strip() + "\n"


def _build_prompt(
    news_items: list[NewsItem], weather: WeatherReport, config: AppConfig
) -> str:
    context = {
        "station_name": config.station_name,
        "style": config.style,
        "target_minutes": config.episode_minutes,
        "voices": config.voices,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "weather": weather.to_dict(),
        "news": [item.to_dict() for item in news_items],
    }

    return (
        "Create a short personalized radio episode script.\n"
        "Output JSON with this shape:\n"
        "{\n"
        '  "title": "Episode title",\n'
        '  "segments": [\n'
        '    {"type": "intro|weather|news|outro", "voice": "host|anchor", "text": "..."}\n'
        "  ]\n"
        "}\n\n"
        "Keep it natural for TTS. Avoid markdown. Mention source names when useful, "
        "but do not include raw URLs in the spoken text.\n\n"
        f"Context:\n{json.dumps(context, indent=2)}"
    )


def _parse_episode(raw: str) -> dict:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(raw[start : end + 1])
            except json.JSONDecodeError:
                pass

    return {
        "title": "Personalized Radio Briefing",
        "segments": [{"type": "script", "voice": "host", "text": raw.strip()}],
    }
