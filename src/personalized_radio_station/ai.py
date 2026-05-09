from __future__ import annotations

import json
import os
from typing import Any

from .config import AiConfig


Message = dict[str, str]


def generate_text(messages: list[Message], config: AiConfig) -> str:
    if config.model == "mock":
        return _mock_completion(messages)

    try:
        from litellm import completion
    except ImportError as exc:
        raise RuntimeError(
            "LiteLLM is not installed. Install dependencies with `pip install -e .`."
        ) from exc

    kwargs: dict[str, Any] = {
        "model": config.model,
        "messages": messages,
        "temperature": config.temperature,
    }
    if config.api_base:
        kwargs["api_base"] = config.api_base
    if config.api_key_env:
        api_key = os.environ.get(config.api_key_env)
        if not api_key:
            raise RuntimeError(f"Missing {config.api_key_env} for LiteLLM.")
        kwargs["api_key"] = api_key
    if config.max_tokens:
        kwargs["max_tokens"] = config.max_tokens

    response = completion(**kwargs)
    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("LiteLLM returned an empty response.")

    return content


def _mock_completion(messages: list[Message]) -> str:
    prompt = messages[-1]["content"] if messages else ""
    station_name = "Personal Radio"
    try:
        context = json.loads(prompt.split("Context:\n", 1)[1])
        station_name = context.get("station_name", station_name)
        weather = context.get("weather", {})
        news = context.get("news", [])
    except (IndexError, json.JSONDecodeError):
        weather = {}
        news = []

    segments = [
        {
            "type": "intro",
            "voice": "host",
            "text": (
                f"...and that is the thread running through this hour on {station_name}. "
                "Let's bring the briefing into focus."
            ),
        }
    ]
    if weather:
        segments.append(
            {
                "type": "weather",
                "voice": "host",
                "text": (
                    f"In {weather.get('location', 'your area')}, it is "
                    f"{weather.get('temperature_c', 'unknown')} degrees Celsius."
                ),
            }
        )

    for item in news[:3]:
        source = item.get("source") or "a news source"
        segments.append(
            {
                "type": "news",
                "voice": "host",
                "text": f"{source} reports: {item.get('title', 'Untitled story')}.",
            }
        )

    segments.append(
        {
            "type": "outro",
            "voice": "host",
            "text": "That is the briefing. Thanks for listening.",
        }
    )
    return json.dumps({"title": f"{station_name} Briefing", "segments": segments})
