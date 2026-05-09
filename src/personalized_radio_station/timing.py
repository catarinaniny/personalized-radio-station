from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import re

from .audio import audio_duration_seconds
from .config import AppConfig


WORD_RE = re.compile(r"[A-Za-z0-9]+(?:['-][A-Za-z0-9]+)?")
TARGET_TOLERANCE = 0.08


@dataclass(frozen=True)
class WordBudget:
    target_words: int
    min_words: int
    max_words: int
    words_per_minute: int


def effective_words_per_minute(config: AppConfig) -> int:
    voice = config.tts.voices.get(config.tts.primary_voice)
    base_wpm = voice.words_per_minute if voice and voice.words_per_minute else config.tts.words_per_minute
    speed = voice.speed if voice else 1.0
    return max(1, round(base_wpm * speed))


def word_budget(config: AppConfig) -> WordBudget | None:
    if config.duration.minutes is None:
        return None

    wpm = effective_words_per_minute(config)
    target_words = config.duration.minutes * wpm
    return WordBudget(
        target_words=target_words,
        min_words=round(target_words * (1 - TARGET_TOLERANCE)),
        max_words=round(target_words * (1 + TARGET_TOLERANCE)),
        words_per_minute=wpm,
    )


def count_episode_words(episode: dict[str, Any]) -> int:
    return sum(count_words(str(segment.get("text", ""))) for segment in episode.get("segments", []))


def count_words(text: str) -> int:
    return len(WORD_RE.findall(text))


def episode_timing_metadata(config: AppConfig, script_words: int) -> dict[str, Any]:
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


def add_audio_timing(
    episode: dict[str, Any], audio_file: Path, script_words: int, config: AppConfig
) -> None:
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


def format_duration(seconds: float | None) -> str | None:
    if seconds is None:
        return None

    total_seconds = round(seconds)
    minutes, second = divmod(total_seconds, 60)
    hours, minute = divmod(minutes, 60)
    if hours:
        return f"{hours}:{minute:02d}:{second:02d}"
    return f"{minute}:{second:02d}"


def _format_signed_duration(seconds: float) -> str:
    sign = "+" if seconds >= 0 else "-"
    label = format_duration(abs(seconds)) or "0:00"
    return f"{sign}{label}"
