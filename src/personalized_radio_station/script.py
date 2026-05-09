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
        "target_duration": config.duration.label,
        "target_minutes": config.duration.minutes,
        "voices": config.voices,
        "opening_style": "already_on_air_listener_just_tuned_in",
        "voice_policy": (
            f'Use the voice label "{config.tts.primary_voice}" for every segment.'
            if config.tts.single_voice
            else "Use the configured voice labels by segment."
        ),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "weather": weather.to_dict(),
        "news": [item.to_dict() for item in news_items],
    }

    return (
        "Create a personalized radio episode script.\n"
        "Output JSON with this shape:\n"
        "{\n"
        '  "title": "Episode title",\n'
        '  "segments": [\n'
        '    {"type": "intro|weather|news|outro", "voice": "host", "text": "..."}\n'
        "  ]\n"
        "}\n\n"
        "The first segment must feel like the station was already playing and the "
        "listener has just tuned in. Start mid-flow, as if the host is already "
        "speaking, then smoothly move into the briefing. Do not begin with a formal "
        "welcome, episode setup, or phrase like `Good morning, here is...`.\n"
        "Use the same voice label for every segment when the voice_policy says so. "
        "Keep it natural for TTS. Avoid markdown. Mention source names when useful, "
        "but do not include raw URLs in the spoken text. If target_duration is "
        "`unlimited`, prioritize useful coverage over fitting a fixed runtime.\n\n"
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
