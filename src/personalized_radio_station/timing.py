from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import re

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


def format_duration(seconds: float | None) -> str | None:
    if seconds is None:
        return None

    total_seconds = round(seconds)
    minutes, second = divmod(total_seconds, 60)
    hours, minute = divmod(minutes, 60)
    if hours:
        return f"{hours}:{minute:02d}:{second:02d}"
    return f"{minute}:{second:02d}"
