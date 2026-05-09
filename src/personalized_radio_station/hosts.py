from __future__ import annotations

from dataclasses import replace

from .config import AppConfig, TtsVoiceConfig


TONE_STYLES = {
    "casual": (
        "casual, vibe-forward, loose but useful radio with warm pacing, quick "
        "reactions, and a little texture between source-backed facts"
    ),
    "professional": (
        "professional, slightly more expert radio with crisp framing, clear "
        "context, and confident analysis without sounding stiff"
    ),
}

VOICE_PRESETS = {
    "female": {
        "host": TtsVoiceConfig(
            voice="coral",
            instructions="Warm, expressive female radio host with natural momentum.",
            words_per_minute=155,
        ),
        "cohost": TtsVoiceConfig(
            voice="alloy",
            instructions="Bright female co-host, concise and conversational.",
            words_per_minute=158,
        ),
    },
    "male": {
        "host": TtsVoiceConfig(
            voice="onyx",
            instructions="Calm, confident male radio host with grounded delivery.",
            words_per_minute=150,
        ),
        "cohost": TtsVoiceConfig(
            voice="verse",
            instructions="Clear male co-host, lightly energetic and direct.",
            words_per_minute=154,
        ),
    },
}

DUO_SEGMENT_VOICES = {
    "intro": "host",
    "weather": "host",
    "news": "cohost",
    "outro": "host",
}


def host_style(tone: str, voice_gender: str, host_format: str) -> str:
    tone_style = TONE_STYLES.get(tone, TONE_STYLES["casual"])
    host_label = "solo host" if host_format == "solo" else "two-host handoff"
    voice_label = "female-led" if voice_gender == "female" else "male-led"
    return f"{tone_style}; {voice_label}; {host_label}"


def apply_host_profile(
    config: AppConfig,
    tone: str | None,
    voice_gender: str | None,
    host_format: str | None,
) -> AppConfig:
    tone = tone if tone in TONE_STYLES else None
    voice_gender = voice_gender if voice_gender in VOICE_PRESETS else None
    host_format = host_format if host_format in {"solo", "duo"} else None
    if not tone and not voice_gender and not host_format:
        return config

    resolved_tone = tone or "casual"
    resolved_gender = voice_gender or "female"
    resolved_format = host_format or "solo"
    preset = VOICE_PRESETS[resolved_gender]

    tts_voices = dict(config.tts.voices)
    tts_voices.update({"host": preset["host"]})
    if resolved_format == "duo":
        tts_voices["cohost"] = preset["cohost"]

    tts = replace(
        config.tts,
        single_voice=resolved_format == "solo",
        primary_voice="host",
        voices=tts_voices,
    )
    voices = (
        dict(DUO_SEGMENT_VOICES)
        if resolved_format == "duo"
        else {segment: "host" for segment in DUO_SEGMENT_VOICES}
    )

    return replace(
        config,
        style=host_style(resolved_tone, resolved_gender, resolved_format),
        tts=tts,
        voices=voices,
    )
