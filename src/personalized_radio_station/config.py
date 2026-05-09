from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import re


@dataclass(frozen=True)
class NewsConfig:
    topics: list[str]
    language: str = "en-US"
    country: str = "US"


@dataclass(frozen=True)
class WeatherConfig:
    name: str
    latitude: float
    longitude: float


@dataclass(frozen=True)
class AiConfig:
    model: str
    api_base: str | None = None
    api_key_env: str | None = None
    temperature: float = 0.7
    max_tokens: int | None = None
    reasoning: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EpisodeDuration:
    minutes: int | None
    label: str

    @property
    def is_unlimited(self) -> bool:
        return self.minutes is None


@dataclass(frozen=True)
class TtsVoiceConfig:
    voice: str
    instructions: str | None = None
    speed: float = 1.0
    words_per_minute: int | None = None
    speaker: str | None = None
    settings: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TtsConfig:
    enabled: bool = True
    provider: str = "elevenlabs"
    model: str = "elevenlabs/eleven_multilingual_v2"
    response_format: str = "mp3"
    api_base: str | None = None
    api_key_env: str | None = "ELEVENLABS_API_KEY"
    single_voice: bool = True
    primary_voice: str = "host"
    words_per_minute: int = 155
    piper_path: str = "piper"
    piper_model_path: str | None = None
    voices: dict[str, TtsVoiceConfig] = field(default_factory=dict)


@dataclass(frozen=True)
class AppConfig:
    station_name: str
    style: str
    duration: EpisodeDuration
    news: NewsConfig
    weather: WeatherConfig
    ai: AiConfig
    tts: TtsConfig = field(default_factory=TtsConfig)
    voices: dict[str, str] = field(default_factory=dict)

    @property
    def episode_minutes(self) -> int | None:
        return self.duration.minutes


def load_config(path: str | Path) -> AppConfig:
    config_path = Path(path)
    raw = _load_yaml(config_path)

    news = raw.get("news", {})
    weather = raw.get("weather", {})
    ai = raw.get("ai", {})
    tts = raw.get("tts", {})
    tts_provider = tts.get("provider", "elevenlabs")
    tts_model = tts.get("model", _default_tts_model(tts_provider))

    return AppConfig(
        station_name=raw.get("station_name", "Personal Radio"),
        style=raw.get("style", "casual, concise morning radio"),
        duration=parse_duration(raw.get("duration", raw.get("episode_minutes", 5))),
        news=NewsConfig(
            topics=list(news.get("topics", [])),
            language=news.get("language", "en-US"),
            country=news.get("country", "US"),
        ),
        weather=WeatherConfig(
            name=weather["name"],
            latitude=float(weather["latitude"]),
            longitude=float(weather["longitude"]),
        ),
        ai=AiConfig(
            model=ai["model"],
            api_base=ai.get("api_base"),
            api_key_env=ai.get("api_key_env"),
            temperature=float(ai.get("temperature", 0.7)),
            max_tokens=_optional_int(ai.get("max_tokens")),
            reasoning=dict(ai.get("reasoning", {})),
        ),
        tts=TtsConfig(
            enabled=_as_bool(tts.get("enabled", True)),
            provider=tts_provider,
            model=tts_model,
            response_format=tts.get(
                "response_format", _default_tts_response_format(tts_provider)
            ),
            api_base=tts.get("api_base", _default_tts_api_base(tts_provider)),
            api_key_env=tts.get(
                "api_key_env", _default_tts_api_key_env(tts_provider, tts_model)
            ),
            single_voice=_as_bool(tts.get("single_voice", True)),
            primary_voice=tts.get("primary_voice", "host"),
            words_per_minute=int(tts.get("words_per_minute", 155)),
            piper_path=tts.get("piper_path", "piper"),
            piper_model_path=tts.get("piper_model_path"),
            voices=_load_tts_voices(tts.get("voices", {})),
        ),
        voices=dict(raw.get("voices", {})),
    )


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)


def parse_duration(value: Any) -> EpisodeDuration:
    if value is None:
        return EpisodeDuration(minutes=5, label="5 minutes")
    if isinstance(value, bool):
        raise ValueError("Duration must be a minute count or `unlimited`.")
    if isinstance(value, int):
        return _duration_from_minutes(value)
    if isinstance(value, float):
        if not value.is_integer():
            raise ValueError("Duration minutes must be a whole number.")
        return _duration_from_minutes(int(value))

    normalized = str(value).strip().lower()
    if normalized in {"unlimited", "open", "open-ended", "none", "no limit"}:
        return EpisodeDuration(minutes=None, label="unlimited")

    minute_match = re.fullmatch(r"(\d+)\s*(m|min|mins|minute|minutes)?", normalized)
    if minute_match:
        return _duration_from_minutes(int(minute_match.group(1)))

    hour_match = re.fullmatch(r"(\d+)\s*(h|hr|hrs|hour|hours)", normalized)
    if hour_match:
        return _duration_from_minutes(int(hour_match.group(1)) * 60)

    raise ValueError(
        "Duration must look like `18`, `18m`, `18 minutes`, `1 hour`, or `unlimited`."
    )


def _duration_from_minutes(minutes: int) -> EpisodeDuration:
    if minutes <= 0:
        raise ValueError("Duration must be greater than zero, or `unlimited`.")
    unit = "minute" if minutes == 1 else "minutes"
    return EpisodeDuration(minutes=minutes, label=f"{minutes} {unit}")


def _load_tts_voices(raw: dict[str, Any]) -> dict[str, TtsVoiceConfig]:
    if not raw:
        return {
            "host": TtsVoiceConfig(
                voice="alloy", instructions="Warm, conversational, morning radio host."
            ),
            "anchor": TtsVoiceConfig(
                voice="onyx", instructions="Clear, grounded, professional news reader."
            ),
        }

    voices: dict[str, TtsVoiceConfig] = {}
    for name, value in raw.items():
        if isinstance(value, str):
            voices[name] = TtsVoiceConfig(voice=value)
            continue

        voices[name] = TtsVoiceConfig(
            voice=value.get("voice", name),
            instructions=value.get("instructions"),
            speed=float(value.get("speed", 1.0)),
            words_per_minute=_optional_int(value.get("words_per_minute")),
            speaker=value.get("speaker"),
            settings=dict(value.get("settings", {})),
        )
    return voices


def _default_tts_model(provider: str) -> str:
    provider = provider.lower()
    if provider == "elevenlabs":
        return "elevenlabs/eleven_multilingual_v2"
    if provider in {"litellm", "openai"}:
        return "openai/gpt-4o-mini-tts"
    return "gpt-4o-mini-tts"


def _default_tts_response_format(provider: str) -> str:
    if provider.lower() == "elevenlabs":
        return "mp3"
    return "wav"


def _default_tts_api_base(provider: str) -> str | None:
    return None


def _default_tts_api_key_env(provider: str, model: str) -> str | None:
    provider = provider.lower()
    if provider == "elevenlabs":
        return "ELEVENLABS_API_KEY"
    if provider in {"litellm", "openai"}:
        if model.startswith("anthropic/"):
            return "ANTHROPIC_API_KEY"
        if model.startswith("azure/"):
            return "AZURE_API_KEY"
        if model.startswith("elevenlabs/"):
            return "ELEVENLABS_API_KEY"
        if model.startswith("openai/") or provider == "openai":
            return "OPENAI_API_KEY"
    return None


def _load_yaml(path: Path) -> dict[str, Any]:
    text = path.read_text()
    try:
        import yaml
    except ImportError:
        return _parse_simple_yaml(text)

    return yaml.safe_load(text) or {}


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _parse_simple_yaml(text: str) -> dict[str, Any]:
    lines = [
        line.rstrip()
        for line in text.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    parsed, next_index = _parse_yaml_block(lines, 0, 0)
    if next_index < len(lines):
        raise ValueError("Could not parse the complete config file.")
    if not isinstance(parsed, dict):
        raise ValueError("Config root must be a mapping.")
    return parsed


def _parse_yaml_block(
    lines: list[str], index: int, indent: int
) -> tuple[dict[str, Any] | list[Any], int]:
    if index >= len(lines):
        return {}, index

    stripped = lines[index].strip()
    if stripped.startswith("- "):
        return _parse_yaml_list(lines, index, indent)
    return _parse_yaml_map(lines, index, indent)


def _parse_yaml_map(lines: list[str], index: int, indent: int) -> tuple[dict[str, Any], int]:
    result: dict[str, Any] = {}

    while index < len(lines):
        line = lines[index]
        line_indent = _indent(line)
        if line_indent < indent:
            break
        if line_indent > indent:
            raise ValueError(f"Unexpected indentation: {line}")

        stripped = line.strip()
        if stripped.startswith("- "):
            break
        key, value = stripped.split(":", 1)
        key = key.strip()
        value = value.strip()

        if value:
            result[key] = _parse_scalar(value)
            index += 1
            continue

        index += 1
        if index >= len(lines) or _indent(lines[index]) <= line_indent:
            result[key] = {}
            continue

        result[key], index = _parse_yaml_block(lines, index, _indent(lines[index]))

    return result, index


def _parse_yaml_list(lines: list[str], index: int, indent: int) -> tuple[list[Any], int]:
    result: list[Any] = []

    while index < len(lines):
        line = lines[index]
        line_indent = _indent(line)
        if line_indent < indent:
            break
        if line_indent != indent:
            raise ValueError(f"Unexpected list indentation: {line}")

        stripped = line.strip()
        if not stripped.startswith("- "):
            break

        result.append(_parse_scalar(stripped[2:].strip()))
        index += 1

    return result, index


def _parse_scalar(value: str) -> Any:
    if value in {"''", '""'}:
        return ""
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    if value.lower() in {"null", "none"}:
        return None
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))
